"""Fábricas de datos para las pruebas automatizadas.

Crean registros mínimos y explícitos para que cada prueba muestre
claramente con qué datos trabaja.
"""

from datetime import time, timedelta
from itertools import count

from django.utils import timezone

from accounts.models import Estudiante, Usuario
from academics.models import Asignatura, Carrera, Docente, Horario, PeriodoAcademico, Seccion

CLAVE = "ClavePrueba2026!"
_sec = count(1)


def carrera(codigo="ISW", nombre="Ingeniería de Software"):
    obj, _ = Carrera.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre})
    return obj


def docente():
    n = next(_sec)
    return Docente.objects.create(nombre="Docente", apellido=f"Prueba {n}", correo=f"docente{n}@prueba.test")


def periodo(estado="activo", dias_limite=30, nombre=None):
    hoy = timezone.localdate()
    return PeriodoAcademico.objects.create(
        nombre=nombre or f"Período prueba {next(_sec)}",
        fecha_inicio=hoy - timedelta(days=10),
        fecha_fin=hoy + timedelta(days=120),
        fecha_limite_matricula=hoy + timedelta(days=dias_limite),
        estado=estado,
    )


def asignatura(nombre="Asignatura", codigo=None, creditos=3, estado="activa", carrera_obj=None):
    return Asignatura.objects.create(
        codigo=codigo or f"TST-{next(_sec):03d}", nombre=nombre, creditos=creditos,
        carrera=carrera_obj or carrera(), semestre_recomendado=1, estado=estado,
    )


def seccion(asig=None, per=None, paralelo="A", capacidad=30, bloques=((1, "07:00", "09:00"),)):
    s = Seccion.objects.create(
        asignatura=asig or asignatura(), docente=docente(), periodo=per or PeriodoAcademico.actual() or periodo(),
        paralelo=paralelo, capacidad_maxima=capacidad,
    )
    for dia, ini, fin in bloques:
        h1, m1 = map(int, ini.split(":"))
        h2, m2 = map(int, fin.split(":"))
        Horario.objects.create(seccion=s, dia_semana=dia, hora_inicio=time(h1, m1), hora_fin=time(h2, m2))
    return s


def estudiante(usuario="estudiante", carrera_obj=None):
    u = Usuario.objects.create_user(
        usuario, f"{usuario}@prueba.test", CLAVE, nombre=usuario.split(".")[0].title(), apellido="Prueba",
    )
    return Estudiante.objects.create(
        usuario=u, codigo_estudiantil=f"COD-{next(_sec):04d}", carrera=carrera_obj or carrera(), semestre_actual=1,
    )


def administrador(usuario="admin.prueba"):
    return Usuario.objects.create_superuser(usuario, f"{usuario}@prueba.test", CLAVE, nombre="Admin", apellido="Prueba")
