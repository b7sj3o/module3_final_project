FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# 1. Dependencies first: this layer stays cached until pyproject.toml or uv.lock change.
#    --no-dev: pytest, ruff and mypy are not needed on the server.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# 2. The code.
COPY . .

# 3. Static files are collected once, while building the image, not on every start.
#    Real secrets are not needed for that, so dummy values are passed only to this command.
RUN SECRET_KEY=build-only DATABASE_URL=sqlite:///build.sqlite3 \
    DJANGO_SETTINGS_MODULE=config.settings.prod \
    python manage.py collectstatic --noinput && rm -f build.sqlite3

# 4. Not root: a hole in the app does not give root in the container.
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/media \
    && chown -R app:app /app/media
USER app

EXPOSE 8000

# Docker (and depends_on: service_healthy) knows when the app really answers.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/', timeout=3)"

CMD ["gunicorn", "config.wsgi:application", "-c", "gunicorn.conf.py"]
