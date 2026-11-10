from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Count, Q
from django.utils import timezone


class Carrera(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    codigo = models.CharField("código", max_length=10, unique=True)

    class Meta:
        db_table = "carreras"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Docente(models.Model):
    nombre = models.CharField(max_length=80)
    apellido = models.CharField(max_length=80)
    correo = models.EmailField("correo electrónico", unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "docentes"
        ordering = ["apellido", "nombre"]

    def __str__(self):
        return f"{self.nombre} {self.apellido}"


class Asignatura(models.Model):
    class Estado(models.TextChoices):
        ACTIVA = "activa", "Activa"
        INACTIVA = "inactiva", "Inactiva"

    codigo = models.CharField("código", max_length=12, unique=True)
    nombre = models.CharField(max_length=120)
    creditos = models.PositiveSmallIntegerField(
        "créditos", validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    carrera = models.ForeignKey(
        Carrera, on_delete=models.PROTECT, related_name="asignaturas", db_column="carrera_id"
    )
    semestre_recomendado = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ACTIVA)

    class Meta:
        db_table = "asignaturas"
        ordering = ["carrera__nombre", "semestre_recomendado", "nombre"]
        constraints = [
            models.CheckConstraint(
                condition=Q(creditos__gte=1, creditos__lte=10), name="asignatura_creditos_validos"
            ),
            models.CheckConstraint(
                condition=Q(semestre_recomendado__gte=1, semestre_recomendado__lte=12),
                name="asignatura_semestre_valido",
            ),
        ]

    def __str__(self):
        return f"{self.codigo} · {self.nombre}"

    @property
    def activa(self) -> bool:
        return self.estado == self.Estado.ACTIVA


class PeriodoAcademico(models.Model):
    class Estado(models.TextChoices):
        PLANIFICADO = "planificado", "Planificado"
        ACTIVO = "activo", "Activo"
        CERRADO = "cerrado", "Cerrado"

    nombre = models.CharField(max_length=60, unique=True)
    fecha_inicio = models.DateField("fecha de inicio")
    fecha_fin = models.DateField("fecha de finalización")
    fecha_limite_matricula = models.DateField("fecha límite de matrícula")
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PLANIFICADO)

    class Meta:
        db_table = "periodos_academicos"
        ordering = ["-fecha_inicio"]
        verbose_name = "período académico"
        verbose_name_plural = "períodos académicos"
        constraints = [
            models.UniqueConstraint(
                fields=["estado"], condition=Q(estado="activo"), name="un_solo_periodo_activo"
            ),
            models.CheckConstraint(
                condition=Q(fecha_fin__gt=models.F("fecha_inicio")), name="periodo_fechas_ordenadas"
            ),
            models.CheckConstraint(
                condition=Q(fecha_limite_matricula__lte=models.F("fecha_fin")),
                name="periodo_limite_dentro_del_periodo",
            ),
        ]

    def __str__(self):
        return self.nombre

    def clean(self):
        errores = {}
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin <= self.fecha_inicio:
            errores["fecha_fin"] = "La fecha de finalización debe ser posterior a la de inicio."
        if self.fecha_limite_matricula and self.fecha_fin and self.fecha_limite_matricula > self.fecha_fin:
            errores["fecha_limite_matricula"] = "La fecha límite de matrícula no puede superar el fin del período."
        if self.estado == self.Estado.ACTIVO:
            otro = PeriodoAcademico.objects.filter(estado=self.Estado.ACTIVO).exclude(pk=self.pk).first()
            if otro:
                errores["estado"] = f"Ya existe un período activo ({otro.nombre}). Ciérralo o planifícalo antes."
        if errores:
            raise ValidationError(errores)

    def matricula_abierta(self, hoy=None) -> bool:
        """La matrícula está habilitada si el período está activo y no venció la fecha límite."""
        hoy = hoy or timezone.localdate()
        return self.estado == self.Estado.ACTIVO and hoy <= self.fecha_limite_matricula

    @classmethod
    def actual(cls):
        return cls.objects.filter(estado=cls.Estado.ACTIVO).first()


class SeccionQuerySet(models.QuerySet):
    def con_cupos(self):
        """Anota inscritos y cupos disponibles calculados desde los registros reales."""
        return self.annotate(
            inscritos=Count("detalles", filter=Q(detalles__estado="inscrita"), distinct=True)
        )


class Seccion(models.Model):
    asignatura = models.ForeignKey(
        Asignatura, on_delete=models.PROTECT, related_name="secciones", db_column="asignatura_id"
    )
    docente = models.ForeignKey(
        Docente, on_delete=models.PROTECT, related_name="secciones", db_column="docente_id"
    )
    periodo = models.ForeignKey(
        PeriodoAcademico, on_delete=models.PROTECT, related_name="secciones", db_column="periodo_id",
        verbose_name="período",
    )
    paralelo = models.CharField(max_length=5)
    capacidad_maxima = models.PositiveSmallIntegerField(
        "capacidad máxima", validators=[MinValueValidator(1), MaxValueValidator(200)]
    )

    objects = SeccionQuerySet.as_manager()

    class Meta:
        db_table = "secciones"
        ordering = ["asignatura__nombre", "paralelo"]
        verbose_name = "sección"
        verbose_name_plural = "secciones"
        constraints = [
            models.UniqueConstraint(
                fields=["asignatura", "periodo", "paralelo"], name="seccion_paralelo_unico"
            ),
            models.CheckConstraint(condition=Q(capacidad_maxima__gte=1), name="seccion_capacidad_positiva"),
        ]

    def __str__(self):
        return f"{self.asignatura.nombre} · Paralelo {self.paralelo}"

    @property
    def cupos_ocupados(self) -> int:
        valor = getattr(self, "inscritos", None)
        if valor is None:
            valor = self.detalles.filter(estado="inscrita").count()
        return valor

    @property
    def cupos_disponibles(self) -> int:
        return max(self.capacidad_maxima - self.cupos_ocupados, 0)

    @property
    def porcentaje_ocupacion(self) -> int:
        if not self.capacidad_maxima:
            return 0
        return min(round(self.cupos_ocupados * 100 / self.capacidad_maxima), 100)

    @property
    def horario_texto(self) -> str:
        return "; ".join(str(h) for h in self.horarios.all()) or "Sin horario"

    def clean(self):
        if self.pk and self.capacidad_maxima is not None:
            ocupados = self.detalles.filter(estado="inscrita").count()
            if self.capacidad_maxima < ocupados:
                raise ValidationError({
                    "capacidad_maxima": f"Hay {ocupados} estudiantes inscritos; la capacidad no puede ser menor."
                })


class Horario(models.Model):
    class Dia(models.IntegerChoices):
        LUNES = 1, "Lunes"
        MARTES = 2, "Martes"
        MIERCOLES = 3, "Miércoles"
        JUEVES = 4, "Jueves"
        VIERNES = 5, "Viernes"
        SABADO = 6, "Sábado"

    seccion = models.ForeignKey(
        Seccion, on_delete=models.CASCADE, related_name="horarios", db_column="seccion_id"
    )
    dia_semana = models.PositiveSmallIntegerField("día de la semana", choices=Dia.choices)
    hora_inicio = models.TimeField("hora de inicio")
    hora_fin = models.TimeField("hora de finalización")

    class Meta:
        db_table = "horarios"
        ordering = ["dia_semana", "hora_inicio"]
        constraints = [
            models.CheckConstraint(
                condition=Q(hora_fin__gt=models.F("hora_inicio")), name="horario_fin_posterior_inicio"
            ),
            models.CheckConstraint(
                condition=Q(dia_semana__gte=1, dia_semana__lte=6), name="horario_dia_valido"
            ),
        ]

    def __str__(self):
        return f"{self.get_dia_semana_display()} {self.hora_inicio:%H:%M}–{self.hora_fin:%H:%M}"

    def clean(self):
        if self.hora_inicio and self.hora_fin and self.hora_fin <= self.hora_inicio:
            raise ValidationError({"hora_fin": "La hora de finalización debe ser posterior a la de inicio."})

    def se_cruza_con(self, otro: "Horario") -> bool:
        return (
            self.dia_semana == otro.dia_semana
            and self.hora_inicio < otro.hora_fin
            and otro.hora_inicio < self.hora_fin
        )
