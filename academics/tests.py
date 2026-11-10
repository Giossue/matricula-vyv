from datetime import time, timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from campusflow import fabricas as f
from enrollments import services

from .models import Asignatura, Horario, PeriodoAcademico, Seccion


class ModelosAcademicosTests(TestCase):
    def test_codigo_de_asignatura_unico(self):
        """El código de la asignatura es único."""
        f.asignatura(codigo="ISW-001")
        with self.assertRaises(IntegrityError):
            f.asignatura(codigo="ISW-001")

    def test_solo_un_periodo_activo(self):
        """La base de datos impide dos períodos activos a la vez."""
        f.periodo()
        with self.assertRaises(IntegrityError):
            f.periodo()

    def test_validacion_de_periodo_activo_duplicado(self):
        """El formulario explica que ya existe un período activo."""
        f.periodo(nombre="Actual")
        hoy = timezone.localdate()
        nuevo = PeriodoAcademico(nombre="Otro", fecha_inicio=hoy, fecha_fin=hoy + timedelta(days=90),
                                 fecha_limite_matricula=hoy + timedelta(days=10), estado="activo")
        with self.assertRaises(ValidationError) as ctx:
            nuevo.full_clean()
        self.assertIn("estado", ctx.exception.message_dict)

    def test_fechas_del_periodo(self):
        """La fecha límite no puede superar el fin del período."""
        hoy = timezone.localdate()
        p = PeriodoAcademico(nombre="Mal", fecha_inicio=hoy, fecha_fin=hoy + timedelta(days=10),
                             fecha_limite_matricula=hoy + timedelta(days=20))
        with self.assertRaises(ValidationError):
            p.full_clean()

    def test_horario_debe_terminar_despues_de_empezar(self):
        """Un horario con fin anterior al inicio es rechazado por la base de datos."""
        s = f.seccion(per=f.periodo())
        with self.assertRaises(IntegrityError), transaction.atomic():
            Horario.objects.create(seccion=s, dia_semana=1, hora_inicio=time(10), hora_fin=time(9))

    def test_cruce_de_horarios(self):
        """Dos bloques se cruzan solo si comparten día y se superponen."""
        a = Horario(dia_semana=1, hora_inicio=time(7), hora_fin=time(9))
        self.assertTrue(a.se_cruza_con(Horario(dia_semana=1, hora_inicio=time(8), hora_fin=time(10))))
        self.assertFalse(a.se_cruza_con(Horario(dia_semana=1, hora_inicio=time(9), hora_fin=time(11))))
        self.assertFalse(a.se_cruza_con(Horario(dia_semana=2, hora_inicio=time(7), hora_fin=time(9))))
        self.assertTrue(a.se_cruza_con(Horario(dia_semana=1, hora_inicio=time(7, 30), hora_fin=time(8))))

    def test_paralelo_unico_por_asignatura_y_periodo(self):
        """No se repite el mismo paralelo de una asignatura en un período."""
        p = f.periodo()
        asig = f.asignatura()
        f.seccion(asig, p, "A")
        with self.assertRaises(IntegrityError):
            f.seccion(asig, p, "A")

    def test_cupos_calculados_desde_registros(self):
        """Los cupos disponibles se calculan contando las inscripciones reales."""
        p = f.periodo()
        s = f.seccion(per=p, capacidad=3)
        services.confirmar_matricula(f.estudiante("uno"), [s.pk])
        services.confirmar_matricula(f.estudiante("dos"), [s.pk])
        anotada = Seccion.objects.con_cupos().get(pk=s.pk)
        self.assertEqual((anotada.cupos_ocupados, anotada.cupos_disponibles), (2, 1))

    def test_capacidad_no_menor_a_inscritos(self):
        """No se puede reducir la capacidad por debajo de los inscritos."""
        p = f.periodo()
        s = f.seccion(per=p, capacidad=3)
        services.confirmar_matricula(f.estudiante("uno"), [s.pk])
        services.confirmar_matricula(f.estudiante("dos"), [s.pk])
        s.capacidad_maxima = 1
        with self.assertRaises(ValidationError):
            s.full_clean()


class GestionAdministrativaTests(TestCase):
    def setUp(self):
        self.admin = f.administrador()
        self.periodo = f.periodo()
        self.client.force_login(self.admin)

    def test_paginas_administrativas_responden(self):
        """Todas las páginas administrativas cargan para el administrador."""
        s = f.seccion(per=self.periodo)
        for url in (reverse("academics:panel"), reverse("academics:asignaturas"), reverse("academics:periodos"),
                    reverse("academics:secciones"), reverse("academics:docentes"), reverse("academics:cupos"),
                    reverse("admin_estudiantes"), reverse("matriculas_admin:admin_matriculas"),
                    reverse("academics:asignatura_nueva"), reverse("academics:periodo_nuevo"),
                    reverse("academics:docente_nuevo"), reverse("academics:seccion_nueva"),
                    reverse("academics:seccion_editar", args=[s.pk])):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_crear_y_editar_asignatura(self):
        """El administrador crea y edita asignaturas."""
        carrera = f.carrera()
        datos = {"codigo": "isw-500", "nombre": "Arquitectura de Software", "creditos": 4, "carrera": carrera.pk,
                 "semestre_recomendado": 6, "estado": "activa"}
        r = self.client.post(reverse("academics:asignatura_nueva"), datos)
        self.assertRedirects(r, reverse("academics:asignaturas"))
        asig = Asignatura.objects.get(codigo="ISW-500")
        datos["nombre"] = "Arquitectura de Software I"
        self.client.post(reverse("academics:asignatura_editar", args=[asig.pk]), datos)
        asig.refresh_from_db()
        self.assertEqual(asig.nombre, "Arquitectura de Software I")

    def test_datos_obligatorios_de_asignatura(self):
        """El backend rechaza una asignatura sin datos obligatorios o con créditos inválidos."""
        r = self.client.post(reverse("academics:asignatura_nueva"), {"codigo": "", "nombre": "", "creditos": 0})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Asignatura.objects.count(), 0)
        for campo in ("codigo", "nombre", "creditos", "carrera"):
            self.assertIn(campo, r.context["form"].errors)

    def test_desactivar_asignatura_la_quita_de_la_oferta(self):
        """Una asignatura desactivada deja de ofrecerse en la matrícula."""
        s = f.seccion(per=self.periodo)
        self.client.post(reverse("academics:asignatura_estado", args=[s.asignatura.pk]))
        s.asignatura.refresh_from_db()
        self.assertEqual(s.asignatura.estado, "inactiva")
        self.assertFalse(services.secciones_ofertadas(self.periodo).filter(pk=s.pk).exists())

    def test_crear_seccion_con_horarios(self):
        """El administrador crea una sección con docente, cupos y horarios."""
        asig = f.asignatura()
        doc = f.docente()
        datos = {
            "asignatura": asig.pk, "periodo": self.periodo.pk, "paralelo": "c", "docente": doc.pk,
            "capacidad_maxima": 20,
            "horarios-TOTAL_FORMS": 2, "horarios-INITIAL_FORMS": 0, "horarios-MIN_NUM_FORMS": 0, "horarios-MAX_NUM_FORMS": 6,
            "horarios-0-dia_semana": 1, "horarios-0-hora_inicio": "07:00", "horarios-0-hora_fin": "09:00",
            "horarios-1-dia_semana": 3, "horarios-1-hora_inicio": "07:00", "horarios-1-hora_fin": "09:00",
        }
        r = self.client.post(reverse("academics:seccion_nueva"), datos)
        self.assertEqual(r.status_code, 302)
        s = Seccion.objects.get(asignatura=asig)
        self.assertEqual((s.paralelo, s.capacidad_maxima, s.horarios.count()), ("C", 20, 2))

    def test_seccion_rechaza_bloques_superpuestos(self):
        """Una sección no puede tener dos bloques de horario superpuestos."""
        datos = {
            "asignatura": f.asignatura().pk, "periodo": self.periodo.pk, "paralelo": "A", "docente": f.docente().pk,
            "capacidad_maxima": 20,
            "horarios-TOTAL_FORMS": 2, "horarios-INITIAL_FORMS": 0, "horarios-MIN_NUM_FORMS": 0, "horarios-MAX_NUM_FORMS": 6,
            "horarios-0-dia_semana": 1, "horarios-0-hora_inicio": "07:00", "horarios-0-hora_fin": "09:00",
            "horarios-1-dia_semana": 1, "horarios-1-hora_inicio": "08:00", "horarios-1-hora_fin": "10:00",
        }
        r = self.client.post(reverse("academics:seccion_nueva"), datos)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Seccion.objects.exists())
        self.assertContains(r, "se superponen")

    def test_crear_periodo(self):
        """El administrador registra un período planificado."""
        hoy = timezone.localdate()
        r = self.client.post(reverse("academics:periodo_nuevo"), {
            "nombre": "Período 2027-1", "fecha_inicio": hoy + timedelta(days=100),
            "fecha_fin": hoy + timedelta(days=250), "fecha_limite_matricula": hoy + timedelta(days=120),
            "estado": "planificado",
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(PeriodoAcademico.objects.filter(nombre="Período 2027-1").exists())

    def test_crear_docente(self):
        """El administrador registra docentes."""
        r = self.client.post(reverse("academics:docente_nuevo"),
                             {"nombre": "Rosa", "apellido": "Vera", "correo": "rosa@prueba.test", "activo": "on"})
        self.assertEqual(r.status_code, 302)
