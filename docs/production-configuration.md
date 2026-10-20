# Production configuration

Set the following environment values on the deployment service:

- `CORS_ALLOWED_ORIGINS`: comma-separated exact frontend origins, including
  scheme and port where relevant. Local development defaults allow ports 3000.
- `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, plus
  `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`,
  `EMAIL_USE_TLS`, and a real `DEFAULT_FROM_EMAIL`. In production, the default
  backend is SMTP; the console backend is only the development default.
- `CACHE_BACKEND` and `CACHE_LOCATION`: the default is Django's database cache,
  shared by workers that use the same database. Its table is created by the
  database-cache migration. Redis or Memcached can be used instead by setting these values to
  the corresponding shared backend and its location. Avoid process-local
  memory cache in multi-worker deployments because login lockouts and API
  throttles would not be shared.

Uploaded media still needs a production serving/storage backend. `MEDIA_ROOT`
can point to a persistent disk, but this project currently serves media routes
only with `DEBUG=True`. A persistent disk alone will not make production image
URLs available.
