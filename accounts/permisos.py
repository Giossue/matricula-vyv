"""Control de acceso por rol."""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def rol_requerido(*roles):
    """Exige sesión iniciada y uno de los roles indicados; si no, responde 403."""

    def decorador(vista):
        @login_required
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            if request.user.rol not in roles:
                raise PermissionDenied("Tu rol no tiene acceso a esta sección.")
            return vista(request, *args, **kwargs)

        return envoltura

    return decorador


def solo_administrador(vista):
    from .models import Usuario

    return rol_requerido(Usuario.Rol.ADMINISTRADOR)(vista)


def solo_estudiante(vista):
    from .models import Usuario

    @rol_requerido(Usuario.Rol.ESTUDIANTE)
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if not hasattr(request.user, "estudiante"):
            raise PermissionDenied("Tu cuenta no tiene un perfil de estudiante asociado.")
        return vista(request, *args, **kwargs)

    return envoltura
