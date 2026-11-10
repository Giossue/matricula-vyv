from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def _crear(self, nombre_usuario, correo, password, **campos):
        if not nombre_usuario:
            raise ValueError("El nombre de usuario es obligatorio.")
        if not correo:
            raise ValueError("El correo electrónico es obligatorio.")
        usuario = self.model(
            nombre_usuario=nombre_usuario,
            correo=self.normalize_email(correo),
            **campos,
        )
        # set_password guarda un hash (PBKDF2 por defecto), nunca el texto plano.
        usuario.set_password(password)
        usuario.full_clean(exclude=["password"])
        usuario.save(using=self._db)
        return usuario

    def create_user(self, nombre_usuario, correo, password=None, **campos):
        campos.setdefault("rol", Usuario.Rol.ESTUDIANTE)
        return self._crear(nombre_usuario, correo, password, **campos)

    def create_superuser(self, nombre_usuario, correo, password=None, **campos):
        campos["rol"] = Usuario.Rol.ADMINISTRADOR
        return self._crear(nombre_usuario, correo, password, **campos)


class Usuario(AbstractBaseUser):
    """Usuario del sistema. El rol determina qué módulos puede usar."""

    class Rol(models.TextChoices):
        ADMINISTRADOR = "administrador", "Administrador"
        ESTUDIANTE = "estudiante", "Estudiante"

    # Campos heredados de Django redefinidos para que sus columnas queden en español.
    password = models.CharField("contraseña (hash)", max_length=128, db_column="contrasena_hash")
    last_login = models.DateTimeField("último acceso", blank=True, null=True, db_column="ultimo_acceso")
    is_active = models.BooleanField("activo", default=True, db_column="activo")

    nombre_usuario = models.CharField("nombre de usuario", max_length=50, unique=True)
    nombre = models.CharField(max_length=80)
    apellido = models.CharField(max_length=80)
    correo = models.EmailField("correo electrónico", unique=True)
    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.ESTUDIANTE)
    fecha_registro = models.DateTimeField(default=timezone.now)

    objects = UsuarioManager()

    USERNAME_FIELD = "nombre_usuario"
    EMAIL_FIELD = "correo"
    REQUIRED_FIELDS = ["correo", "nombre", "apellido"]

    class Meta:
        db_table = "usuarios"
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["apellido", "nombre"]

    def __str__(self):
        return f"{self.nombre_completo} ({self.nombre_usuario})"

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellido}".strip()

    @property
    def es_administrador(self) -> bool:
        return self.rol == self.Rol.ADMINISTRADOR

    @property
    def es_estudiante(self) -> bool:
        return self.rol == self.Rol.ESTUDIANTE

    @property
    def iniciales(self) -> str:
        return (self.nombre[:1] + self.apellido[:1]).upper()

    # Compatibilidad mínima con utilidades de Django que consultan permisos.
    @property
    def is_staff(self) -> bool:
        return self.es_administrador

    def has_perm(self, perm, obj=None) -> bool:
        return self.is_active and self.es_administrador

    def has_module_perms(self, app_label) -> bool:
        return self.is_active and self.es_administrador


class Estudiante(models.Model):
    """Perfil académico asociado a un usuario con rol estudiante."""

    usuario = models.OneToOneField(
        Usuario, on_delete=models.CASCADE, related_name="estudiante", db_column="usuario_id"
    )
    codigo_estudiantil = models.CharField("código estudiantil", max_length=20, unique=True)
    carrera = models.ForeignKey(
        "academics.Carrera", on_delete=models.PROTECT, related_name="estudiantes", db_column="carrera_id"
    )
    semestre_actual = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )

    class Meta:
        db_table = "estudiantes"
        ordering = ["usuario__apellido", "usuario__nombre"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(semestre_actual__gte=1, semestre_actual__lte=12),
                name="estudiante_semestre_valido",
            )
        ]

    def __str__(self):
        return f"{self.codigo_estudiantil} · {self.usuario.nombre_completo}"
