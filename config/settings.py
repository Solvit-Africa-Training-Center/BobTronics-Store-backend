"""Django settings for the BobTronics Store API."""
from datetime import timedelta
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = [host.strip() for host in config("ALLOWED_HOSTS", default="localhost,127.0.0.1").split(",") if host.strip()]

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "corsheaders",
    "apps.common.apps.CommonConfig", "apps.accounts.apps.AccountsConfig",
    "apps.catalog.apps.CatalogConfig", "apps.services.apps.ServicesConfig",
    "apps.cart.apps.CartConfig", "apps.wishlist.apps.WishlistConfig",
    "apps.orders.apps.OrdersConfig", "apps.payments.apps.PaymentsConfig",
    "apps.deliveries.apps.DeliveriesConfig", "apps.promotions.apps.PromotionsConfig",
    "apps.reviews.apps.ReviewsConfig", "apps.audit.apps.AuditConfig",
    "rest_framework", "django_filters", "drf_spectacular",
    "rest_framework_simplejwt.token_blacklist",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware", "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware", "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in config(
        "CORS_ALLOWED_ORIGINS",
        default="http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request", "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
AUTH_USER_MODEL = "accounts.User"

DATABASES = {"default": {
    "ENGINE": config("DB_ENGINE", default="django.db.backends.sqlite3"),
    "NAME": config("DB_NAME", default=str(BASE_DIR / "db.sqlite3")),
    "USER": config("DB_USER", default=""), "PASSWORD": config("DB_PASSWORD", default=""),
    "HOST": config("DB_HOST", default=""), "PORT": config("DB_PORT", default=""),
}}
CACHES = {
    "default": {
        # Shared by workers using the same database; deployments can override
        # this with a shared Redis or Memcached backend.
        "BACKEND": config("CACHE_BACKEND", default="django.core.cache.backends.db.DatabaseCache"),
        "LOCATION": config("CACHE_LOCATION", default="django_cache"),
    }
}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "USER_ID_FIELD": "user_id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_HEADER_TYPES": ("Bearer",),
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework_simplejwt.authentication.JWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "config.settings.api_exception_handler",
    "DEFAULT_THROTTLE_RATES": {
        "auth_login": "5/minute",
        "auth_register": "10/hour",
        "auth_password_reset": "3/hour",
    },
}
SPECTACULAR_SETTINGS = {
    "TITLE": "BØB TRONICS Store API", "DESCRIPTION": "Backend API for the BØB TRONICS Store.",
    "VERSION": "1.0.0", "SERVE_INCLUDE_SCHEMA": False,
}
EMAIL_BACKEND = config("EMAIL_BACKEND", default="").strip() or (
    "django.core.mail.backends.console.EmailBackend"
    if DEBUG
    else "django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = int(config("EMAIL_PORT", default="587") or 587)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="") or "noreply@localhost"

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(config("MEDIA_ROOT", default=str(BASE_DIR / "media")))


def _first_error_message(value):
    """Return the first readable validation message from nested DRF errors."""
    if isinstance(value, dict):
        for nested in value.values():
            message = _first_error_message(nested)
            if message:
                return message
        return ""
    if isinstance(value, (list, tuple)):
        for nested in value:
            message = _first_error_message(nested)
            if message:
                return message
        return ""
    return str(value) if value is not None else ""


def api_exception_handler(exc, context):
    """Return concise, customer-friendly API errors in a consistent envelope."""
    from rest_framework.views import exception_handler
    response = exception_handler(exc, context)
    if response is None:
        return None
    details = response.data
    message = _first_error_message(details)
    if response.status_code == 401:
        message = "Please log in to continue."
    elif response.status_code == 403:
        message = "Access to this action is not allowed."
    elif response.status_code == 404:
        message = "We couldn't find what you requested."
    elif response.status_code == 400:
        if isinstance(details, dict) and len(details) > 1:
            message = "Please check the form fields."
        message = message or "Please check your information."
    else:
        message = message or "Request could not be completed."
    response.data = {"success": False, "error": {
        "status_code": response.status_code, "message": message, "details": details,
    }}
    return response
