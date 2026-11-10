import io
import json
import tempfile
import unittest
from pathlib import Path

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Estudiante, Usuario
from academics.models import Asignatura, PeriodoAcademico, Seccion
from campusflow import fabricas as f
from enrollments import services
from enrollments.models import Matricula

from quality_lab import demo, verificacion
from quality_lab.models import ConfiguracionDemo, EvaluacionExperiencia
from quality_lab.runner import ResultadoVyV
from quality_lab.soporte import CasoVyVMixin, caso


class LaboratorioVistasTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        ajuste = override_settings(CAMPUSFLOW_REPORTES_DIR=Path(self.tmp.name))
        ajuste.enable()
        self.addCleanup(ajuste.disable)
        self.client.force_login(f.administrador())

    def test_sin_reporte_ningun_caso_aparece_aprobado(self):
        """Antes de ejecutar, los casos se muestran como «sin ejecutar», nunca aprobados."""
        r = self.client.get(reverse("quality_lab:verificacion"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual({c["estado"] for c in r.context["casos"]}, {"sin_ejecutar"})
        self.assertNotContains(r, "badge-success\">")

    def test_reporte_existente_se_muestra(self):
        """El laboratorio presenta lo que dice el reporte de la ejecución."""
        reporte = {
            "ejecutado_en": "2026-11-09T10:00:00", "comando": "python manage.py test", "codigo_salida": 1,
            "duracion_s": 1.2, "total": 2, "aprobadas": 1, "fallidas": 1, "base_datos_pruebas": ":memory:",
            "bd_principal_antes": {"usuarios": 1, "matriculas": 0, "detalles_matricula": 0},
            "bd_principal_despues": {"usuarios": 1, "matriculas": 0, "detalles_matricula": 0},
            "registros": [
                {"id": "x.test_v01", "caso": "V01", "estado": "aprobado", "obtenido": "Sesión creada", "descripcion": "", "detalle": "", "duracion_ms": 3, "datos_utilizados": "d"},
                {"id": "x.test_v05", "caso": "V05", "estado": "fallido", "obtenido": "Se aceptó", "descripcion": "", "detalle": "AssertionError", "duracion_ms": 3, "datos_utilizados": "d"},
            ],
            "salida": "...",
        }
        verificacion.ruta_reporte().write_text(json.dumps(reporte), encoding="utf-8")
        r = self.client.get(reverse("quality_lab:verificacion"))
        casos = {c["id"]: c for c in r.context["casos"]}
        self.assertEqual(casos["V01"]["estado"], "aprobado")
        self.assertEqual(casos["V05"]["estado"], "fallido")
        self.assertEqual(casos["V09"]["estado"], "sin_ejecutar")
        self.assertContains(r, "Se aceptó")

    def test_paginas_del_laboratorio(self):
        """Laboratorio, verificación y validación cargan para el administrador."""
        for nombre in ("quality_lab:laboratorio", "quality_lab:verificacion", "quality_lab:validacion"):
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 200)


class RunnerTests(unittest.TestCase):
    def test_resultado_registra_caso_y_obtenido(self):
        """El runner del laboratorio registra el caso, el estado y el resultado obtenido."""

        class Ejemplo(CasoVyVMixin, unittest.TestCase):
            @caso("V99")
            def test_ok(self):
                self.registrar(datos="d", obtenido="todo bien")

            def test_falla(self):
                self.assertEqual(1, 2)

        suite = unittest.defaultTestLoader.loadTestsFromTestCase(Ejemplo)
        resultado = ResultadoVyV(io.StringIO(), True, 0)
        suite.run(resultado)
        por_nombre = {r["id"].rsplit(".", 1)[-1]: r for r in resultado.registros}
        self.assertEqual(por_nombre["test_ok"]["caso"], "V99")
        self.assertEqual(por_nombre["test_ok"]["estado"], "aprobado")
        self.assertEqual(por_nombre["test_ok"]["obtenido"], "todo bien")
        self.assertEqual(por_nombre["test_falla"]["estado"], "fallido")
        self.assertIn("AssertionError", por_nombre["test_falla"]["detalle"])


class ValidacionTests(TestCase):
    def setUp(self):
        self.est = f.estudiante("ana.evalua")

    def test_evaluacion_se_guarda(self):
        """Las respuestas del formulario de evaluación se guardan en la base de datos."""
        self.client.force_login(self.est.usuario)
        r = self.client.post(reverse("evaluar"), {
            "version": "A", "participante": "Compañero 1", "facilidad_seleccion": 4,
            "comprension_horarios": 2, "informacion_suficiente": 2, "mejoras": "Ver mi semana antes de confirmar",
        })
        self.assertEqual(r.status_code, 302)
        e = EvaluacionExperiencia.objects.get()
        self.assertEqual((e.version, e.comprension_horarios, e.usuario), ("A", 2, self.est.usuario))

    def test_evaluacion_valida_rangos(self):
        """El backend rechaza puntuaciones fuera de la escala 1–5."""
        self.client.force_login(self.est.usuario)
        r = self.client.post(reverse("evaluar"), {"version": "C", "facilidad_seleccion": 9})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(EvaluacionExperiencia.objects.exists())

    def test_version_b_no_se_declara_validada_sin_evaluaciones(self):
        """Sin respuestas, la Versión B aparece pendiente de evaluación."""
        self.client.force_login(f.administrador())
        r = self.client.get(reverse("quality_lab:validacion"))
        self.assertEqual(r.context["resumen"]["B"]["n"], 0)
        self.assertContains(r, "Pendiente: sin evaluaciones de usuarios")
        self.assertNotContains(r, "Validada")

    def test_ambas_versiones_usan_las_mismas_reglas(self):
        """Con la Versión A o la B, el backend rechaza el mismo cruce."""
        periodo = f.periodo()
        a = f.seccion(per=periodo, bloques=((1, "07:00", "09:00"),))
        b = f.seccion(per=periodo, bloques=((1, "08:00", "10:00"),))
        self.client.force_login(self.est.usuario)
        for version in ("A", "B"):
            ConfiguracionDemo.objects.update_or_create(pk=1, defaults={"version_experiencia": version})
            r = self.client.post(reverse("enrollments:confirmar"), {"secciones": [a.pk, b.pk]})
            self.assertContains(r, "CRUCE_HORARIO", status_code=422)
        self.assertFalse(Matricula.objects.exists())


class DatosDemoTests(TestCase):
    def test_cargar_demo_crea_los_escenarios(self):
        """Los datos de demostración incluyen todos los escenarios de la exposición."""
        call_command("cargar_demo", stdout=io.StringIO())
        self.assertEqual(Usuario.objects.filter(rol="administrador").count(), 1)
        self.assertEqual(Estudiante.objects.count(), 3)
        self.assertTrue(8 <= Asignatura.objects.count() <= 12)
        periodo = PeriodoAcademico.actual()
        self.assertTrue(periodo.matricula_abierta())
        secciones = list(Seccion.objects.filter(periodo=periodo).con_cupos())
        self.assertTrue(any(s.cupos_disponibles == 0 for s in secciones))
        self.assertTrue(sum(1 for s in secciones if s.cupos_disponibles > 0) >= 5)
        ana = Estudiante.objects.get(usuario__nombre_usuario="ana.torres")
        # Matrícula exitosa posible.
        ok = Seccion.objects.get(periodo=periodo, asignatura__codigo="ISW-101", paralelo="A")
        self.assertEqual(services.validar_seleccion(ana, [ok.pk]), [])
        # Duplicada, cupo agotado y cruce.
        dup = Seccion.objects.get(periodo=periodo, asignatura__codigo="ISW-102", paralelo="B")
        llena = Seccion.objects.get(periodo=periodo, asignatura__codigo="ISW-202", paralelo="A")
        cruce = Seccion.objects.get(periodo=periodo, asignatura__codigo="ISW-201", paralelo="A")
        self.assertEqual([i.regla for i in services.validar_seleccion(ana, [dup.pk])], [services.ASIGNATURA_DUPLICADA])
        self.assertEqual([i.regla for i in services.validar_seleccion(ana, [llena.pk])], [services.CUPO_AGOTADO])
        self.assertEqual([i.regla for i in services.validar_seleccion(ana, [ok.pk, cruce.pk])], [services.CRUCE_HORARIO])
        # Las contraseñas de la demo funcionan y están cifradas.
        self.assertTrue(self.client.login(username="admin", password=demo.CLAVE_ADMIN))
        self.assertTrue(self.client.login(username="ana.torres", password=demo.CLAVE_ESTUDIANTE))

    def test_cargar_demo_no_duplica(self):
        """Ejecutar cargar_demo dos veces no duplica datos."""
        call_command("cargar_demo", stdout=io.StringIO())
        salida = io.StringIO()
        call_command("cargar_demo", stdout=salida)
        self.assertIn("No se cargó nada", salida.getvalue())
        self.assertEqual(Estudiante.objects.count(), 3)

    @override_settings(DEBUG=True)
    def test_reset_demo_restaura_el_estado_inicial(self):
        """reset_demo deshace los cambios hechos durante la demostración."""
        call_command("cargar_demo", stdout=io.StringIO())
        ana = Estudiante.objects.get(usuario__nombre_usuario="ana.torres")
        ok = Seccion.objects.get(periodo=PeriodoAcademico.actual(), asignatura__codigo="ISW-101", paralelo="A")
        services.confirmar_matricula(ana, [ok.pk])
        EvaluacionExperiencia.objects.create(version="A", facilidad_seleccion=3, comprension_horarios=2, informacion_suficiente=2)
        otro_admin = f.administrador("coordinacion")
        call_command("reset_demo", "--si", stdout=io.StringIO())
        ana = Estudiante.objects.get(usuario__nombre_usuario="ana.torres")
        self.assertEqual(services.detalles_vigentes(ana, PeriodoAcademico.actual()).count(), 1)
        self.assertEqual(EvaluacionExperiencia.objects.count(), 1)  # se conservan por defecto
        self.assertTrue(Usuario.objects.filter(pk=otro_admin.pk).exists())

    @override_settings(DEBUG=False)
    def test_reset_demo_bloqueado_sin_debug(self):
        """reset_demo se niega a ejecutarse con DEBUG desactivado."""
        with self.assertRaisesMessage(CommandError, "DEBUG"):
            call_command("reset_demo", "--si", stdout=io.StringIO())

    @override_settings(CAMPUSFLOW_ENTORNO="produccion")
    def test_reset_demo_bloqueado_fuera_de_local(self):
        """reset_demo se niega a ejecutarse si el entorno no es local."""
        with self.assertRaisesMessage(CommandError, "CAMPUSFLOW_ENTORNO"):
            call_command("reset_demo", "--si", stdout=io.StringIO())
