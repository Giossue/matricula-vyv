from django.contrib.auth import views as auth_views
from django.db.models import Count, Q
from django.shortcuts import redirect, render

from academics.models import Carrera

from .forms import IngresoForm
from .models import Estudiante
from .permisos import solo_administrador


class IngresoView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = IngresoForm
    redirect_authenticated_user = True


def inicio(request):
    """Punto de entrada: dirige a cada rol a su panel."""
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    if request.user.es_administrador:
        return redirect("academics:panel")
    return redirect("enrollments:panel")


@solo_administrador
def estudiantes(request):
    consulta = request.GET.get("q", "").strip()
    carrera_id = request.GET.get("carrera", "")
    qs = Estudiante.objects.select_related("usuario", "carrera").annotate(
        asignaturas_vigentes=Count(
            "matriculas__detalles",
            filter=Q(matriculas__periodo__estado="activo", matriculas__detalles__estado="inscrita"),
        )
    )
    if consulta:
        qs = qs.filter(
            Q(usuario__nombre__icontains=consulta)
            | Q(usuario__apellido__icontains=consulta)
            | Q(codigo_estudiantil__icontains=consulta)
        )
    if carrera_id.isdigit():
        qs = qs.filter(carrera_id=int(carrera_id))
    return render(request, "accounts/estudiantes.html", {
        "estudiantes": qs,
        "carreras": Carrera.objects.all(),
        "q": consulta,
        "carrera_sel": carrera_id,
        "seccion_activa": "estudiantes",
    })
