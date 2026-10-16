import os
from django.apps import AppConfig
from django.db.models.signals import post_migrate


def auto_create_superuser(sender, **kwargs):
    email = os.environ.get("DJANGO_SUPERUSER_EMAIL") or os.environ.get("ADMIN_EMAIL")
    password = os.environ.get("DJANGO_SUPERUSER_PASSWORD") or os.environ.get("ADMIN_PASSWORD")
    if email and password:
        try:
            from apps.accounts.models import User, Role
            user, created = User.objects.get_or_create(
                email=email.strip().lower(),
                defaults={
                    "first_name": os.environ.get("DJANGO_SUPERUSER_FIRST_NAME", "Admin"),
                    "last_name": os.environ.get("DJANGO_SUPERUSER_LAST_NAME", "BobTronics"),
                },
            )
            user.set_password(password)
            user.role = Role.SUPER_ADMIN
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.save()
            print(f"[post_migrate] Superuser {email} configured successfully (Active: True, Staff: True, Superuser: True)")
        except Exception as exc:
            print(f"[post_migrate] Superuser setup skipped: {exc}")


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"

    def ready(self):
        post_migrate.connect(auto_create_superuser, sender=self)
