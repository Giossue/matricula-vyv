"""Reglas de negocio de la matrícula.

Toda la lógica vive aquí para que las vistas (cualquier versión de la interfaz)
y las pruebas automatizadas usen exactamente las mismas reglas.

Reglas implementadas
--------------------
R1  No se matricula dos veces la misma asignatura en el período.
R2  No se matricula una sección sin cupos (calculados desde los registros reales).
R3  No se matriculan secciones con horarios que se crucen (entre sí o con lo ya inscrito).
R4  No se confirma una matrícula sin al menos una asignatura seleccionada.
R5  No se matricula fuera del período habilitado (período activo y antes de la fecha límite).
R9  La confirmación es atómica: si una regla falla, no se guarda nada.
R10 Un estudiante solo opera sobre su propia matrícula.

Cancelación y recuperación de cupos
-----------------------------------
C1  El estudiante puede retirar una asignatura inscrita mientras el período esté
    activo y no haya vencido la fecha límite de matrícula.
C2  El retiro no borra el registro: el detalle pasa a estado "retirada" y guarda la fecha.
C3  El cupo se recupera de inmediato porque los cupos se cuentan solo con detalles "inscrita".
C4  Si se retiran todas las asignaturas, la matrícula queda "sin asignaturas vigentes";
    vuelve a "activa" si el estudiante matricula de nuevo dentro del plazo.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from django.db import IntegrityError, transaction
from django.db.models import Count, F, Q
from django.utils import timezone

from academics.models import Asignatura, Horario, PeriodoAcademico, Seccion

from .models import DetalleMatricula, Matricula


# --------------------------------------------------------------------------- #
# Tipos de resultado
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Incidencia:
    """Motivo comprensible por el que no se puede completar una operación."""

    regla: str          # Código de la regla incumplida (p. ej. "CUPO_AGOTADO").
    mensaje: str        # Texto pensado para el estudiante.
    seccion_id: int | None = None


class MatriculaRechazada(Exception):
    """La operación no cumple las reglas. Contiene todas las incidencias encontradas."""

    def __init__(self, incidencias: list[Incidencia]):
        self.incidencias = incidencias
        super().__init__("; ".join(i.mensaje for i in incidencias))


@dataclass
class ResultadoMatricula:
    matricula: Matricula
    detalles_creados: list[DetalleMatricula] = field(default_factory=list)


# Códigos de reglas (se muestran en el laboratorio y en las pruebas).
SIN_SELECCION = "SIN_SELECCION"
FUERA_DE_PERIODO = "FUERA_DE_PERIODO"
SECCION_INVALIDA = "SECCION_INVALIDA"
ASIGNATURA_DUPLICADA = "ASIGNATURA_DUPLICADA"
CUPO_AGOTADO = "CUPO_AGOTADO"
CRUCE_HORARIO = "CRUCE_HORARIO"
RETIRO_NO_PERMITIDO = "RETIRO_NO_PERMITIDO"


# --------------------------------------------------------------------------- #
# Consultas de apoyo
# --------------------------------------------------------------------------- #

def periodo_activo() -> PeriodoAcademico | None:
    return PeriodoAcademico.actual()


def estado_periodo(periodo: PeriodoAcademico | None, hoy=None) -> Incidencia | None:
    """Devuelve una incidencia si la matrícula no está habilitada; None si lo está."""
    hoy = hoy or timezone.localdate()
    if periodo is None:
        return Incidencia(FUERA_DE_PERIODO, "No hay un período académico activo. La matrícula no está habilitada.")
    if periodo.estado != PeriodoAcademico.Estado.ACTIVO:
        return Incidencia(FUERA_DE_PERIODO, f"El período {periodo.nombre} no está activo.")
    if hoy > periodo.fecha_limite_matricula:
        return Incidencia(
            FUERA_DE_PERIODO,
            f"La matrícula del período {periodo.nombre} cerró el "
            f"{periodo.fecha_limite_matricula:%d/%m/%Y}.",
        )
    return None


def secciones_ofertadas(periodo: PeriodoAcademico | None):
    """Secciones del período con asignatura activa, cupos calculados y horarios precargados."""
    if periodo is None:
        return Seccion.objects.none()
    return (
        Seccion.objects.filter(periodo=periodo, asignatura__estado=Asignatura.Estado.ACTIVA)
        .select_related("asignatura", "asignatura__carrera", "docente", "periodo")
        .prefetch_related("horarios")
        .con_cupos()
        .order_by("asignatura__semestre_recomendado", "asignatura__nombre", "paralelo")
    )


def matricula_de(estudiante, periodo) -> Matricula | None:
    if periodo is None:
        return None
    return Matricula.objects.filter(estudiante=estudiante, periodo=periodo).first()


def detalles_vigentes(estudiante, periodo):
    return (
        DetalleMatricula.objects.filter(
            matricula__estudiante=estudiante,
            matricula__periodo=periodo,
            estado=DetalleMatricula.Estado.INSCRITA,
        )
        .select_related("seccion", "seccion__asignatura", "seccion__docente")
        .prefetch_related("seccion__horarios")
    )


def _cruce(horarios_a, horarios_b) -> Horario | None:
    for ha in horarios_a:
        for hb in horarios_b:
            if ha.se_cruza_con(hb):
                return ha
    return None


# --------------------------------------------------------------------------- #
# Validación (sin efectos secundarios)
# --------------------------------------------------------------------------- #

def validar_seleccion(estudiante, seccion_ids, hoy=None) -> list[Incidencia]:
    """Evalúa todas las reglas sobre una selección y devuelve las incidencias encontradas.

    No modifica la base de datos. Se usa para la vista previa y antes de confirmar.
    """
    incidencias: list[Incidencia] = []
    ids = _normalizar_ids(seccion_ids)

    if not ids:
        return [Incidencia(SIN_SELECCION, "Debes seleccionar al menos una asignatura para confirmar la matrícula.")]

    periodo = periodo_activo()
    problema_periodo = estado_periodo(periodo, hoy)
    if problema_periodo:
        return [problema_periodo]

    secciones = {s.pk: s for s in secciones_ofertadas(periodo).filter(pk__in=ids)}
    for sid in ids:
        if sid not in secciones:
            incidencias.append(Incidencia(
                SECCION_INVALIDA,
                "Una de las secciones seleccionadas no pertenece a la oferta del período activo.",
                sid,
            ))

    vigentes = list(detalles_vigentes(estudiante, periodo))
    asignaturas_inscritas = {d.seccion.asignatura_id: d.seccion for d in vigentes}

    vistas: dict[int, Seccion] = {}
    aceptadas: list[Seccion] = []
    for sid in ids:
        seccion = secciones.get(sid)
        if seccion is None:
            continue
        asignatura = seccion.asignatura

        # R1: misma asignatura ya inscrita o elegida dos veces en esta selección.
        if asignatura.pk in asignaturas_inscritas:
            previa = asignaturas_inscritas[asignatura.pk]
            incidencias.append(Incidencia(
                ASIGNATURA_DUPLICADA,
                f"Ya tienes matriculada {asignatura.nombre} (paralelo {previa.paralelo}) en este período.",
                sid,
            ))
            continue
        if asignatura.pk in vistas:
            incidencias.append(Incidencia(
                ASIGNATURA_DUPLICADA,
                f"Seleccionaste dos paralelos de {asignatura.nombre}. Elige solo uno.",
                sid,
            ))
            continue
        vistas[asignatura.pk] = seccion

        # R2: cupos calculados desde los detalles inscritos reales.
        if seccion.cupos_disponibles <= 0:
            incidencias.append(Incidencia(
                CUPO_AGOTADO,
                f"{asignatura.nombre} (paralelo {seccion.paralelo}) no tiene cupos disponibles "
                f"({seccion.cupos_ocupados}/{seccion.capacidad_maxima} ocupados).",
                sid,
            ))
            continue

        # R3: cruce con asignaturas ya inscritas o con otras de la selección.
        horarios = list(seccion.horarios.all())
        choque = None
        for previa in vigentes:
            h = _cruce(horarios, list(previa.seccion.horarios.all()))
            if h:
                choque = (previa.seccion, h, "ya inscrita")
                break
        if not choque:
            for otra in aceptadas:
                h = _cruce(horarios, list(otra.horarios.all()))
                if h:
                    choque = (otra, h, "también seleccionada")
                    break
        if choque:
            otra, h, origen = choque
            incidencias.append(Incidencia(
                CRUCE_HORARIO,
                f"{asignatura.nombre} (paralelo {seccion.paralelo}) se cruza el {h} con "
                f"{otra.asignatura.nombre} (paralelo {otra.paralelo}), {origen}.",
                sid,
            ))
            continue

        aceptadas.append(seccion)

    return incidencias


def _normalizar_ids(seccion_ids) -> list[int]:
    ids: list[int] = []
    for valor in seccion_ids or []:
        try:
            numero = int(valor)
        except (TypeError, ValueError):
            continue
        # Se descartan valores fuera del rango de un entero de SQLite (64 bits).
        if 0 < numero < 2**63 and numero not in ids:
            ids.append(numero)
    return ids


# --------------------------------------------------------------------------- #
# Operaciones con efectos
# --------------------------------------------------------------------------- #

def confirmar_matricula(estudiante, seccion_ids, hoy=None) -> ResultadoMatricula:
    """Registra la matrícula de forma atómica (R9).

    Se vuelve a validar dentro de la transacción para que los cupos se lean
    en el mismo momento en que se escribe. Si cualquier regla falla, se lanza
    MatriculaRechazada y no queda ningún registro parcial.
    """
    ids = _normalizar_ids(seccion_ids)
    try:
        with transaction.atomic():
            # Bloquea las filas de las secciones en motores que lo soportan;
            # en SQLite la transacción de escritura ya serializa las operaciones.
            list(Seccion.objects.select_for_update().filter(pk__in=ids).values_list("pk", flat=True))

            incidencias = validar_seleccion(estudiante, ids, hoy)
            if incidencias:
                raise MatriculaRechazada(incidencias)

            periodo = periodo_activo()
            matricula, _ = Matricula.objects.get_or_create(estudiante=estudiante, periodo=periodo)
            if matricula.estado != Matricula.Estado.ACTIVA:
                matricula.estado = Matricula.Estado.ACTIVA
                matricula.save(update_fields=["estado"])

            creados = []
            for seccion in Seccion.objects.filter(pk__in=ids).select_related("asignatura"):
                creados.append(DetalleMatricula.objects.create(
                    matricula=matricula, seccion=seccion, asignatura=seccion.asignatura
                ))

            # Comprobación final de cupos tras escribir (defensa ante concurrencia).
            excedidas = (
                Seccion.objects.filter(pk__in=ids)
                .annotate(n=Count("detalles", filter=Q(detalles__estado=DetalleMatricula.Estado.INSCRITA)))
                .filter(n__gt=F("capacidad_maxima"))
            )
            if excedidas.exists():
                raise MatriculaRechazada([
                    Incidencia(CUPO_AGOTADO, f"{s.asignatura.nombre} (paralelo {s.paralelo}) se quedó sin cupos.", s.pk)
                    for s in excedidas.select_related("asignatura")
                ])
    except IntegrityError:
        # La restricción de la base de datos actúa como última barrera (R1).
        raise MatriculaRechazada([Incidencia(
            ASIGNATURA_DUPLICADA, "La base de datos rechazó una asignatura duplicada. No se guardó ningún cambio."
        )])

    matricula.refresh_from_db()
    return ResultadoMatricula(matricula=matricula, detalles_creados=creados)


def retirar_asignatura(estudiante, detalle_id, hoy=None) -> DetalleMatricula:
    """Retira una asignatura propia respetando el plazo del período (C1–C4, R10)."""
    with transaction.atomic():
        detalle = (
            DetalleMatricula.objects.select_for_update()
            .select_related("matricula", "matricula__periodo", "seccion__asignatura")
            .filter(pk=detalle_id, matricula__estudiante=estudiante)
            .first()
        )
        if detalle is None:
            # No se distingue entre "no existe" y "es de otra persona" (R10).
            raise MatriculaRechazada([Incidencia(RETIRO_NO_PERMITIDO, "La asignatura indicada no forma parte de tu matrícula.")])
        if detalle.estado != DetalleMatricula.Estado.INSCRITA:
            raise MatriculaRechazada([Incidencia(RETIRO_NO_PERMITIDO, "Esta asignatura ya fue retirada.")])

        problema = estado_periodo(detalle.matricula.periodo, hoy)
        if problema:
            raise MatriculaRechazada([Incidencia(
                RETIRO_NO_PERMITIDO,
                "El plazo para retirar asignaturas terminó: " + problema.mensaje,
            )])

        detalle.estado = DetalleMatricula.Estado.RETIRADA
        detalle.fecha_retiro = timezone.now()
        detalle.save(update_fields=["estado", "fecha_retiro"])

        matricula = detalle.matricula
        if not matricula.detalles.filter(estado=DetalleMatricula.Estado.INSCRITA).exists():
            matricula.estado = Matricula.Estado.SIN_ASIGNATURAS
            matricula.save(update_fields=["estado"])
    return detalle
