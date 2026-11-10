from django.urls import path

from . import views

app_name = "enrollments"

urlpatterns = [
    path("", views.panel, name="panel"),
    path("oferta/", views.oferta, name="oferta"),
    path("matricula/", views.matricula, name="matricula"),
    path("matricula/validar/", views.validar, name="validar"),
    path("matricula/confirmar/", views.confirmar, name="confirmar"),
    path("matricula/<int:pk>/", views.comprobante, name="comprobante"),
    path("mis-asignaturas/", views.mis_asignaturas, name="mis_asignaturas"),
    path("mis-asignaturas/<int:pk>/retirar/", views.retirar, name="retirar"),
]

admin_urlpatterns = [
    path("", views.admin_matriculas, name="admin_matriculas"),
    path("<int:pk>/", views.admin_matricula_detalle, name="admin_matricula_detalle"),
]

demo_urlpatterns = [
    path("version/", views.demo_version, name="demo_version"),
    path("validacion-navegador/", views.demo_validacion_cliente, name="demo_validacion_cliente"),
]
