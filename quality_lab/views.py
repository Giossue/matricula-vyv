from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST

from accounts.permisos import solo_administrador

from . import verificacion
from .forms import EvaluacionForm
from .models import ConfiguracionDemo, EvaluacionExperiencia


@solo_administrador
def laboratorio(request):
    reporte = verificacion.leer_reporte()
    return render(request, "quality_lab/laboratorio.html", {
        "seccion_activa": "laboratorio",
        "reporte": reporte,
        "n_evaluaciones": EvaluacionExperiencia.objects.count(),
        "version": ConfiguracionDemo.obtener().version_experiencia,
    })


@solo_administrador
def verificacion_view(request):
    reporte = verificacion.leer_reporte()
    casos = verificacion.casos_con_resultado(reporte)
    otras = [r for r in (reporte or {}).get("registros", []) if not r.get("caso")]
    fecha = parse_datetime(reporte.get("ejecutado_en") or "") if reporte else None
    if fecha and timezone.is_naive(fecha):
        fecha = timezone.make_aware(fecha)
    bd = (reporte or {}).get("base_datos_pruebas", "")
    return render(request, "quality_lab/verificacion.html", {
        "seccion_activa": "laboratorio",
        "reporte": reporte,
        "casos": casos,
        "otras": otras,
        "casos_aprobados": sum(1 for c in casos if c["estado"] == "aprobado"),
        "fecha_ejecucion": timezone.localtime(fecha) if fecha else None,
        "bd_pruebas": "SQLite en memoria (temporal y aislada)" if "memory" in bd else bd,
    })


@solo_administrador
@require_POST
def ejecutar(request):
    alcance = request.POST.get("alcance", "completa")
    etiquetas = ["quality_lab.tests.test_verificacion"] if alcance == "casos" else []
    try:
        reporte = verificacion.ejecutar_pruebas(etiquetas)
    except verificacion.EjecucionEnCurso as exc:
        messages.warning(request, str(exc))
    else:
        if reporte["total"] == 0:
            messages.error(request, "La ejecución no produjo resultados. Revisa la salida del comando.")
        elif reporte["fallidas"]:
            messages.error(request, f"{reporte['fallidas']} de {reporte['total']} pruebas fallaron. Revisa los detalles.")
        else:
            messages.success(request, f"{reporte['aprobadas']} de {reporte['total']} pruebas aprobadas en {reporte['duracion_s']} s.")
    return redirect("quality_lab:verificacion")


def _resumen_por_version():
    resumen = {}
    for version, etiqueta in EvaluacionExperiencia.Version.choices:
        datos = EvaluacionExperiencia.objects.filter(version=version).aggregate(
            n=Count("id"),
            facilidad=Avg("facilidad_seleccion"),
            horarios=Avg("comprension_horarios"),
            informacion=Avg("informacion_suficiente"),
        )
        resumen[version] = {"etiqueta": etiqueta, **datos}
    return resumen


@solo_administrador
def validacion(request):
    return render(request, "quality_lab/validacion.html", {
        "seccion_activa": "laboratorio",
        "version": ConfiguracionDemo.obtener().version_experiencia,
        "resumen": _resumen_por_version(),
        "evaluaciones": EvaluacionExperiencia.objects.select_related("usuario")[:50],
        "modo_demo": settings.CAMPUSFLOW_MODO_DEMO,
    })


@login_required
def evaluar(request):
    inicial = {"version": request.GET.get("version") or ConfiguracionDemo.obtener().version_experiencia}
    form = EvaluacionForm(request.POST or None, initial=inicial)
    if request.method == "POST" and form.is_valid():
        evaluacion = form.save(commit=False)
        evaluacion.usuario = request.user
        evaluacion.save()
        messages.success(request, "Gracias. Tu opinión quedó registrada para el análisis de validación.")
        return redirect("inicio")
    return render(request, "quality_lab/evaluar.html", {"form": form, "seccion_activa": "evaluar"})
