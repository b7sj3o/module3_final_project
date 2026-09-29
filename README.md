# Hop & Barley

Інтернет-магазин товарів для домашнього пивоваріння: каталог з фільтрами, кошик у сесії,
оформлення замовлення з доставкою Новою Поштою, особистий кабінет, відгуки після покупки,
staff-панель і REST API з документацією.

**Стек:** Python 3.12, Django 6.1, DRF + SimpleJWT, drf-spectacular, PostgreSQL 17,
uv, gunicorn, whitenoise, Caddy, Docker Compose, GitHub Actions.

## Що всередині

| Розділ | Адреса |
|---|---|
| Каталог, фільтри, пошук, сортування | `/` |
| Товар і відгуки | `/product/<slug>/` |
| Кошик / оформлення | `/cart/`, `/checkout/` |
| Кабінет (історія замовлень, профіль, адреса НП) | `/accounts/` |
| Staff-панель (товари, аналітика) | `/staff/products/`, `/staff/dashboard/` |
| Django admin | `/admin/` |
| REST API | `/api/` |
| Swagger / ReDoc | `/api/docs/`, `/api/redoc/` |
| Healthcheck | `/health/` |

## Запуск локально (без Docker)

Потрібні [uv](https://docs.astral.sh/uv/) і PostgreSQL.

```bash
cp .env.example .env.local          # заповнити DATABASE_URL, SECRET_KEY, NOVA_POSHTA_API_KEY
uv sync
uv run manage.py migrate
uv run manage.py seed_shop          # демо-каталог, покупці, замовлення, відгуки
uv run manage.py createsuperuser
uv run manage.py runserver
```

Демо-покупці: `olena@example.com` / `demo-pass-123` (вхід за email або логіном).

## Docker локально

```bash
cp .env.example .env.dev            # DJANGO_SETTINGS_MODULE=config.settings.dev, DATABASE_URL=...@db:5432/...
docker compose up --build
```

## Перевірки

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy .
uv run pytest
```

Те саме запускає CI на кожен push і PR, плюс `manage.py check --deploy` для прод-налаштувань
і збірку Docker-образу.

## Продакшн

Схема: `браузер → Caddy (HTTPS, /media/) → gunicorn (Django + whitenoise) → PostgreSQL`.

1. VPS з Docker, DNS-запис `A` вашого домену → IP сервера, відкриті порти 80 і 443.
2. На сервері:

   ```bash
   git clone <repo> shop && cd shop
   cp .env.example .env.production
   ```

   У `.env.production` обов'язково:

   | Змінна | Значення |
   |---|---|
   | `DJANGO_SETTINGS_MODULE` | `config.settings.prod` |
   | `DEBUG` | `False` |
   | `SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
   | `SITE_DOMAIN` | `shop.example.com` |
   | `ALLOWED_HOSTS` | `shop.example.com,localhost` (`localhost` — для healthcheck) |
   | `DATABASE_URL` | `postgresql://USER:PASSWORD@db:5432/DB` (те саме, що `POSTGRES_*`) |
   | `EMAIL_HOST` / `EMAIL_HOST_PASSWORD` | `smtp.resend.com` / API-ключ Resend |
   | `DEFAULT_FROM_EMAIL` | адреса на підтвердженому в Resend домені |
   | `NOVA_POSHTA_API_KEY` | ключ з кабінету НП |

3. Запуск і перший адміністратор:

   ```bash
   docker compose -f docker-compose.prod.yml up -d --build
   docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
   docker compose -f docker-compose.prod.yml logs -f web
   ```

Caddy сам отримає й оновлюватиме сертифікат Let's Encrypt для `SITE_DOMAIN`.
Оновлення: `git pull && docker compose -f docker-compose.prod.yml up -d --build`
(міграції застосовуються при старті контейнера).

## REST API коротко

| Ресурс | Методи |
|---|---|
| `/api/products/`, `/api/products/<id>/` | GET — усі; POST/PUT/PATCH/DELETE — staff. Фільтри як у каталозі: `search`, `category`, `min_price`, `max_price`, `in_stock`, `ordering` |
| `/api/products/<id>/reviews/` | GET; POST — лише після покупки, один раз |
| `/api/categories/` | GET |
| `/api/cart/` | GET, POST (додати), PATCH (кількість), DELETE (`?product=<id>` або весь кошик) |
| `/api/orders/` | GET свої (`?status=`), POST — з кошика; `/api/orders/<id>/`: PATCH статусу — staff, DELETE — скасування |
| `/api/users/register/`, `/api/users/login/`, `/api/users/token/refresh/`, `/api/users/me/` | реєстрація, JWT, свій профіль |

Кошик в API — той самий сесійний кошик, що й на сайті: Swagger і Postman зберігають cookie.
