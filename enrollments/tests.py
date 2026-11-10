import re
from datetime import timedelta
from unittest import mock

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from campusflow import fabricas as f
from quality_lab.models import ConfiguracionDemo

from . import services
from .models import DetalleMatricula, Matricula


class ReglasMatriculaTests(TestCase):
    def setUp(self):
        self.periodo = f.periodo()
        self.est = f.estudiante("ana.reglas")

    def reglas(self, ids, estudiante=None):
        return [i.regla for i in services.validar_seleccion(estudiante or self.est, ids)]

    def test_sin_seleccion(self):
        """R4: no se confirma sin al menos una asignatura."""
        self.assertEqual(self.reglas([]), [services.SIN_SELECCION])
        with self.assertRaises(services.MatriculaRechazada):
            services.confirmar_matricula(self.est, [])
        self.assertFalse(Matricula.objects.exists())

    def test_ids_invalidos_se_ignoran(self):
        """Valores no numéricos en la selección se tratan como selección vacía."""
        self.assertEqual(self.reglas(["abc", None, "-3"]), [services.SIN_SELECCION])
        self.assertEqual(self.reglas([str(10**30)]), [services.SIN_SELECCION])

    def test_duplicado_en_la_misma_seleccion(self):
        """R1: dos paralelos de la misma asignatura en una sola selección."""
        asig = f.asignatura()
        a = f.seccion(asig, self.periodo, "A", bloques=((1, "07:00", "09:00"),))
        b = f.seccion(asig, self.periodo, "B", bloques=((2, "07:00", "09:00"),))
        self.assertEqual(self.reglas([a.pk, b.pk]), [services.ASIGNATURA_DUPLICADA])

    def test_misma_seccion_repetida_cuenta_una_vez(self):
        """Enviar el mismo identificador dos veces equivale a una sola selección."""
        s = f.seccion(per=self.periodo)
        resultado = services.confirmar_matricula(self.est, [s.pk, s.pk])
        self.assertEqual(len(resultado.detalles_creados), 1)

    def test_cruce_con_asignatura_ya_inscrita(self):
        """R3: también se detecta el cruce con lo matriculado antes."""
        a = f.seccion(per=self.periodo, bloques=((4, "07:00", "09:00"),))
        b = f.seccion(per=self.periodo, bloques=((4, "07:30", "09:30"),))
        services.confirmar_matricula(self.est, [a.pk])
        incidencias = services.validar_seleccion(self.est, [b.pk])
        self.assertEqual([i.regla for i in incidencias], [services.CRUCE_HORARIO])
        self.assertIn("ya inscrita", incidencias[0].mensaje)

    def test_bloques_contiguos_no_se_cruzan(self):
        """Una clase que empieza cuando termina otra no es un cruce."""
        a = f.seccion(per=self.periodo, bloques=((3, "07:00", "09:00"),))
        b = f.seccion(per=self.periodo, bloques=((3, "09:00", "12:00"),))
        resultado = services.confirmar_matricula(self.est, [a.pk, b.pk])
        self.assertEqual(len(resultado.detalles_creados), 2)

    def test_fuera_de_plazo(self):
        """R5: después de la fecha límite no se puede matricular."""
        s = f.seccion(per=self.periodo)
        manana = timezone.localdate() + timedelta(days=31)
        self.assertEqual(self.reglas_en([s.pk], manana), [services.FUERA_DE_PERIODO])

    def reglas_en(self, ids, hoy):
        return [i.regla for i in services.validar_seleccion(self.est, ids, hoy=hoy)]

    def test_sin_periodo_activo(self):
        """R5: sin período activo no hay matrícula."""
        s = f.seccion(per=self.periodo)
        self.periodo.estado = "cerrado"
        self.periodo.save()
        self.assertEqual(self.reglas([s.pk]), [services.FUERA_DE_PERIODO])

    def test_seccion_de_otro_periodo_o_asignatura_inactiva(self):
        """Solo se aceptan secciones ofertadas en el período activo."""
        otro = f.periodo(estado="planificado")
        ajena = f.seccion(per=otro)
        inactiva = f.seccion(f.asignatura(estado="inactiva"), self.periodo)
        self.assertEqual(self.reglas([ajena.pk, inactiva.pk]),
                         [services.SECCION_INVALIDA, services.SECCION_INVALIDA])

    def test_atomicidad_una_valida_y_una_sin_cupo(self):
        """R9: si una sección falla, tampoco se guarda la válida."""
        valida = f.seccion(per=self.periodo, bloques=((1, "07:00", "09:00"),))
        llena = f.seccion(per=self.periodo, capacidad=1, bloques=((2, "07:00", "09:00"),))
        services.confirmar_matricula(f.estudiante("otro"), [llena.pk])
        with self.assertRaises(services.MatriculaRechazada) as ctx:
            services.confirmar_matricula(self.est, [valida.pk, llena.pk])
        self.assertEqual([i.regla for i in ctx.exception.incidencias], [services.CUPO_AGOTADO])
        self.assertFalse(Matricula.objects.filter(estudiante=self.est).exists())
        self.assertEqual(valida.cupos_ocupados, 0)

    def test_varias_incidencias_se_informan_juntas(self):
        """Se informan todos los motivos de rechazo, no solo el primero."""
        llena = f.seccion(per=self.periodo, capacidad=1, bloques=((2, "07:00", "09:00"),))
        services.confirmar_matricula(f.estudiante("otro"), [llena.pk])
        a = f.seccion(per=self.periodo, bloques=((1, "07:00", "09:00"),))
        b = f.seccion(per=self.periodo, bloques=((1, "08:00", "10:00"),))
        self.assertEqual(self.reglas([llena.pk, a.pk, b.pk]), [services.CUPO_AGOTADO, services.CRUCE_HORARIO])

    def test_restriccion_bd_impide_duplicado(self):
        """La base de datos rechaza la misma asignatura inscrita dos veces en una matrícula."""
        asig = f.asignatura()
        a = f.seccion(asig, self.periodo, "A")
        b = f.seccion(asig, self.periodo, "B", bloques=((5, "07:00", "09:00"),))
        m = services.confirmar_matricula(self.est, [a.pk]).matricula
        with self.assertRaises(IntegrityError), transaction.atomic():
            DetalleMatricula.objects.create(matricula=m, seccion=b, asignatura=asig)

    def test_una_matricula_por_estudiante_y_periodo(self):
        """Confirmaciones sucesivas agregan detalles a la misma matrícula."""
        a = f.seccion(per=self.periodo, bloques=((1, "07:00", "09:00"),))
        b = f.seccion(per=self.periodo, bloques=((2, "07:00", "09:00"),))
        m1 = services.confirmar_matricula(self.est, [a.pk]).matricula
        m2 = services.confirmar_matricula(self.est, [b.pk]).matricula
        self.assertEqual(m1.pk, m2.pk)
        self.assertEqual(m2.detalles_vigentes().count(), 2)

    def test_condicion_de_carrera_en_cupos(self):
        """La comprobación final dentro de la transacción evita superar la capacidad."""
        s = f.seccion(per=self.periodo, capacidad=1)
        original = services.validar_seleccion

        def validar_y_colarse(estudiante, ids, hoy=None):
            # Simula que otro estudiante toma el último cupo justo después de validar.
            incidencias = original(estudiante, ids, hoy)
            if estudiante == self.est and not getattr(validar_y_colarse, "hecho", False):
                validar_y_colarse.hecho = True
                intruso = f.estudiante("intruso")
                m = Matricula.objects.create(estudiante=intruso, periodo=self.periodo)
                DetalleMatricula.objects.create(matricula=m, seccion=s, asignatura=s.asignatura)
            return incidencias

        with mock.patch.object(services, "validar_seleccion", validar_y_colarse):
            with self.assertRaises(services.MatriculaRechazada) as ctx:
                services.confirmar_matricula(self.est, [s.pk])
        self.assertEqual(ctx.exception.incidencias[0].regla, services.CUPO_AGOTADO)
        self.assertFalse(Matricula.objects.filter(estudiante=self.est).exists())


class RetiroTests(TestCase):
    def setUp(self):
        self.periodo = f.periodo()
        self.est = f.estudiante("ana.retiro")
        self.seccion = f.seccion(per=self.periodo, capacidad=1)
        self.detalle = services.confirmar_matricula(self.est, [self.seccion.pk]).detalles_creados[0]

    def test_retiro_libera_cupo_y_conserva_historial(self):
        """C2/C3: el retiro marca el detalle como retirado y libera el cupo."""
        services.retirar_asignatura(self.est, self.detalle.pk)
        self.detalle.refresh_from_db()
        self.assertEqual(self.detalle.estado, "retirada")
        self.assertIsNotNone(self.detalle.fecha_retiro)
        self.assertEqual(self.seccion.cupos_disponibles, 1)

    def test_matricula_queda_sin_asignaturas_y_se_reactiva(self):
        """C4: sin asignaturas vigentes la matrícula cambia de estado y se reactiva al volver a matricular."""
        services.retirar_asignatura(self.est, self.detalle.pk)
        m = Matricula.objects.get(estudiante=self.est)
        self.assertEqual(m.estado, Matricula.Estado.SIN_ASIGNATURAS)
        services.confirmar_matricula(self.est, [self.seccion.pk])
        m.refresh_from_db()
        self.assertEqual(m.estado, Matricula.Estado.ACTIVA)
        self.assertEqual(m.detalles.count(), 2)

    def test_retiro_fuera_de_plazo(self):
        """C1: después de la fecha límite no se puede retirar."""
        despues = timezone.localdate() + timedelta(days=31)
        with self.assertRaises(services.MatriculaRechazada):
            services.retirar_asignatura(self.est, self.detalle.pk, hoy=despues)
        self.detalle.refresh_from_db()
        self.assertEqual(self.detalle.estado, "inscrita")

    def test_no_se_retira_dos_veces(self):
        """Un detalle ya retirado no puede retirarse de nuevo."""
        services.retirar_asignatura(self.est, self.detalle.pk)
        with self.assertRaises(services.MatriculaRechazada):
            services.retirar_asignatura(self.est, self.detalle.pk)

    def test_no_se_retira_asignatura_ajena(self):
        """R10: un estudiante no puede retirar asignaturas de otro."""
        with self.assertRaises(services.MatriculaRechazada):
            services.retirar_asignatura(f.estudiante("otro"), self.detalle.pk)


class VistasEstudianteTests(TestCase):
    def setUp(self):
        self.periodo = f.periodo()
        self.est = f.estudiante("ana.vistas")
        self.a = f.seccion(f.asignatura("Programación I"), self.periodo, bloques=((1, "07:00", "09:00"),))
        self.b = f.seccion(f.asignatura("Programación OO"), self.periodo, bloques=((1, "08:00", "10:00"),))
        self.client.force_login(self.est.usuario)

    def test_paginas_del_estudiante(self):
        """Inicio, oferta, matrícula y mis asignaturas cargan para el estudiante."""
        for nombre in ("enrollments:panel", "enrollments:oferta", "enrollments:matricula", "enrollments:mis_asignaturas", "evaluar"):
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 200, nombre)

    def test_filtro_de_oferta(self):
        """La oferta se filtra por nombre y por carrera."""
        otra = f.carrera("CDA", "Ciencia de Datos")
        f.seccion(f.asignatura("Estadística", carrera_obj=otra), self.periodo)
        r = self.client.get(reverse("enrollments:oferta"), {"q": "estad"})
        self.assertContains(r, "Estadística")
        self.assertNotContains(r, "Programación I")
        r = self.client.get(reverse("enrollments:oferta"), {"carrera": otra.pk})
        self.assertEqual([g["asignatura"].nombre for g in r.context["grupos"]], ["Estadística"])

    def test_versiones_a_y_b(self):
        """La página de matrícula muestra la versión configurada para la demostración."""
        r = self.client.get(reverse("enrollments:matricula"))
        self.assertTemplateUsed(r, "enrollments/matricula_a.html")
        self.assertNotContains(r, "data-calendario")
        self.client.post(reverse("demo:demo_version"), {"version": "B"})
        r = self.client.get(reverse("enrollments:matricula"))
        self.assertTemplateUsed(r, "enrollments/matricula_b.html")
        self.assertContains(r, "data-calendario")
        self.assertEqual(ConfiguracionDemo.obtener().version_experiencia, "B")

    def test_confirmar_desde_la_web(self):
        """Una confirmación válida redirige al comprobante con la matrícula guardada."""
        r = self.client.post(reverse("enrollments:confirmar"), {"secciones": [self.a.pk]})
        m = Matricula.objects.get(estudiante=self.est)
        self.assertRedirects(r, reverse("enrollments:comprobante", args=[m.pk]))
        self.assertContains(self.client.get(r["Location"]), "Programación I")

    def test_rechazo_desde_la_web_explica_el_motivo(self):
        """Un cruce se rechaza con HTTP 422 y un mensaje comprensible."""
        r = self.client.post(reverse("enrollments:confirmar"), {"secciones": [self.a.pk, self.b.pk]})
        self.assertEqual(r.status_code, 422)
        self.assertContains(r, "se cruza", status_code=422)
        self.assertContains(r, "No se guardó ningún cambio", status_code=422)
        self.assertFalse(Matricula.objects.exists())

    def test_confirmar_sin_seleccion_desde_la_web(self):
        """El backend rechaza un envío vacío aunque se salte la validación del navegador."""
        r = self.client.post(reverse("enrollments:confirmar"), {})
        self.assertEqual(r.status_code, 422)
        self.assertContains(r, "al menos una asignatura", status_code=422)

    def test_validar_responde_json_sin_guardar(self):
        """La comprobación previa de la Versión B no guarda nada."""
        r = self.client.post(reverse("enrollments:validar"), {"secciones": [self.a.pk, self.b.pk]})
        datos = r.json()
        self.assertFalse(datos["valida"])
        self.assertEqual(datos["incidencias"][0]["regla"], services.CRUCE_HORARIO)
        r = self.client.post(reverse("enrollments:validar"), {"secciones": [self.a.pk]})
        self.assertTrue(r.json()["valida"])
        self.assertFalse(Matricula.objects.exists())

    def test_retirar_desde_la_web(self):
        """El estudiante retira una asignatura propia desde Mis asignaturas."""
        d = services.confirmar_matricula(self.est, [self.a.pk]).detalles_creados[0]
        r = self.client.post(reverse("enrollments:retirar", args=[d.pk]), follow=True)
        self.assertContains(r, "El cupo quedó disponible")
        d.refresh_from_db()
        self.assertEqual(d.estado, "retirada")

    def test_retirar_requiere_post(self):
        """Retirar no se puede hacer con un simple enlace GET."""
        d = services.confirmar_matricula(self.est, [self.a.pk]).detalles_creados[0]
        self.assertEqual(self.client.get(reverse("enrollments:retirar", args=[d.pk])).status_code, 405)

    def test_omitir_validacion_del_navegador_habilita_opciones(self):
        """En la demo se puede desactivar la validación del navegador para probar el backend."""
        llena = f.seccion(f.asignatura("Llena"), self.periodo, capacidad=1, bloques=((6, "07:00", "09:00"),))
        services.confirmar_matricula(f.estudiante("otro"), [llena.pk])

        def casilla(respuesta):
            html = respuesta.content.decode()
            return re.search(rf'<input type="checkbox" name="secciones" value="{llena.pk}"[^>]*>', html).group(0)

        self.assertIn("disabled", casilla(self.client.get(reverse("enrollments:matricula"))))
        self.client.post(reverse("demo:demo_validacion_cliente"))
        r = self.client.get(reverse("enrollments:matricula"))
        self.assertNotIn("disabled", casilla(r))
        self.assertContains(r, "data-sin-validacion")
        # Aun así, el backend rechaza la sección llena.
        r = self.client.post(reverse("enrollments:confirmar"), {"secciones": [llena.pk]})
        self.assertContains(r, "CUPO_AGOTADO", status_code=422)

    def test_siguiente_externo_no_redirige_fuera(self):
        """Los controles de demo no redirigen a sitios externos."""
        r = self.client.post(reverse("demo:demo_version"), {"version": "A", "siguiente": "https://ejemplo.com/"})
        self.assertEqual(r["Location"], reverse("inicio"))


class VistasAdminMatriculasTests(TestCase):
    def test_admin_consulta_matriculas(self):
        """El administrador consulta la lista y el detalle de cualquier matrícula."""
        periodo = f.periodo()
        est = f.estudiante("ana.admin")
        m = services.confirmar_matricula(est, [f.seccion(per=periodo).pk]).matricula
        self.client.force_login(f.administrador())
        r = self.client.get(reverse("matriculas_admin:admin_matriculas"))
        self.assertContains(r, m.codigo)
        r = self.client.get(reverse("matriculas_admin:admin_matricula_detalle", args=[m.pk]))
        self.assertContains(r, "Ana")
