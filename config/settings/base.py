from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent


environ.Env.read_env(BASE_DIR / ".env.local")

env = environ.Env()

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    # apps
    "apps.accounts",
    "apps.api",
    "apps.catalog",
    "apps.core",
    "apps.delivery",
    "apps.orders",
    "apps.payments",
    "apps.staff",
    "apps.reviews",
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

ROOT_URLCONF = "config.urls"

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
                "apps.core.context_processors.shop",
                "apps.orders.context_processors.cart",
            ],
        },
    },
]

DATABASES = {"default": env.db("DATABASE_URL")}

WSGI_APPLICATION = "config.wsgi.application"

AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "catalog:home"
LOGOUT_REDIRECT_URL = "catalog:home"
AUTHENTICATION_BACKENDS = [
    "apps.accounts.backends.EmailBackend",  # shop login by email
    "django.contrib.auth.backends.ModelBackend",  # admin login by username
]
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "uk"
TIME_ZONE = "Europe/Kyiv"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Django 6.1+: MAILERS replaces the deprecated EMAIL_BACKEND setting.
MAILERS = {
    "default": {
        "BACKEND": env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"),
    },
}
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="shop@example.com")
SHOP_ADMIN_EMAIL = env("SHOP_ADMIN_EMAIL", default="")

SHOP_NAME = env("SHOP_NAME", default="Hop & Barley")
SHOP_CURRENCY = "$"

NOVA_POSHTA_API_URL = "https://api.novaposhta.ua/v2.0/json/"
NOVA_POSHTA_API_KEY = env("NOVA_POSHTA_API_KEY", default="")


REST_FRAMEWORK: dict = {}
