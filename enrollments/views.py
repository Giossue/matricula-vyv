from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q, Sum
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.permisos import solo_administrador, solo_estudiante
from academics.models import Carrera, PeriodoAcademico
from quality_lab.models import ConfiguracionDemo

from . import services
from .models import DetalleMatricula, Matricula

SESION_OMITIR_VALIDACION = "vyv_omitir_validacion_cliente"


# --------------------------------------------------------------------------- #
# Utilidades de presentación
# --------------------------------------------------------------------------- #

def _bloques(seccion):
    return [
        {"dia": h.dia_semana, "inicio": h.hora_inicio.strftime("%H:%M"), "fin": h.hora_fin.strftime("%H:%M"),
         "texto": str(h)}
        for h in seccion.horarios.all()
    ]


def _seccion_json(seccion, inscrita=False):
    return {
        "id": seccion.pk,
        "asignatura_id": seccion.asignatura_id,
        "asignatura": seccion.asignatura.nombre,
        "codigo": seccion.asignatura.codigo,
        "paralelo": seccion.paralelo,
        "docente": str(seccion.docente),
        "creditos": seccion.asignatura.creditos,
        "cupos": seccion.cupos_disponibles,
        "capacidad": seccion.capacidad_maxima,
        "horarios": _bloques(seccion),
        "inscrita": inscrita,
    }


def _agrupar_por_asignatura(secciones):
    grupos = {}
    for s in secciones:
        grupos.setdefault(s.asignatura_id, {"asignatura": s.asignatura, "secciones": []})["secciones"].append(s)
    return list(grupos.values())


def _version_activa():
    return ConfiguracionDemo.obtener().version_experiencia if settings.CAMPUSFLOW_MODO_DEMO else "B"


def _redirigir_a_siguiente(request, por_defecto):
    destino = request.POST.get("siguiente") or request.GET.get("siguiente")
    if destino and url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
        return redirect(destino)
    return redirect(por_defecto)


# --------------------------------------------------------------------------- #
# Estudiante
# --------------------------------------------------------------------------- #

@solo_estudiante
def panel(request):
    estudiante = request.user.estudiante
    periodo = services.periodo_activo()
    vigentes = list(services.detalles_vigentes(estudiante, periodo)) if periodo else []
    problema = services.estado_periodo(periodo)
    dias_restantes = (periodo.fecha_limite_matricula - timezone.localdate()).days if periodo else None
    return render(request, "enrollments/panel.html", {
        "seccion_activa": "panel",
        "estudiante": estudiante,
        "periodo": periodo,
        "matricula": services.matricula_de(estudiante, periodo),
        "vigentes": vigentes,
        "creditos": sum(d.seccion.asignatura.creditos for d in vigentes),
        "matricula_abierta": problema is None,
        "problema_periodo": problema,
        "dias_restantes": dias_restantes,
        "historial": Matricula.objects.filter(estudiante=estudiante).select_related("periodo")
        .annotate(n=Count("detalles", filter=Q(detalles__estado="inscrita"))),
    })


@solo_estudiante
def oferta(request):
    periodo = services.periodo_activo()
    q = request.GET.get("q", "").strip()
    carrera = request.GET.get("carrera", "")
    qs = services.secciones_ofertadas(periodo)
    if q:
        qs = qs.filter(Q(asignatura__nombre__icontains=q) | Q(asignatura__codigo__icontains=q))
    if carrera.isdigit():
        qs = qs.filter(asignatura__carrera_id=int(carrera))
    return render(request, "enrollments/oferta.html", {
        "seccion_activa": "oferta", "periodo": periodo, "grupos": _agrupar_por_asignatura(qs),
        "carreras": Carrera.objects.all(), "q": q, "carrera_sel": carrera,
        "total_secciones": len(qs),
    })


def _contexto_matricula(request, seleccion=None, incidencias=None):
    estudiante = request.user.estudiante
    periodo = services.periodo_activo()
    secciones = list(services.secciones_ofertadas(periodo))
    vigentes = list(services.detalles_vigentes(estudiante, periodo)) if periodo else []
    inscritas_asig = {d.seccion.asignatura_id for d in vigentes}
    for s in secciones:
        s.ya_inscrita = s.asignatura_id in inscritas_asig
        s.bloqueada = s.ya_inscrita or s.cupos_disponibles == 0
    problema = services.estado_periodo(periodo)
    version = _version_activa()
    omitir = bool(request.session.get(SESION_OMITIR_VALIDACION)) and settings.CAMPUSFLOW_MODO_DEMO
    return {
        "seccion_activa": "matricula",
        "estudiante": estudiante,
        "periodo": periodo,
        "problema_periodo": problema,
        "matricula_abierta": problema is None,
        "grupos": _agrupar_por_asignatura(secciones),
        "vigentes": vigentes,
        "asignaturas_inscritas": inscritas_asig,
        "creditos_vigentes": sum(d.seccion.asignatura.creditos for d in vigentes),
        "seleccion": [int(x) for x in (seleccion or []) if str(x).isdigit()],
        "incidencias": incidencias or [],
        "errores_seccion": {i.seccion_id: i.mensaje for i in (incidencias or []) if i.seccion_id},
        "version": version,
        "mostrar_toggle_validacion": True,
        "omitir_validacion": omitir,
        "datos_oferta": [_seccion_json(s, s.asignatura_id in inscritas_asig) for s in secciones],
        "datos_vigentes": [_seccion_json(d.seccion, True) for d in vigentes],
    }


@solo_estudiante
def matricula(request):
    ctx = _contexto_matricula(request)
    plantilla = "enrollments/matricula_b.html" if ctx["version"] == "B" else "enrollments/matricula_a.html"
    return render(request, plantilla, ctx)


@solo_estudiante
@require_POST
def confirmar(request):
    ids = request.POST.getlist("secciones")
    try:
        resultado = services.confirmar_matricula(request.user.estudiante, ids)
    except services.MatriculaRechazada as error:
        ctx = _contexto_matricula(request, seleccion=ids, incidencias=error.incidencias)
        plantilla = "enrollments/matricula_b.html" if ctx["version"] == "B" else "enrollments/matricula_a.html"
        return render(request, plantilla, ctx, status=422)
    nombres = ", ".join(d.seccion.asignatura.nombre for d in resultado.detalles_creados)
    messages.success(request, f"Matrícula registrada: {nombres}.")
    return redirect("enrollments:comprobante", pk=resultado.matricula.pk)


@solo_estudiante
@require_POST
def validar(request):
    """Comprobación previa (sin guardar) usada por la Versión B antes de confirmar."""
    incidencias = services.validar_seleccion(request.user.estudiante, request.POST.getlist("secciones"))
    return JsonResponse({
        "valida": not incidencias,
        "incidencias": [{"regla": i.regla, "mensaje": i.mensaje, "seccion_id": i.seccion_id} for i in incidencias],
    })


@solo_estudiante
def mis_asignaturas(request):
    estudiante = request.user.estudiante
    periodo = services.periodo_activo()
    vigentes = list(services.detalles_vigentes(estudiante, periodo)) if periodo else []
    retiradas = (
        DetalleMatricula.objects.filter(matricula__estudiante=estudiante, matricula__periodo=periodo,
                                        estado=DetalleMatricula.Estado.RETIRADA)
        .select_related("seccion__asignatura") if periodo else []
    )
    return render(request, "enrollments/mis_asignaturas.html", {
        "seccion_activa": "mis_asignaturas",
        "periodo": periodo,
        "matricula": services.matricula_de(estudiante, periodo),
        "vigentes": vigentes,
        "retiradas": retiradas,
        "creditos": sum(d.seccion.asignatura.creditos for d in vigentes),
        "puede_retirar": services.estado_periodo(periodo) is None,
        "version": _version_activa(),
        "datos_vigentes": [_seccion_json(d.seccion, True) for d in vigentes],
    })


@solo_estudiante
@require_POST
def retirar(request, pk):
    try:
        detalle = services.retirar_asignatura(request.user.estudiante, pk)
    except services.MatriculaRechazada as error:
        for incidencia in error.incidencias:
            messages.error(request, incidencia.mensaje)
    else:
        messages.success(
            request,
            f"Retiraste {detalle.seccion.asignatura.nombre} (paralelo {detalle.seccion.paralelo}). "
            "El cupo quedó disponible para otros estudiantes.",
        )
    return redirect("enrollments:mis_asignaturas")


@solo_estudiante
def comprobante(request, pk):
    # R10: solo se busca dentro de las matrículas del propio estudiante.
    matricula = get_object_or_404(
        Matricula.objects.select_related("periodo", "estudiante__usuario", "estudiante__carrera"),
        pk=pk, estudiante=request.user.estudiante,
    )
    detalles = matricula.detalles.select_related("seccion__asignatura", "seccion__docente").prefetch_related("seccion__horarios")
    return render(request, "enrollments/comprobante.html", {
        "seccion_activa": "mis_asignaturas", "matricula": matricula, "detalles": detalles,
        "creditos": sum(d.seccion.asignatura.creditos for d in detalles if d.estado == "inscrita"),
    })


# --------------------------------------------------------------------------- #
# Controles de la demostración VyV
# --------------------------------------------------------------------------- #

@login_required
@require_POST
def demo_version(request):
    if not settings.CAMPUSFLOW_MODO_DEMO:
        raise PermissionDenied("El modo demostración está desactivado.")
    version = request.POST.get("version")
    if version in ConfiguracionDemo.Version.values:
        config = ConfiguracionDemo.obtener()
        config.version_experiencia = version
        config.save()
        messages.info(request, f"Demostración: ahora se muestra la Versión {version} de la experiencia de matrícula.")
    return _redirigir_a_siguiente(request, "inicio")


@login_required
@require_POST
def demo_validacion_cliente(request):
    if not settings.CAMPUSFLOW_MODO_DEMO:
        raise PermissionDenied("El modo demostración está desactivado.")
    activo = not request.session.get(SESION_OMITIR_VALIDACION, False)
    request.session[SESION_OMITIR_VALIDACION] = activo
    if activo:
        messages.warning(request, "Validaciones del navegador desactivadas: ahora solo responde el backend.")
    else:
        messages.info(request, "Validaciones del navegador reactivadas.")
    return _redirigir_a_siguiente(request, "inicio")


# --------------------------------------------------------------------------- #
# Administración de matrículas
# --------------------------------------------------------------------------- #

@solo_administrador
def admin_matriculas(request):
    periodos = PeriodoAcademico.objects.all()
    valor = request.GET.get("periodo", "")
    periodo = periodos.filter(pk=int(valor)).first() if valor.isdigit() else PeriodoAcademico.actual()
    q = request.GET.get("q", "").strip()
    qs = (
        Matricula.objects.filter(periodo=periodo)
        .select_related("estudiante__usuario", "estudiante__carrera", "periodo")
        .annotate(
            n_vigentes=Count("detalles", filter=Q(detalles__estado="inscrita")),
            n_retiradas=Count("detalles", filter=Q(detalles__estado="retirada")),
            creditos=Sum("detalles__seccion__asignatura__creditos", filter=Q(detalles__estado="inscrita")),
        )
    )
    if q:
        qs = qs.filter(
            Q(estudiante__usuario__nombre__icontains=q) | Q(estudiante__usuario__apellido__icontains=q)
            | Q(estudiante__codigo_estudiantil__icontains=q)
        )
    return render(request, "enrollments/admin_matriculas.html", {
        "seccion_activa": "matriculas", "matriculas": qs, "periodo": periodo, "periodos": periodos, "q": q,
    })


@solo_administrador
def admin_matricula_detalle(request, pk):
    matricula = get_object_or_404(
        Matricula.objects.select_related("periodo", "estudiante__usuario", "estudiante__carrera"), pk=pk
    )
    detalles = matricula.detalles.select_related("seccion__asignatura", "seccion__docente").prefetch_related("seccion__horarios")
    return render(request, "enrollments/comprobante.html", {
        "seccion_activa": "matriculas", "matricula": matricula, "detalles": detalles, "vista_admin": True,
        "creditos": sum(d.seccion.asignatura.creditos for d in detalles if d.estado == "inscrita"),
    })
