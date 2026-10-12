"""Django settings for the BobTronics Store API."""
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = [host.strip() for host in config("ALLOWED_HOSTS", default="localhost,127.0.0.1").split(",") if host.strip()]

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "apps.common.apps.CommonConfig", "apps.accounts.apps.AccountsConfig",
    "apps.catalog.apps.CatalogConfig", "apps.services.apps.ServicesConfig",
    "apps.cart.apps.CartConfig", "apps.wishlist.apps.WishlistConfig",
    "apps.orders.apps.OrdersConfig", "apps.payments.apps.PaymentsConfig",
    "apps.deliveries.apps.DeliveriesConfig", "apps.promotions.apps.PromotionsConfig",
    "apps.reviews.apps.ReviewsConfig", "apps.audit.apps.AuditConfig",
    "rest_framework", "django_filters", "drf_spectacular",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware", "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware", "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
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

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework_simplejwt.authentication.JWTAuthentication",),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "config.settings.api_exception_handler",
}
SPECTACULAR_SETTINGS = {
    "TITLE": "B?B TRONICS Store API", "DESCRIPTION": "Backend API for the B?B TRONICS Store.",
    "VERSION": "1.0.0", "SERVE_INCLUDE_SCHEMA": False,
}
MAILERS = {"default": {"BACKEND": "django.core.mail.backends.console.EmailBackend"}}

def api_exception_handler(exc, context):
    """Return API errors in a consistent envelope."""
    from rest_framework.views import exception_handler
    response = exception_handler(exc, context)
    if response is None:
        return None
    details = response.data
    if isinstance(details, dict) and "detail" in details:
        message = str(details["detail"])
    else:
        message = "Request validation failed" if response.status_code == 400 else "Request failed"
    response.data = {"success": False, "error": {
        "status_code": response.status_code, "message": message, "details": details,
    }}
    return response
