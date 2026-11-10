from django.core.management.base import BaseCommand, CommandError

from quality_lab import verificacion


class Command(BaseCommand):
    help = "Ejecuta las pruebas y guarda el reporte que muestra el Laboratorio de Verificación."

    def add_arguments(self, parser):
        parser.add_argument("--solo-casos", action="store_true", help="Ejecuta solo los casos V01–V09.")

    def handle(self, *args, **options):
        etiquetas = ["quality_lab.tests.test_verificacion"] if options["solo_casos"] else []
        reporte = verificacion.ejecutar_pruebas(etiquetas)
        for caso in verificacion.casos_con_resultado(reporte):
            marca = "OK " if caso["estado"] == "aprobado" else "ERR"
            self.stdout.write(f"  [{marca}] {caso['id']} {caso['titulo']}: {caso['obtenido'] or caso['estado']}")
        self.stdout.write(
            f"Total {reporte['total']} · aprobadas {reporte['aprobadas']} · fallidas {reporte['fallidas']} "
            f"· {reporte['duracion_s']} s · reporte en {verificacion.ruta_reporte()}"
        )
        if reporte["fallidas"] or reporte["total"] == 0:
            raise CommandError("Hay pruebas fallidas o no se ejecutó ninguna.")
