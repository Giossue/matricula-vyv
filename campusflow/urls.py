from django.urls import include, path

from accounts import views as accounts_views
from enrollments import urls as enrollments_urls
from quality_lab import views as quality_views

urlpatterns = [
    path("", accounts_views.inicio, name="inicio"),
    path("cuenta/", include("accounts.urls")),
    path("estudiante/", include("enrollments.urls")),
    path("administracion/", include("academics.urls")),
    path("administracion/estudiantes/", accounts_views.estudiantes, name="admin_estudiantes"),
    path("administracion/matriculas/", include((enrollments_urls.admin_urlpatterns, "matriculas_admin"))),
    path("administracion/laboratorio/", include("quality_lab.urls")),
    path("demo/", include((enrollments_urls.demo_urlpatterns, "demo"))),
    path("validacion/evaluar/", quality_views.evaluar, name="evaluar"),
]

handler403 = "campusflow.errores.prohibido"
handler404 = "campusflow.errores.no_encontrado"
