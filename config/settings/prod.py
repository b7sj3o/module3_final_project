from .base import *

DEBUG = False

# віддає статику (адмінка, restframework, swagger ui, ...) на проді, альтернатива nginx
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}


# --- HTTPS behind Caddy (manage.py check --deploy) ----------------------------------
# Caddy terminates TLS and passes the original scheme in X-Forwarded-Proto.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SECURE_REDIRECT_EXEMPT = [r"^health/$"]  # the Docker healthcheck calls plain http inside
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True


# HSTS: the browser goes straight to https next time. Start small, raise to a year
# (31536000) when you are sure HTTPS works.
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=3600)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True


# --- Logs ---------------------------------------------------------------------------
# With DEBUG=False Django prints errors nowhere by default. Send everything to stdout:
# `docker compose logs web` shows tracebacks and our logger.exception() calls.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {"format": "{asctime} {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {"django": {"handlers": ["console"], "level": "INFO", "propagate": False}},
}