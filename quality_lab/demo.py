"""Datos de demostración reproducibles para la exposición.

Todos los nombres, correos y códigos son ficticios. Las fechas del período
activo se calculan a partir del día de carga para que la matrícula esté
siempre abierta durante la demostración.
"""

from __future__ import annotations

from datetime import time, timedelta

from django.db import transaction
from django.utils import timezone

from accounts.models import Estudiante, Usuario
from academics.models import Asignatura, Carrera, Docente, Horario, PeriodoAcademico, Seccion
from enrollments.models import DetalleMatricula, Matricula

from .models import ConfiguracionDemo, EvaluacionExperiencia

CLAVE_ADMIN = "CampusAdmin2026!"
CLAVE_ESTUDIANTE = "Estudiante2026!"

USUARIOS_DEMO = ["admin", "ana.torres", "bruno.mena", "carla.rios"]

CARRERAS = [("ISW", "Ingeniería de Software"), ("CDA", "Ciencia de Datos")]

DOCENTES = [
    ("Marta", "Salgado"), ("Jorge", "Villacís"), ("Lucía", "Andrade"),
    ("Pablo", "Cevallos"), ("Elena", "Paredes"), ("Andrés", "Moreira"),
]

# código, nombre, créditos, carrera, semestre, estado
ASIGNATURAS = [
    ("ISW-101", "Fundamentos de Programación", 4, "ISW", 1, "activa"),
    ("ISW-102", "Matemática Discreta", 3, "ISW", 1, "activa"),
    ("ISW-201", "Programación Orientada a Objetos", 4, "ISW", 2, "activa"),
    ("ISW-202", "Base de Datos I", 4, "ISW", 3, "activa"),
    ("ISW-203", "Ingeniería de Requisitos", 3, "ISW", 3, "activa"),
    ("ISW-302", "Interacción Humano-Computador", 3, "ISW", 4, "activa"),
    ("ISW-301", "Verificación y Validación de Software", 3, "ISW", 5, "activa"),
    ("ISW-399", "Taller de Tecnologías Emergentes", 2, "ISW", 6, "inactiva"),
    ("CDA-101", "Estadística Descriptiva", 4, "CDA", 1, "activa"),
    ("CDA-102", "Cálculo Diferencial", 4, "CDA", 1, "activa"),
    ("CDA-201", "Programación para Ciencia de Datos", 3, "CDA", 2, "activa"),
    ("CDA-202", "Álgebra Lineal", 4, "CDA", 2, "activa"),
]

LU, MA, MI, JU, VI = 1, 2, 3, 4, 5


def _h(texto):
    hh, mm = texto.split(":")
    return time(int(hh), int(mm))


# asignatura, paralelo, docente (índice), capacidad, [(día, inicio, fin)]
SECCIONES_ACTIVAS = [
    ("ISW-101", "A", 0, 30, [(LU, "07:00", "09:00"), (MI, "07:00", "09:00")]),
    ("ISW-101", "B", 0, 30, [(LU, "11:00", "13:00"), (MI, "11:00", "13:00")]),
    ("ISW-102", "A", 1, 25, [(MA, "07:00", "09:00"), (JU, "07:00", "09:00")]),
    ("ISW-102", "B", 1, 25, [(MI, "15:00", "17:00"), (VI, "15:00", "17:00")]),
    # Cruza con ISW-101 A (lunes y miércoles 08:00–09:00).
    ("ISW-201", "A", 2, 30, [(LU, "08:00", "10:00"), (MI, "08:00", "10:00")]),
    ("ISW-201", "B", 2, 30, [(MA, "11:00", "13:00"), (JU, "11:00", "13:00")]),
    # Sección sin cupos: capacidad 2, ocupada por Bruno y Carla.
    ("ISW-202", "A", 3, 2, [(MA, "09:00", "11:00"), (JU, "09:00", "11:00")]),
    ("ISW-202", "B", 3, 25, [(VI, "07:00", "11:00")]),
    ("ISW-203", "A", 4, 30, [(LU, "14:00", "17:00")]),
    # Cruza el jueves con ISW-102 A (que Ana ya tiene matriculada).
    ("ISW-302", "A", 4, 25, [(JU, "07:30", "09:30")]),
    # Empieza justo cuando termina ISW-101 A: NO es un cruce (límite exacto).
    ("ISW-301", "A", 5, 20, [(MI, "09:00", "12:00")]),
    ("CDA-101", "A", 5, 35, [(MA, "14:00", "16:00"), (JU, "14:00", "16:00")]),
    ("CDA-102", "A", 1, 35, [(LU, "09:00", "11:00"), (MI, "09:00", "11:00")]),
    ("CDA-102", "B", 1, 35, [(MA, "16:00", "18:00"), (JU, "16:00", "18:00")]),
    ("CDA-201", "A", 3, 25, [(VI, "14:00", "17:00")]),
    ("CDA-202", "A", 2, 30, [(LU, "11:00", "13:00"), (MI, "11:00", "13:00")]),
]

# usuario, nombre, apellido, código, carrera, semestre
ESTUDIANTES = [
    ("ana.torres", "Ana", "Torres", "2024-ISW-0012", "ISW", 3),
    ("bruno.mena", "Bruno", "Mena", "2023-ISW-0047", "ISW", 3),
    ("carla.rios", "Carla", "Ríos", "2024-CDA-0031", "CDA", 2),
]

# Matrículas existentes en el período activo: usuario -> [(asignatura, paralelo)]
MATRICULAS_ACTIVAS = {
    "ana.torres": [("ISW-102", "A")],
    "bruno.mena": [("ISW-202", "A"), ("ISW-203", "A")],
    "carla.rios": [("ISW-202", "A"), ("CDA-202", "A")],
}


def hay_datos_demo() -> bool:
    return Carrera.objects.exists() or Usuario.objects.filter(nombre_usuario__in=USUARIOS_DEMO).exists()


@transaction.atomic
def borrar_datos_demo(incluir_evaluaciones: bool = False) -> dict[str, int]:
    """Elimina los datos académicos, de matrícula y las cuentas de demostración.

    Conserva las cuentas administrativas creadas por fuera de la demo y, salvo
    que se indique, las evaluaciones de participantes (son evidencia real).
    """
    conteo = {
        "detalles_matricula": DetalleMatricula.objects.all().delete()[0],
        "matriculas": Matricula.objects.all().delete()[0],
    }
    conteo["horarios"] = Horario.objects.all().delete()[0]
    conteo["secciones"] = Seccion.objects.all().delete()[0]
    conteo["estudiantes"] = Estudiante.objects.all().delete()[0]
    conteo["usuarios"] = Usuario.objects.filter(nombre_usuario__in=USUARIOS_DEMO).delete()[0]
    conteo["usuarios"] += Usuario.objects.filter(rol=Usuario.Rol.ESTUDIANTE).delete()[0]
    conteo["asignaturas"] = Asignatura.objects.all().delete()[0]
    conteo["periodos"] = PeriodoAcademico.objects.all().delete()[0]
    conteo["docentes"] = Docente.objects.all().delete()[0]
    conteo["carreras"] = Carrera.objects.all().delete()[0]
    if incluir_evaluaciones:
        conteo["evaluaciones"] = EvaluacionExperiencia.objects.all().delete()[0]
    ConfiguracionDemo.objects.all().delete()
    return conteo


@transaction.atomic
def cargar_datos_demo(hoy=None) -> dict[str, int]:
    hoy = hoy or timezone.localdate()
    ahora = timezone.now()

    carreras = {c: Carrera.objects.create(codigo=c, nombre=n) for c, n in CARRERAS}
    docentes = [
        Docente.objects.create(
            nombre=n, apellido=a,
            correo=f"{n.lower()}.{a.lower().replace('í', 'i').replace('á', 'a')}@docentes.campusflow.test",
        )
        for n, a in DOCENTES
    ]
    asignaturas = {
        cod: Asignatura.objects.create(
            codigo=cod, nombre=nom, creditos=cr, carrera=carreras[car], semestre_recomendado=sem, estado=est
        )
        for cod, nom, cr, car, sem, est in ASIGNATURAS
    }

    semestre = 1 if hoy.month <= 6 else 2
    nombre_actual = f"Período {hoy.year}-{semestre}"
    nombre_anterior = f"Período {hoy.year}-1" if semestre == 2 else f"Período {hoy.year - 1}-2"
    anterior = PeriodoAcademico.objects.create(
        nombre=nombre_anterior,
        fecha_inicio=hoy - timedelta(days=220), fecha_fin=hoy - timedelta(days=60),
        fecha_limite_matricula=hoy - timedelta(days=200), estado=PeriodoAcademico.Estado.CERRADO,
    )
    activo = PeriodoAcademico.objects.create(
        nombre=nombre_actual,
        fecha_inicio=hoy - timedelta(days=14), fecha_fin=hoy + timedelta(days=120),
        fecha_limite_matricula=hoy + timedelta(days=30), estado=PeriodoAcademico.Estado.ACTIVO,
    )

    secciones = {}
    for cod, paralelo, doc, cap, bloques in SECCIONES_ACTIVAS:
        s = Seccion.objects.create(
            asignatura=asignaturas[cod], docente=docentes[doc], periodo=activo, paralelo=paralelo,
            capacidad_maxima=cap,
        )
        for dia, ini, fin in bloques:
            Horario.objects.create(seccion=s, dia_semana=dia, hora_inicio=_h(ini), hora_fin=_h(fin))
        secciones[(cod, paralelo)] = s

    historica = Seccion.objects.create(
        asignatura=asignaturas["ISW-101"], docente=docentes[0], periodo=anterior, paralelo="A", capacidad_maxima=30,
    )
    Horario.objects.create(seccion=historica, dia_semana=LU, hora_inicio=_h("07:00"), hora_fin=_h("09:00"))

    admin = Usuario.objects.create_superuser(
        "admin", "admin@campusflow.test", CLAVE_ADMIN, nombre="Laura", apellido="Benítez",
    )
    estudiantes = {}
    for usuario, nombre, apellido, codigo, carrera, semestre_actual in ESTUDIANTES:
        u = Usuario.objects.create_user(
            usuario, f"{usuario}@estudiantes.campusflow.test", CLAVE_ESTUDIANTE, nombre=nombre, apellido=apellido,
        )
        estudiantes[usuario] = Estudiante.objects.create(
            usuario=u, codigo_estudiantil=codigo, carrera=carreras[carrera], semestre_actual=semestre_actual,
        )

    # Matrículas existentes (se registran directamente como datos históricos de la demo).
    for i, (usuario, materias) in enumerate(MATRICULAS_ACTIVAS.items()):
        fecha = ahora - timedelta(days=5 - i, hours=3)
        m = Matricula.objects.create(estudiante=estudiantes[usuario], periodo=activo, fecha_registro=fecha)
        for cod, paralelo in materias:
            s = secciones[(cod, paralelo)]
            DetalleMatricula.objects.create(matricula=m, seccion=s, asignatura=s.asignatura, fecha_registro=fecha)

    previa = Matricula.objects.create(
        estudiante=estudiantes["bruno.mena"], periodo=anterior, fecha_registro=ahora - timedelta(days=210),
    )
    DetalleMatricula.objects.create(
        matricula=previa, seccion=historica, asignatura=historica.asignatura, fecha_registro=previa.fecha_registro,
    )

    ConfiguracionDemo.objects.update_or_create(pk=1, defaults={"version_experiencia": "A"})

    return {
        "carreras": len(carreras), "docentes": len(docentes), "asignaturas": len(asignaturas),
        "periodos": 2, "secciones": len(secciones) + 1, "estudiantes": len(estudiantes), "administradores": 1,
        "matriculas": Matricula.objects.count(), "detalles": DetalleMatricula.objects.count(),
        "periodo_activo": activo.nombre, "limite": activo.fecha_limite_matricula.isoformat(), "admin": admin.pk,
    }
