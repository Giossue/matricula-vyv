from django.db import models
from django.db.models import Q
from django.utils import timezone


class Matricula(models.Model):
    """Matrícula de un estudiante en un período. Agrupa los detalles (asignaturas)."""

    class Estado(models.TextChoices):
        ACTIVA = "activa", "Activa"
        SIN_ASIGNATURAS = "sin_asignaturas", "Sin asignaturas vigentes"

    estudiante = models.ForeignKey(
        "accounts.Estudiante", on_delete=models.PROTECT, related_name="matriculas", db_column="estudiante_id"
    )
    periodo = models.ForeignKey(
        "academics.PeriodoAcademico", on_delete=models.PROTECT, related_name="matriculas",
        db_column="periodo_id", verbose_name="período",
    )
    fecha_registro = models.DateTimeField(default=timezone.now)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ACTIVA)

    class Meta:
        db_table = "matriculas"
        ordering = ["-fecha_registro"]
        verbose_name = "matrícula"
        verbose_name_plural = "matrículas"
        constraints = [
            models.UniqueConstraint(fields=["estudiante", "periodo"], name="una_matricula_por_periodo"),
        ]

    def __str__(self):
        return f"Matrícula {self.pk} · {self.estudiante} · {self.periodo}"

    @property
    def codigo(self) -> str:
        return f"MAT-{self.periodo_id:02d}-{self.pk:05d}"

    def detalles_vigentes(self):
        return self.detalles.filter(estado=DetalleMatricula.Estado.INSCRITA)


class DetalleMatricula(models.Model):
    """Una asignatura (sección) dentro de una matrícula."""

    class Estado(models.TextChoices):
        INSCRITA = "inscrita", "Inscrita"
        RETIRADA = "retirada", "Retirada"

    matricula = models.ForeignKey(
        Matricula, on_delete=models.CASCADE, related_name="detalles", db_column="matricula_id"
    )
    seccion = models.ForeignKey(
        "academics.Seccion", on_delete=models.PROTECT, related_name="detalles", db_column="seccion_id",
        verbose_name="sección",
    )
    # Copia de seccion.asignatura: permite que la base de datos impida duplicar
    # la misma asignatura (en cualquier paralelo) dentro de una matrícula.
    asignatura = models.ForeignKey(
        "academics.Asignatura", on_delete=models.PROTECT, related_name="+", db_column="asignatura_id"
    )
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.INSCRITA)
    fecha_registro = models.DateTimeField(default=timezone.now)
    fecha_retiro = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "detalles_matricula"
        ordering = ["seccion__asignatura__nombre"]
        verbose_name = "detalle de matrícula"
        verbose_name_plural = "detalles de matrícula"
        constraints = [
            models.UniqueConstraint(
                fields=["matricula", "asignatura"],
                condition=Q(estado="inscrita"),
                name="asignatura_no_duplicada_en_matricula",
            ),
        ]

    def __str__(self):
        return f"{self.seccion} ({self.get_estado_display()})"

    def save(self, *args, **kwargs):
        if self.seccion_id and not self.asignatura_id:
            self.asignatura_id = self.seccion.asignatura_id
        super().save(*args, **kwargs)
