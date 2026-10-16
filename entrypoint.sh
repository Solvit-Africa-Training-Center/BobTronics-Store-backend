#!/bin/sh
set -e

echo "==> Running collectstatic..."
python manage.py collectstatic --noinput

echo "==> Applying database migrations..."
python manage.py migrate --noinput

if [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "==> Ensuring superuser exists and is active..."
    python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.accounts.models import User, Role
email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
first_name = os.environ.get('DJANGO_SUPERUSER_FIRST_NAME', 'Admin')
last_name = os.environ.get('DJANGO_SUPERUSER_LAST_NAME', 'BobTronics')
user, created = User.objects.get_or_create(email=email, defaults={'first_name': first_name, 'last_name': last_name})
user.set_password(password)
user.role = Role.SUPER_ADMIN
user.is_staff = True
user.is_superuser = True
user.is_active = True
user.save()
print(f'==> Superuser {email} configured successfully (Active: True, Role: super_admin)')
" || true
fi

echo "==> Starting Gunicorn on port ${PORT:-8000}..."
exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
