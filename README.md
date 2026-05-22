# YouGotaGift Payroll App

Django payroll service for payee onboarding, bank-detail acknowledgement, pay runs, Form 16 distribution, Zoho People integration, Google login, GraphQL/REST APIs, and background processing through Celery.

The backend lives in clear Django app boundaries:

- `payees`: payee profile, bank details, acknowledgements, storage helpers, and payee-facing APIs.
- `payroll`: pay runs, payments, Form 16 workflows, and payroll maintenance commands.
- `zohopeople`: Zoho People token storage, token refresh, and integration utilities.
- `configs`: configuration models.
- `core`: auth/profile APIs and shared helpers.
- `youpayroll`: Django project settings, URLs, Celery, ASGI, and WSGI entry points.
- `deployment`: app/nginx images and Helm values for `youpayroll` and `youpayroll-aps`.

## Local Quick Start

Use Python 3.11+ if possible. The compose setup starts PostgreSQL, Redis, the Django web container, and Celery.

```bash
cp .env.example .env  # if present; otherwise create .env from the contract below
docker compose up --build
```

The web service is exposed on `http://localhost:8002` by default. Override it with `WEB_HOST_PORT`.

For local commands inside the container:

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py shell
```

For a host-only run:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Host-only PostgreSQL defaults to `localhost`; compose defaults to service host `db`.

## Environment Contract

All values are read with `python-decouple`. Keep real values in local `.env`, Vault, or the runtime environment. Do not commit secrets.

Required for all non-test settings:

```dotenv
FIELD_ENCRYPTION_KEY=...
```

Generate a development key with:

```bash
python manage.py generate_encryption_key
```

Required for `production`, `qa`, and `sandbox` settings:

```dotenv
SECRET_KEY=...
GOOGLE_CLIENT_ID=...
FIELD_ENCRYPTION_KEY=...
```

Database:

```dotenv
DATABASE_ENGINE=django.db.backends.postgresql
DATABASES_NAME=youpayroll
DATABASES_USER=postgres
DATABASES_PASSWORD=postgres
DATABASES_HOST=localhost
DATABASES_PORT=5432
```

Local compose uses `DATABASES_HOST=db` and exposes PostgreSQL on host port `5433` unless `DB_HOST_PORT` is overridden.

Celery and Redis:

```dotenv
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

AWS/S3 storage, used when `DEBUG=False`:

```dotenv
AWS_S3_HOST=s3.amazonaws.com
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_STORAGE_BUCKET_NAME=...
AWS_CLOUDFRONT_DOMAIN=...
AWS_S3_REGION_NAME=...
AWS_DEFAULT_ACL=private
AWS_QUERYSTRING_AUTH=False
AWS_S3_FILE_OVERWRITE=False
AWS_LOCATION=staticfiles
AWS_S3_SIGNATURE_VERSION=s3v4
```

Auth, CORS, and security:

```dotenv
ALLOWED_HOSTS=localhost,127.0.0.1
GOOGLE_CLIENT_ID=...
CORS_ALLOW_ALL_ORIGINS=False
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
SECURE_HSTS_SECONDS=0
ENABLE_GRAPHIQL=False
LOG_BASE_DIR=logs
```

Zoho People:

```dotenv
ZOHOPEOPLE_CLIENT_ID=...
ZOHOPEOPLE_CLIENT_SECRET=...
ZOHOPEOPLE_REDIRECT_URI=...
```

Nginx deployment allowlist for the Vinton Gray Cerf path:

```dotenv
VINTON_GRAY_CERF_IP_ALLOWLIST=203.0.113.10,198.51.100.0/24
```

This is consumed by the nginx entrypoint and rendered as nginx `geo` rules.

## Zoho Token Bootstrap

Zoho People form tokens are stored in `ZohoPeopleFormToken`; token fields are encrypted at rest with `FIELD_ENCRYPTION_KEY`. The singleton row is created or updated by the management command.

Prerequisites:

- `FIELD_ENCRYPTION_KEY` is set and stable for the environment.
- Database migrations have run.
- `ZOHOPEOPLE_CLIENT_ID`, `ZOHOPEOPLE_CLIENT_SECRET`, and optional `ZOHOPEOPLE_REDIRECT_URI` are set.
- A fresh Zoho OAuth grant token has been issued for the configured client and redirect URI.

Run:

```bash
python manage.py zoho_forms_token_generation --grant-token "<zoho-grant-token>"
```

In compose:

```bash
docker compose exec web python manage.py zoho_forms_token_generation --grant-token "<zoho-grant-token>"
```

The command redacts sensitive response fields in error output and updates row `id=1` with the latest access and refresh tokens.

## Tests

Use the dedicated test settings for isolated in-memory SQLite and eager Celery tasks:

```bash
DJANGO_SETTINGS_MODULE=youpayroll.settings.testing python manage.py test
```

Run a focused test module or class:

```bash
DJANGO_SETTINGS_MODULE=youpayroll.settings.testing python manage.py test payees.tests
DJANGO_SETTINGS_MODULE=youpayroll.settings.testing python manage.py test payees.tests.PayeeAdminZohoSyncTest
```

When testing against PostgreSQL instead, ensure the configured database is reachable and the user can create the test database.

## Deployment

Runtime images and entrypoints live under `deployment/app` and `deployment/nginx`.

Helm values are organized by app and environment:

```text
deployment/values/youpayroll/{production,qa,sandbox}/helm/
deployment/values/youpayroll-aps/{production,sandbox}/helm/
```

Terraform configuration is not present in this repository. Keep Terraform-managed infrastructure values aligned with the Helm values and Vault secret paths documented here.

Secrets are expected to come from Vault CSI through the `values-secret-provider-class.yaml` files. Environment-specific secret material should remain in Vault or the deployment system, not in this repository.

Nginx configs are committed under each environment directory. The Vinton Gray Cerf IP allowlist is supplied at runtime through `VINTON_GRAY_CERF_IP_ALLOWLIST`, not hardcoded in nginx config.

## Operational Notes

- Production-like settings raise on missing `SECRET_KEY`, `GOOGLE_CLIENT_ID`, and `FIELD_ENCRYPTION_KEY`.
- `FIELD_ENCRYPTION_KEY` protects encrypted model fields. Rotating it requires a planned token/data re-encryption process.
- GraphQL uses token authentication through project decorators; REST uses DRF token/session auth.
- Audit logging is enabled on sensitive models through `django-auditlog`.
- Pay run and Form 16 tasks include idempotency guards; keep those guarantees when changing task behavior.
