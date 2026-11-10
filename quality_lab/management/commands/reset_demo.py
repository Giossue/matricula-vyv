import sys
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from quality_lab import demo

from .cargar_demo import Command as CargarDemo


class Command(BaseCommand):
    help = (
        "Restaura los datos de demostración: borra datos académicos, matrículas y cuentas demo "
        "y los vuelve a cargar. Solo funciona en el entorno local."
    )

    def add_arguments(self, parser):
        parser.add_argument("--si", action="store_true", help="Confirma la restauración sin preguntar.")
        parser.add_argument(
            "--incluir-evaluaciones", action="store_true",
            help="También borra las evaluaciones de participantes (por defecto se conservan).",
        )

    def _comprobar_entorno(self):
        problemas = []
        if not settings.DEBUG:
            problemas.append("DEBUG está desactivado (posible entorno de producción).")
        if getattr(settings, "CAMPUSFLOW_ENTORNO", "") != "local":
            problemas.append(f"CAMPUSFLOW_ENTORNO es '{settings.CAMPUSFLOW_ENTORNO}', se requiere 'local'.")
        bd = connection.settings_dict
        if bd["ENGINE"] != "django.db.backends.sqlite3":
            problemas.append("La base de datos no es SQLite.")
        elif not self._es_memoria(str(bd["NAME"])):
            ruta = Path(str(bd["NAME"])).resolve()
            if Path(settings.BASE_DIR).resolve() not in ruta.parents:
                problemas.append(f"La base de datos ({ruta}) no está dentro de la carpeta del proyecto.")
        if problemas:
            raise CommandError("reset_demo se canceló por seguridad:\n  - " + "\n  - ".join(problemas))

    @staticmethod
    def _es_memoria(nombre: str) -> bool:
        # Base temporal en memoria que usan las pruebas automatizadas.
        return nombre == ":memory:" or "mode=memory" in nombre

    def handle(self, *args, **options):
        self._comprobar_entorno()
        if not options["si"]:
            if not sys.stdin.isatty():
                raise CommandError("Sin terminal interactiva: usa --si para confirmar explícitamente.")
            self.stdout.write(self.style.WARNING(
                "Se borrarán asignaturas, períodos, secciones, docentes, matrículas y las cuentas de "
                "demostración, y se volverán a crear."
            ))
            if input("Escribe RESTAURAR para continuar: ").strip() != "RESTAURAR":
                raise CommandError("Restauración cancelada.")
        borrado = demo.borrar_datos_demo(incluir_evaluaciones=options["incluir_evaluaciones"])
        self.stdout.write("Registros eliminados: " + ", ".join(f"{k}={v}" for k, v in borrado.items()))
        resumen = demo.cargar_datos_demo()
        CargarDemo._informar(self, resumen)
        if not options["incluir_evaluaciones"]:
            self.stdout.write("Las evaluaciones de participantes se conservaron.")
