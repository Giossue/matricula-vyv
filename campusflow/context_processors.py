from django.conf import settings


def campusflow(request):
    """Variables globales disponibles en todas las plantillas."""
    return {
        "MODO_DEMO": settings.CAMPUSFLOW_MODO_DEMO,
        "NOMBRE_SISTEMA": "CampusFlow",
    }
