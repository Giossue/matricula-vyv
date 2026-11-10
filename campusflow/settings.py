"""
Configuración de CampusFlow.

Proyecto pensado para ejecutarse en localhost con fines académicos.
Los valores sensibles se leen de variables de entorno (ver .env.example).
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _cargar_env(ruta: Path) -> None:
    """Carga un archivo .env sencillo (CLAVE=valor) sin dependencias externas."""
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


_cargar_env(BASE_DIR / ".env")


def _bool(nombre: str, por_defecto: bool) -> bool:
    valor = os.environ.get(nombre)
    if valor is None:
        return por_defecto
    return valor.strip().lower() in {"1", "true", "si", "sí", "yes", "on"}


SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "solo-desarrollo-local-campusflow-no-usar-en-produccion",
)
DEBUG = _bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]

# Entorno de ejecución. reset_demo solo funciona cuando vale "local".
CAMPUSFLOW_ENTORNO = os.environ.get("CAMPUSFLOW_ENTORNO", "local")
# Muestra la barra de demostración VyV (selector Versión A / Versión B).
CAMPUSFLOW_MODO_DEMO = _bool("CAMPUSFLOW_MODO_DEMO", True)
# Carpeta donde se guarda el último reporte del laboratorio de verificación.
CAMPUSFLOW_REPORTES_DIR = BASE_DIR / "var"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "academics",
    "enrollments",
    "quality_lab",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "campusflow.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "campusflow.context_processors.campusflow",
            ],
        },
    },
]

WSGI_APPLICATION = "campusflow.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / os.environ.get("CAMPUSFLOW_DB", "db.sqlite3"),
        # Las pruebas usan una base de datos SQLite en memoria, aislada de la principal.
        "TEST": {"NAME": None},
    }
}

AUTH_USER_MODEL = "accounts.Usuario"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "inicio"
LOGOUT_REDIRECT_URL = "accounts:login"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es"
TIME_ZONE = "America/Guayaquil"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MESSAGE_TAGS = {40: "error", 25: "success", 30: "warning", 20: "info"}
