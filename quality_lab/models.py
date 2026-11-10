from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

ESCALA = [(1, "1 · Muy en desacuerdo"), (2, "2"), (3, "3 · Neutral"), (4, "4"), (5, "5 · Muy de acuerdo")]


class EvaluacionExperiencia(models.Model):
    """Respuesta de un participante en la validación con usuarios.

    Representa la opinión de una persona: el sistema la guarda y la resume,
    pero no saca conclusiones automáticas a partir de ella.
    """

    class Version(models.TextChoices):
        A = "A", "Versión A · sin vista semanal"
        B = "B", "Versión B · con vista semanal"

    version = models.CharField("versión evaluada", max_length=1, choices=Version.choices)
    participante = models.CharField(
        "participante (alias opcional)", max_length=80, blank=True,
        help_text="Puede quedar vacío para mantener el anonimato.",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="evaluaciones", db_column="usuario_id",
    )
    facilidad_seleccion = models.PositiveSmallIntegerField(
        "¿Fue fácil seleccionar las asignaturas?", choices=ESCALA,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comprension_horarios = models.PositiveSmallIntegerField(
        "¿Pudiste comprender los horarios disponibles?", choices=ESCALA,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    informacion_suficiente = models.PositiveSmallIntegerField(
        "¿La información fue suficiente para tomar una decisión?", choices=ESCALA,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    mejoras = models.TextField("¿Qué mejorarías del proceso?", blank=True, max_length=1500)
    fecha_registro = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "evaluaciones_experiencia"
        ordering = ["-fecha_registro"]
        constraints = [
            models.CheckConstraint(condition=models.Q(version__in=["A", "B"]), name="evaluacion_version_valida"),
        ]

    def __str__(self):
        return f"Evaluación {self.version} · {self.participante or 'anónimo'}"

    @property
    def promedio(self) -> float:
        return round((self.facilidad_seleccion + self.comprension_horarios + self.informacion_suficiente) / 3, 2)


class ConfiguracionDemo(models.Model):
    """Ajustes de la demostración de validación (una sola fila).

    Solo controla qué versión de la experiencia de matrícula se muestra.
    Ambas versiones usan las mismas reglas de negocio del backend.
    """

    class Version(models.TextChoices):
        A = "A", "Versión A"
        B = "B", "Versión B"

    version_experiencia = models.CharField(max_length=1, choices=Version.choices, default=Version.A)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "configuracion_demo"

    def __str__(self):
        return f"Experiencia activa: {self.get_version_experiencia_display()}"

    @classmethod
    def obtener(cls) -> "ConfiguracionDemo":
        objeto, _ = cls.objects.get_or_create(pk=1)
        return objeto
