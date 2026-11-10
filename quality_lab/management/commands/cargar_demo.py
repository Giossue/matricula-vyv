from django.core.management.base import BaseCommand

from quality_lab import demo


class Command(BaseCommand):
    help = "Carga los datos de demostración de CampusFlow (solo si la base está vacía)."

    def handle(self, *args, **options):
        if demo.hay_datos_demo():
            self.stdout.write(self.style.WARNING(
                "Ya existen datos académicos o cuentas de demostración. No se cargó nada.\n"
                "Para volver al estado inicial usa: python manage.py reset_demo"
            ))
            return
        resumen = demo.cargar_datos_demo()
        self._informar(self, resumen)

    @staticmethod
    def _informar(cmd, resumen):
        cmd.stdout.write(cmd.style.SUCCESS("Datos de demostración cargados."))
        for clave in ("carreras", "docentes", "asignaturas", "periodos", "secciones", "estudiantes", "matriculas", "detalles"):
            cmd.stdout.write(f"  {clave:<12} {resumen[clave]}")
        cmd.stdout.write(f"  Período activo: {resumen['periodo_activo']} (matrícula hasta {resumen['limite']})")
        cmd.stdout.write("  Cuentas (solo desarrollo local):")
        cmd.stdout.write(f"    admin       / {demo.CLAVE_ADMIN}")
        for usuario in demo.USUARIOS_DEMO[1:]:
            cmd.stdout.write(f"    {usuario:<11} / {demo.CLAVE_ESTUDIANTE}")
