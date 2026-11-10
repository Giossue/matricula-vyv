from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import Estudiante
from accounts.permisos import solo_administrador
from enrollments.models import DetalleMatricula, Matricula

from .forms import AsignaturaForm, DocenteForm, HorarioFormSet, PeriodoForm, SeccionForm
from .models import Asignatura, Carrera, Docente, PeriodoAcademico, Seccion


def _formulario(request, form_class, instancia, plantilla_ctx, exito, url_retorno):
    form = form_class(request.POST or None, instance=instancia)
    if request.method == "POST" and form.is_valid():
        objeto = form.save()
        messages.success(request, exito.format(obj=objeto))
        return redirect(url_retorno)
    plantilla_ctx["form"] = form
    return render(request, "academics/formulario.html", plantilla_ctx)


# --------------------------------------------------------------------------- #
# Panel
# --------------------------------------------------------------------------- #

@solo_administrador
def panel(request):
    periodo = PeriodoAcademico.actual()
    secciones = (
        Seccion.objects.filter(periodo=periodo).select_related("asignatura", "docente").con_cupos()
        if periodo else Seccion.objects.none()
    )
    secciones = list(secciones)
    criticas = sorted(secciones, key=lambda s: (s.cupos_disponibles, s.asignatura.nombre))[:6]
    capacidad_total = sum(s.capacidad_maxima for s in secciones)
    ocupados_total = sum(s.cupos_ocupados for s in secciones)
    ultimas = (
        DetalleMatricula.objects.filter(matricula__periodo=periodo)
        .select_related("matricula__estudiante__usuario", "seccion__asignatura")
        .order_by("-fecha_registro")[:8]
        if periodo else []
    )
    return render(request, "academics/panel.html", {
        "seccion_activa": "panel",
        "periodo": periodo,
        "total_estudiantes": Estudiante.objects.count(),
        "total_asignaturas": Asignatura.objects.filter(estado=Asignatura.Estado.ACTIVA).count(),
        "total_secciones": len(secciones),
        "total_matriculas": Matricula.objects.filter(periodo=periodo, estado=Matricula.Estado.ACTIVA).count()
        if periodo else 0,
        "capacidad_total": capacidad_total,
        "ocupados_total": ocupados_total,
        "ocupacion_pct": round(ocupados_total * 100 / capacidad_total) if capacidad_total else 0,
        "secciones_llenas": sum(1 for s in secciones if s.cupos_disponibles == 0),
        "criticas": criticas,
        "ultimas": ultimas,
    })


# --------------------------------------------------------------------------- #
# Asignaturas
# --------------------------------------------------------------------------- #

@solo_administrador
def asignaturas(request):
    q = request.GET.get("q", "").strip()
    carrera = request.GET.get("carrera", "")
    estado = request.GET.get("estado", "")
    qs = Asignatura.objects.select_related("carrera").annotate(n_secciones=Count("secciones"))
    if q:
        qs = qs.filter(Q(nombre__icontains=q) | Q(codigo__icontains=q))
    if carrera.isdigit():
        qs = qs.filter(carrera_id=int(carrera))
    if estado in Asignatura.Estado.values:
        qs = qs.filter(estado=estado)
    return render(request, "academics/asignaturas.html", {
        "seccion_activa": "asignaturas", "asignaturas": qs, "carreras": Carrera.objects.all(),
        "q": q, "carrera_sel": carrera, "estado_sel": estado, "estados": Asignatura.Estado.choices,
    })


@solo_administrador
def asignatura_form(request, pk=None):
    instancia = get_object_or_404(Asignatura, pk=pk) if pk else None
    return _formulario(
        request, AsignaturaForm, instancia,
        {"seccion_activa": "asignaturas", "titulo": "Editar asignatura" if pk else "Nueva asignatura",
         "volver": "academics:asignaturas"},
        "Asignatura «{obj.nombre}» guardada.", "academics:asignaturas",
    )


@solo_administrador
@require_POST
def asignatura_estado(request, pk):
    asignatura = get_object_or_404(Asignatura, pk=pk)
    if asignatura.activa:
        asignatura.estado = Asignatura.Estado.INACTIVA
        messages.success(request, f"«{asignatura.nombre}» fue desactivada: ya no aparece en la oferta de matrícula.")
    else:
        asignatura.estado = Asignatura.Estado.ACTIVA
        messages.success(request, f"«{asignatura.nombre}» fue activada.")
    asignatura.save(update_fields=["estado"])
    return redirect("academics:asignaturas")


# --------------------------------------------------------------------------- #
# Períodos
# --------------------------------------------------------------------------- #

@solo_administrador
def periodos(request):
    qs = PeriodoAcademico.objects.annotate(
        n_secciones=Count("secciones", distinct=True),
        n_matriculas=Count("matriculas", distinct=True),
    )
    return render(request, "academics/periodos.html", {"seccion_activa": "periodos", "periodos": qs})


@solo_administrador
def periodo_form(request, pk=None):
    instancia = get_object_or_404(PeriodoAcademico, pk=pk) if pk else None
    return _formulario(
        request, PeriodoForm, instancia,
        {"seccion_activa": "periodos", "titulo": "Editar período" if pk else "Nuevo período",
         "volver": "academics:periodos",
         "ayuda": "Solo puede existir un período activo. La matrícula y los retiros se permiten mientras "
                  "el período esté activo y no haya vencido la fecha límite de matrícula."},
        "Período «{obj.nombre}» guardado.", "academics:periodos",
    )


# --------------------------------------------------------------------------- #
# Docentes
# --------------------------------------------------------------------------- #

@solo_administrador
def docentes(request):
    periodo = PeriodoAcademico.actual()
    qs = Docente.objects.annotate(n_secciones=Count("secciones", filter=Q(secciones__periodo=periodo)))
    return render(request, "academics/docentes.html", {"seccion_activa": "docentes", "docentes": qs, "periodo": periodo})


@solo_administrador
def docente_form(request, pk=None):
    instancia = get_object_or_404(Docente, pk=pk) if pk else None
    return _formulario(
        request, DocenteForm, instancia,
        {"seccion_activa": "docentes", "titulo": "Editar docente" if pk else "Nuevo docente",
         "volver": "academics:docentes"},
        "Docente «{obj}» guardado.", "academics:docentes",
    )


# --------------------------------------------------------------------------- #
# Secciones y horarios
# --------------------------------------------------------------------------- #

def _periodo_filtrado(request):
    valor = request.GET.get("periodo", "")
    if valor.isdigit():
        return PeriodoAcademico.objects.filter(pk=int(valor)).first()
    return PeriodoAcademico.actual()


@solo_administrador
def secciones(request):
    periodo = _periodo_filtrado(request)
    q = request.GET.get("q", "").strip()
    qs = (
        Seccion.objects.filter(periodo=periodo)
        .select_related("asignatura", "docente", "periodo")
        .prefetch_related("horarios")
        .con_cupos()
        .order_by("asignatura__nombre", "paralelo")
    )
    if q:
        qs = qs.filter(Q(asignatura__nombre__icontains=q) | Q(asignatura__codigo__icontains=q) | Q(docente__apellido__icontains=q))
    return render(request, "academics/secciones.html", {
        "seccion_activa": "secciones", "secciones": qs, "periodo": periodo,
        "periodos": PeriodoAcademico.objects.all(), "q": q,
    })


@solo_administrador
def seccion_form(request, pk=None):
    instancia = get_object_or_404(Seccion, pk=pk) if pk else Seccion(periodo=PeriodoAcademico.actual())
    form = SeccionForm(request.POST or None, instance=instancia)
    formset = HorarioFormSet(request.POST or None, instance=instancia, prefix="horarios")
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            seccion = form.save()
            formset.instance = seccion
            formset.save()
        messages.success(request, f"Sección «{seccion}» guardada con {seccion.horarios.count()} bloque(s) de horario.")
        return redirect(f"{_url('academics:secciones')}?periodo={seccion.periodo_id}")
    inscritos = instancia.cupos_ocupados if instancia.pk else 0
    return render(request, "academics/seccion_form.html", {
        "seccion_activa": "secciones", "form": form, "formset": formset,
        "titulo": "Editar sección" if pk else "Nueva sección", "inscritos": inscritos, "objeto": instancia,
    })


@solo_administrador
def cupos(request):
    periodo = _periodo_filtrado(request)
    qs = list(
        Seccion.objects.filter(periodo=periodo)
        .select_related("asignatura", "asignatura__carrera", "docente")
        .con_cupos()
        .order_by("asignatura__carrera__nombre", "asignatura__nombre", "paralelo")
    )
    return render(request, "academics/cupos.html", {
        "seccion_activa": "cupos", "secciones": qs, "periodo": periodo,
        "periodos": PeriodoAcademico.objects.all(),
        "capacidad": sum(s.capacidad_maxima for s in qs),
        "ocupados": sum(s.cupos_ocupados for s in qs),
    })


def _url(nombre):
    from django.urls import reverse

    return reverse(nombre)
