"""Test runner que, además de ejecutar las pruebas, guarda un reporte JSON.

Se usa con:  python manage.py test --testrunner=quality_lab.runner.VyVRunner
El reporte se escribe en la ruta indicada por la variable CAMPUSFLOW_REPORTE_VYV.
"""

import json
import os
import time
import traceback
import unittest

from django.test.runner import DiscoverRunner


def _metodo(test):
    return getattr(test, getattr(test, "_testMethodName", ""), None)


class ResultadoVyV(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.registros = []
        self._inicios = {}

    def startTest(self, test):
        self._inicios[test.id()] = time.perf_counter()
        super().startTest(test)

    def _registrar(self, test, estado, detalle=""):
        inicio = self._inicios.pop(test.id(), None)
        metodo = _metodo(test)
        self.registros.append({
            "id": test.id(),
            "caso": getattr(metodo, "_caso_vyv", None),
            "descripcion": (getattr(metodo, "__doc__", None) or "").strip().splitlines()[0:1],
            "estado": estado,
            "duracion_ms": round((time.perf_counter() - inicio) * 1000, 1) if inicio else None,
            "datos_utilizados": getattr(test, "datos_utilizados", None),
            "obtenido": getattr(test, "obtenido", None),
            "detalle": detalle[-1500:],
        })

    def addSuccess(self, test):
        super().addSuccess(test)
        self._registrar(test, "aprobado")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._registrar(test, "fallido", "".join(traceback.format_exception_only(err[0], err[1])))

    def addError(self, test, err):
        super().addError(test, err)
        self._registrar(test, "error", "".join(traceback.format_exception(*err)))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._registrar(test, "omitido", reason)

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self._registrar(test, "aprobado")

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self._registrar(test, "fallido", "Éxito inesperado")


class VyVRunner(DiscoverRunner):
    def get_resultclass(self):
        return ResultadoVyV

    def run_suite(self, suite, **kwargs):
        resultado = super().run_suite(suite, **kwargs)
        ruta = os.environ.get("CAMPUSFLOW_REPORTE_VYV")
        if ruta:
            for r in getattr(resultado, "registros", []):
                r["descripcion"] = r["descripcion"][0] if r["descripcion"] else ""
            datos = {
                "total": resultado.testsRun,
                "registros": getattr(resultado, "registros", []),
                "base_datos_pruebas": self._descripcion_bd(),
            }
            with open(ruta, "w", encoding="utf-8") as archivo:
                json.dump(datos, archivo, ensure_ascii=False, indent=2)
        return resultado

    @staticmethod
    def _descripcion_bd():
        from django.db import connection

        nombre = connection.settings_dict.get("NAME")
        return str(nombre)
