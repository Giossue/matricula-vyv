"""Ejecuta la suite de pruebas de Django en un proceso aparte y guarda el reporte.

- Las pruebas corren con `manage.py test`, que crea una base de datos SQLite
  en memoria: la base de datos principal (db.sqlite3) no se toca.
- Se cuentan registros de la base principal antes y después para dejar
  evidencia de ese aislamiento en el laboratorio.
"""

from __future__ import annotations

import fcntl
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from .casos import CASOS

ARCHIVO_REPORTE = "reporte_verificacion.json"
TIEMPO_MAXIMO_S = 300


class EjecucionEnCurso(Exception):
    pass


def _dir_reportes() -> Path:
    ruta = Path(settings.CAMPUSFLOW_REPORTES_DIR)
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def ruta_reporte() -> Path:
    return _dir_reportes() / ARCHIVO_REPORTE


def conteo_bd_principal() -> dict[str, int]:
    from accounts.models import Usuario
    from enrollments.models import DetalleMatricula, Matricula

    return {
        "usuarios": Usuario.objects.count(),
        "matriculas": Matricula.objects.count(),
        "detalles_matricula": DetalleMatricula.objects.count(),
    }


def ejecutar_pruebas(etiquetas: list[str] | None = None) -> dict:
    """Corre `manage.py test` con el runner del laboratorio y devuelve el reporte."""
    directorio = _dir_reportes()
    candado = open(directorio / ".ejecucion.lock", "w")
    try:
        try:
            fcntl.flock(candado, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise EjecucionEnCurso("Ya hay una ejecución de pruebas en curso.") from exc

        antes = conteo_bd_principal()
        with tempfile.NamedTemporaryFile(dir=directorio, suffix=".json", delete=False) as tmp:
            ruta_tmp = Path(tmp.name)
        comando = [
            sys.executable, "manage.py", "test", *(etiquetas or []),
            "--testrunner=quality_lab.runner.VyVRunner", "--noinput", "-v", "2",
        ]
        entorno = {**os.environ, "CAMPUSFLOW_REPORTE_VYV": str(ruta_tmp), "PYTHONUNBUFFERED": "1"}
        inicio = time.perf_counter()
        try:
            proceso = subprocess.run(
                comando, cwd=settings.BASE_DIR, env=entorno, capture_output=True, text=True,
                timeout=TIEMPO_MAXIMO_S,
            )
            codigo, salida = proceso.returncode, (proceso.stdout + proceso.stderr)
        except subprocess.TimeoutExpired as exc:
            codigo, salida = -1, f"Tiempo máximo superado ({TIEMPO_MAXIMO_S} s).\n{exc.stdout or ''}"
        duracion = round(time.perf_counter() - inicio, 2)

        try:
            datos = json.loads(ruta_tmp.read_text(encoding="utf-8")) if ruta_tmp.stat().st_size else {}
        except (OSError, json.JSONDecodeError):
            datos = {}
        finally:
            ruta_tmp.unlink(missing_ok=True)

        registros = datos.get("registros", [])
        reporte = {
            "ejecutado_en": timezone.now().isoformat(),
            "comando": "python manage.py test " + " ".join(etiquetas or []) + " --testrunner=quality_lab.runner.VyVRunner",
            "codigo_salida": codigo,
            "duracion_s": duracion,
            "total": len(registros),
            "aprobadas": sum(1 for r in registros if r["estado"] == "aprobado"),
            "fallidas": sum(1 for r in registros if r["estado"] in ("fallido", "error")),
            "base_datos_pruebas": datos.get("base_datos_pruebas", "desconocida"),
            "bd_principal_antes": antes,
            "bd_principal_despues": conteo_bd_principal(),
            "registros": registros,
            "salida": salida[-6000:],
        }
        ruta_reporte().write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")
        return reporte
    finally:
        candado.close()


def leer_reporte() -> dict | None:
    ruta = ruta_reporte()
    if not ruta.exists():
        return None
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def casos_con_resultado(reporte: dict | None) -> list[dict]:
    """Une el catálogo V01–V09 con lo que realmente devolvió la ejecución."""
    por_caso = {}
    for registro in (reporte or {}).get("registros", []):
        if registro.get("caso"):
            por_caso[registro["caso"]] = registro
    filas = []
    for identificador, info in CASOS.items():
        registro = por_caso.get(identificador)
        filas.append({
            "id": identificador,
            **info,
            "datos_reales": (registro or {}).get("datos_utilizados"),
            "obtenido": (registro or {}).get("obtenido"),
            "estado": (registro or {}).get("estado", "sin_ejecutar"),
            "detalle": (registro or {}).get("detalle", ""),
            "prueba": (registro or {}).get("id", ""),
            "duracion_ms": (registro or {}).get("duracion_ms"),
        })
    return filas
