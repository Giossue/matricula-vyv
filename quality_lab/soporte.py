"""Ayudas para escribir casos de verificación que el laboratorio pueda mostrar."""


def caso(identificador):
    """Marca una prueba con el identificador del catálogo (V01…V09)."""

    def decorador(funcion):
        funcion._caso_vyv = identificador
        return funcion

    return decorador


class CasoVyVMixin:
    """Permite a la prueba informar los datos que usó y el resultado que obtuvo."""

    datos_utilizados = None
    obtenido = None

    def registrar(self, datos=None, obtenido=None):
        if datos is not None:
            self.datos_utilizados = datos
        if obtenido is not None:
            self.obtenido = obtenido
