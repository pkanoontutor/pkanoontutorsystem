"""
Django settings for config project.
"""

import os
from pathlib import Path

import dj_database_url

# -------------------------------------------------------------------
# BASE
# -------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent


# -------------------------------------------------------------------
# SECURITY
# -------------------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-dev-only-change-this-in-production")

# ✅ DEBUG อ่านจาก env (prod แนะนำ DEBUG=0)
DEBUG = os.getenv("DEBUG", "0").lower() in ("1", "true", "yes", "y")

# ✅ Render hostname (ถ้ามี)
RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")

_allowed_hosts_env = os.getenv("ALLOWED_HOSTS", "")
if _allowed_hosts_env:
    ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts_env.split(",") if h.strip()]
else:
    ALLOWED_HOSTS = ["127.0.0.1", "localhost", "pkanoontutor.com", "www.pkanoontutor.com"]
    if RENDER_EXTERNAL_HOSTNAME:
        ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# CSRF trusted origins (แนะนำใส่ https://www.pkanoontutor.com)
_csrf_env = os.getenv("CSRF_TRUSTED_ORIGINS", "")
if _csrf_env:
    CSRF_TRUSTED_ORIGINS = [x.strip() for x in _csrf_env.split(",") if x.strip()]
else:
    CSRF_TRUSTED_ORIGINS = [
        "https://pkanoontutor.com",
        "https://www.pkanoontutor.com",
    ]
    if RENDER_EXTERNAL_HOSTNAME:
        CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")

# ✅ ให้ config/urls.py ตัดสินใจเสิร์ฟ media ใน prod ได้
SERVE_MEDIA = os.getenv("SERVE_MEDIA", "0").lower() in ("1", "true", "yes", "y")

# -------------------------------------------------------------------
# APPLICATIONS
# -------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "core",
]


# -------------------------------------------------------------------
# MIDDLEWARE
# -------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    # ✅ สำหรับ production static files
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ✅ Security headers (ปลอดภัยขึ้นสำหรับ prod)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG


# -------------------------------------------------------------------
# URL / TEMPLATE
# -------------------------------------------------------------------
ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
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

WSGI_APPLICATION = "config.wsgi.application"


# -------------------------------------------------------------------
# DATABASE
# -------------------------------------------------------------------
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        ssl_require=True,
    )
}


# -------------------------------------------------------------------
# PASSWORD VALIDATION
# -------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# -------------------------------------------------------------------
# INTERNATIONALIZATION
# -------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("TIME_ZONE", "Asia/Bangkok")
USE_I18N = True
USE_TZ = True


# -------------------------------------------------------------------
# STATIC FILES
# -------------------------------------------------------------------
STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "core" / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


# -------------------------------------------------------------------
# MEDIA FILES
# -------------------------------------------------------------------
MEDIA_URL = os.getenv("MEDIA_URL", "/media/")

# ✅ สำคัญสุด: ชี้ไป persistent disk ที่คุณ mount ไว้ (/var/data)
# ให้ตั้ง Render env: MEDIA_ROOT=/var/data/media
MEDIA_ROOT = os.getenv("MEDIA_ROOT", str(BASE_DIR / "media"))


# -------------------------------------------------------------------
# DEFAULT PRIMARY KEY
# -------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/adminlublub/login/"
LOGIN_REDIRECT_URL = "/dashboard/"


# -------------------------------------------------------------------
# EMAIL — Gmail SMTP
# อย่าใส่ password ตรงนี้ ให้ตั้ง env variable บน Render แทน
# Key: EMAIL_HOST_PASSWORD  Value: <Gmail App Password>
# -------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "pkanoontutor@gmail.com"
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = "pkanoontutor@gmail.com"
