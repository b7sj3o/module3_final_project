"""Gunicorn settings for production: `gunicorn config.wsgi:application -c gunicorn.conf.py`."""

import multiprocessing
import os

bind = "0.0.0.0:8000"

# 2 x CPU + 1 is the usual start; WEB_CONCURRENCY overrides it on a small server.
workers = int(os.environ.get("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))

# A stuck request is killed after 30 s instead of blocking a worker forever.
timeout = 30
graceful_timeout = 30

# Restart each worker after ~1000 requests: a slow memory leak never grows big.
max_requests = 1000
max_requests_jitter = 100

# Logs to stdout/stderr -> `docker compose logs web`.
accesslog = "-"
errorlog = "-"

# Only Caddy can reach this container, so its X-Forwarded-* headers are trusted.
forwarded_allow_ips = "*"