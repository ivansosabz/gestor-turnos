"""Settings de Django para el proyecto no_me_olvido.

Lee configuración sensible/variable desde variables de entorno (ver
.env.example). Pensado para correr tanto en local (sqlite) como en
Railway u otro PaaS (PostgreSQL via DATABASE_URL).
"""
import os
from pathlib import Path

import dj_database_url

# BASE_DIR apunta a la raíz del repo (donde vive manage.py).
BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Seguridad / entorno
# ---------------------------------------------------------------------------

# Clave secreta de Django. En producción setear DJANGO_SECRET_KEY a un
# valor largo y aleatorio en las variables de entorno.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-key-change-me")

# DEBUG=True solo en desarrollo. Se controla con DJANGO_DEBUG.
DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() == "true"

# Hosts/dominios desde los que Django acepta requests.
# Lista separada por comas: "localhost,127.0.0.1,miapp.up.railway.app".
ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]

# Orígenes confiables para CSRF cuando el sitio se sirve por HTTPS detrás
# de un proxy (caso típico de Railway).
CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
    if o.strip()
]


# ---------------------------------------------------------------------------
# Apps
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    # whitenoise.runserver_nostatic desactiva el servidor de estáticos
    # built-in de Django para que en dev también se sirvan vía whitenoise
    # (mismo comportamiento que en prod).
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    # API
    "rest_framework",
    # App propia
    "turnos",
]


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise debe ir JUSTO después de SecurityMiddleware para servir
    # los estáticos eficientemente en producción sin Nginx.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "no_me_olvido.urls"


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # Templates compartidos viven en /templates/ en la raíz del repo.
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "no_me_olvido.wsgi.application"


# ---------------------------------------------------------------------------
# Base de datos
# ---------------------------------------------------------------------------

# Si DATABASE_URL está seteada se usa eso (PostgreSQL en Railway).
# Si no, fallback a sqlite local en BASE_DIR/db.sqlite3.
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,  # reusar conexiones por 10 minutos
    )
}


# ---------------------------------------------------------------------------
# Validadores de password (no se usan, pero los dejamos por compatibilidad
# con el admin y un eventual login futuro).
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ---------------------------------------------------------------------------
# i18n / Localización
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "es-ar"
TIME_ZONE = "America/Argentina/Buenos_Aires"
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Estáticos (servidos por WhiteNoise en prod)
# ---------------------------------------------------------------------------

STATIC_URL = "/static/"
# Carpeta donde tenemos manifest.json, sw.js, iconos, etc.
STATICFILES_DIRS = [BASE_DIR / "static"]
# `collectstatic` los junta acá (lo usa WhiteNoise en prod).
STATIC_ROOT = BASE_DIR / "staticfiles"

# En desarrollo usamos el storage sin manifest para que funcione sin
# ejecutar collectstatic primero. En prod usamos el manifest con hashes
# para cache busting (requiere `python manage.py collectstatic`).
if DEBUG:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"
else:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# DRF: solo respondemos JSON (no necesitamos la UI navegable de DRF).
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}
