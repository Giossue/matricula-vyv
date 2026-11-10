from django.urls import path

from . import views

app_name = "academics"

urlpatterns = [
    path("", views.panel, name="panel"),
    path("asignaturas/", views.asignaturas, name="asignaturas"),
    path("asignaturas/nueva/", views.asignatura_form, name="asignatura_nueva"),
    path("asignaturas/<int:pk>/editar/", views.asignatura_form, name="asignatura_editar"),
    path("asignaturas/<int:pk>/estado/", views.asignatura_estado, name="asignatura_estado"),
    path("periodos/", views.periodos, name="periodos"),
    path("periodos/nuevo/", views.periodo_form, name="periodo_nuevo"),
    path("periodos/<int:pk>/editar/", views.periodo_form, name="periodo_editar"),
    path("docentes/", views.docentes, name="docentes"),
    path("docentes/nuevo/", views.docente_form, name="docente_nuevo"),
    path("docentes/<int:pk>/editar/", views.docente_form, name="docente_editar"),
    path("secciones/", views.secciones, name="secciones"),
    path("secciones/nueva/", views.seccion_form, name="seccion_nueva"),
    path("secciones/<int:pk>/editar/", views.seccion_form, name="seccion_editar"),
    path("cupos/", views.cupos, name="cupos"),
]
