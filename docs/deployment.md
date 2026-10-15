# Render deployment

Deploy this Django API as a Render web service backed by a managed PostgreSQL database. Payments are not configured in this deployment.

## Render commands

Build command:

```sh
pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
```

Start command:

```sh
gunicorn config.wsgi:application
```

## Environment variables

Set these in the Render service's environment settings. Do not commit real values to the repository.

| Name | Purpose |
| --- | --- |
| `SECRET_KEY` | Private Django signing key. Required when `DEBUG=False`. Generate a new value for production. |
| `DEBUG` | Set to `False` in Render. Locally, the existing `.env` may set this to `True`. |
| `ALLOWED_HOSTS` | Optional comma-separated hostnames. The Render hostname is added automatically. |
| `CSRF_TRUSTED_ORIGINS` | Optional comma-separated full origins, including scheme, for unsafe browser requests. |
| `CORS_ALLOWED_ORIGINS` | Comma-separated full origins allowed to call the API from the frontend. Set the actual frontend origin(s); there is no allow-all mode. |
| `DATABASE_URL` | Render PostgreSQL connection URL. When present, it takes precedence over the local `DB_*` settings. |

Render provides `RENDER_EXTERNAL_HOSTNAME` automatically. The application uses it to add the service hostname to `ALLOWED_HOSTS` and its HTTPS origin to `CSRF_TRUSTED_ORIGINS`.

The existing `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT` variables remain available for local database configuration when `DATABASE_URL` is unset. Email configuration and `SITE_URL` remain as currently defined in settings.

Generate a secret key with:

```sh
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Store the generated value directly in Render's environment settings. Do not put it in source control.

## First administrator

After the database migrations complete, open a Render shell for the web service and run:

```sh
python manage.py createsuperuser
```

Enter the administrator's email address, first name, last name, and a strong password at the prompts. The custom user model uses email for login and the manager assigns the superuser role and staff flags. Enter the password only at the interactive prompt; do not pass it in a command or commit it to a file.

## Post-deploy checklist

1. Open `/api/v1/health/` and confirm it returns `{"status":"ok"}`.
2. Open `/api/docs/` (which redirects to `/api/v1/docs/`) and confirm the Swagger UI loads.
3. From the deployed frontend, make an API request and confirm the browser accepts the response from its configured origin. Check the browser console and network response for CORS errors.
4. Open `/admin/` and confirm the admin page styling loads.
5. Sign in to the admin site with the email and password created above.

## Troubleshooting

| Symptom | Likely cause | What to check |
| --- | --- | --- |
| `DisallowedHost` | The request hostname is missing from `ALLOWED_HOSTS`. | Confirm Render provides `RENDER_EXTERNAL_HOSTNAME`, or add the exact service hostname to `ALLOWED_HOSTS`. |
| Browser reports a CORS error | The frontend origin is missing or does not exactly match the configured origin. | Set `CORS_ALLOWED_ORIGINS` with the full scheme and hostname (and port when applicable); do not include a path. |
| Swagger CSS or UI assets are missing | The browser cannot load Swagger UI's configured assets, or the request is blocked by a browser/network policy. | Check the browser network panel for failed Swagger asset requests and verify `/api/v1/docs/` loads. Admin static files are collected and served by WhiteNoise. |
| Build fails during `collectstatic` or `migrate` | A dependency, environment variable, or database connection is missing or invalid. | Review the Render build log; confirm the build command, `SECRET_KEY`, and managed PostgreSQL `DATABASE_URL` are set correctly. |
