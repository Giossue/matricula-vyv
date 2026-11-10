from django import template
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def icono(nombre, clase=""):
    """Inserta un icono SVG del sprite definido en includes/iconos.html."""
    return format_html(
        '<svg class="icon {}" aria-hidden="true" focusable="false"><use href="#i-{}"></use></svg>', clase, nombre
    )


@register.filter
def clave(diccionario, llave):
    """Permite leer diccionario[llave] desde la plantilla."""
    try:
        return diccionario.get(llave)
    except AttributeError:
        return None


@register.filter
def nivel_ocupacion(seccion):
    """Clase visual según la ocupación real de la sección."""
    if seccion.cupos_disponibles == 0:
        return "lleno"
    if seccion.porcentaje_ocupacion >= 75:
        return "alto"
    return "normal"
