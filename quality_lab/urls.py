from django.urls import path

from . import views

app_name = "quality_lab"

urlpatterns = [
    path("", views.laboratorio, name="laboratorio"),
    path("verificacion/", views.verificacion_view, name="verificacion"),
    path("verificacion/ejecutar/", views.ejecutar, name="ejecutar"),
    path("validacion/", views.validacion, name="validacion"),
]
