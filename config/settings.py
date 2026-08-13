"""Configuración de Django para TheBrotherhood.

Migrado desde FastAPI conservando el esquema `daw` de la base existente y las
reglas de negocio RN-01..RN-23 documentadas en `docs/01_analisis.md`.
"""

import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "Falta la variable de entorno DJANGO_SECRET_KEY. "
        "Copie .env.example a .env y defina una clave."
    )

DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_HOSTS_PERMITIDOS", "127.0.0.1,localhost").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "apps.usuarios",
    "apps.catalogo",
    "apps.citas",
]

# `django.contrib.auth` y `django.contrib.sessions` quedan deliberadamente
# fuera: la autenticación es propia (JWT sobre la tabla `daw.usuario`), no
# usa la tabla `auth_user` ni las sesiones de servidor de Django.

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # Sirve los archivos estáticos sin depender de un servidor aparte. Va
    # justo después del middleware de seguridad, como pide su documentación.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# --- Base de datos ---------------------------------------------------------
# Se reutiliza el DATABASE_URL del proyecto FastAPI. Viene en formato
# SQLAlchemy (`postgresql+psycopg://...`), así que se traduce a los campos
# que espera Django.

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "Falta la variable de entorno DATABASE_URL. "
        "Copie .env.example a .env y defina la cadena de conexión."
    )

_dsn = urlparse(DATABASE_URL.replace("postgresql+psycopg://", "postgresql://"))

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": (_dsn.path or "/postgres").lstrip("/"),
        "USER": _dsn.username or "",
        "PASSWORD": _dsn.password or "",
        "HOST": _dsn.hostname or "",
        "PORT": str(_dsn.port or 5432),
        "OPTIONS": {
            # Fija el esquema `daw` en cada conexión, igual que hacía
            # `app/database.py`. El rol `daw_api` no tiene privilegios sobre
            # `public`, donde vive la base real del cliente.
            "options": "-c search_path=daw",
        },
        "CONN_MAX_AGE": 60,
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --- Django REST Framework -------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.usuarios.autenticacion.AutenticacionCookieOBearer",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        # Cerrado por defecto: cada vista abre el acceso explícitamente con
        # AllowAny. Así un endpoint nuevo no queda público por descuido, que
        # es exactamente lo que pasó con `clientes` y `barberos` en FastAPI.
        "rest_framework.permissions.IsAuthenticated",
    ],
    "EXCEPTION_HANDLER": "config.excepciones.manejador_de_excepciones",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "UNAUTHENTICATED_USER": None,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "TheBrotherhood — API de gestión de citas",
    "DESCRIPTION": "Gestión de citas de barbería. Proyecto 04 de Desarrollo de Aplicaciones Web.",
    "VERSION": "3.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}


# --- Sesión: JWT en cookie httpOnly ---------------------------------------

JWT_SECRETO = os.getenv("JWT_SECRETO")
if not JWT_SECRETO:
    raise RuntimeError(
        "Falta la variable de entorno JWT_SECRETO. "
        "Copie .env.example a .env y defina un secreto de firma."
    )

JWT_ALGORITMO = "HS256"
JWT_MINUTOS_VIGENCIA = int(os.getenv("JWT_MINUTOS_VIGENCIA", "60"))

COOKIE_SESION = "brotherhood_sesion"
# Una cookie `Secure` no viaja sobre http://127.0.0.1: en desarrollo debe ser
# False o el login parecería funcionar y todo lo demás daría 401.
COOKIE_SEGURA = os.getenv("COOKIE_SEGURA", "false").lower() == "true"
# 'Lax' basta mientras el frontend se sirva desde el mismo origen. Con React en
# otro puerto hace falta 'None' (que exige Secure=True) y, con ello, CSRF.
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "Lax")


# --- CORS ------------------------------------------------------------------
# En desarrollo React corre en su propio puerto (Vite, 5173), así que las
# peticiones son cross-origin. En producción, si el build de React se sirve
# desde el mismo origen que la API, esta lista puede quedar vacía.

CORS_ALLOWED_ORIGINS = [
    origen.strip()
    for origen in os.getenv(
        "CORS_ORIGENES", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origen.strip()
]
# Imprescindible para que el navegador envíe la cookie de sesión.
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS


# --- Internacionalización --------------------------------------------------

LANGUAGE_CODE = "es"
# La API almacena y opera en UTC (RN-17). La conversión al huso de la
# barbería ocurre en `apps/citas/agenda.py` y en el frontend.
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# --- Seguridad del transporte ----------------------------------------------
# Sólo se aplica fuera de desarrollo: en local la aplicación se sirve por
# http://127.0.0.1, donde exigir HTTPS impediría entrar.

if not DEBUG:
    # La redirección puede desactivarse para comprobar en local una compilación
    # de producción, donde no hay certificado y el navegador no puede anunciar
    # el protocolo original. En el despliegue se deja activada.
    SECURE_SSL_REDIRECT = (
        os.getenv("DJANGO_REDIRIGIR_A_HTTPS", "true").lower() == "true"
    )
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # Un año, con los subdominios incluidos: el navegador recuerda que este
    # sitio sólo se visita por HTTPS y deja de intentar la primera petición en
    # claro. Conviene desplegar antes con un plazo corto y ampliarlo después,
    # porque hasta que expire no hay forma de volver atrás.
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # La plataforma termina el TLS y reenvía la petición por HTTP interno;
    # sin esta cabecera Django la vería insegura y entraría en un bucle de
    # redirecciones.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    X_FRAME_OPTIONS = "DENY"

STATIC_URL = "static/"

# Destino de `collectstatic`. La plataforma lo ejecuta al desplegar y
# WhiteNoise sirve el resultado.
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        # Comprime y añade un hash al nombre de cada archivo, de modo que
        # puedan cachearse indefinidamente sin servir una versión vieja.
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# --- Cliente web -----------------------------------------------------------
# Django sirve el build de React, de modo que la aplicación entera vive en un
# solo origen: la interfaz y la API comparten dominio y puerto. Eso es lo que
# permite mantener la cookie de sesión en SameSite=Lax, que ya bloquea su
# envío desde otros sitios, sin necesidad de un token CSRF aparte.
#
# En desarrollo puede usarse en su lugar el servidor de Vite (`npm run dev`),
# que recompila al guardar y reenvía las peticiones de la API aquí.

CLIENTE_BUILD = BASE_DIR / "static_build"

# Los archivos con hash en el nombre (JS y CSS que genera Vite) se sirven
# desde /assets/.
STATICFILES_DIRS = [CLIENTE_BUILD / "assets"] if CLIENTE_BUILD.is_dir() else []
