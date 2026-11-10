from django.shortcuts import render


def prohibido(request, exception=None):
    return render(request, "errores/403.html", {"mensaje": str(exception or "")}, status=403)


def no_encontrado(request, exception=None):
    return render(request, "errores/404.html", status=404)
