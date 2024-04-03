import datetime
import os
from pathlib import Path

from django.urls import reverse_lazy

import sentry_sdk
from celery.schedules import crontab
from corsheaders.defaults import default_headers as default_cors_headers
from log_outgoing_requests.formatters import HttpFormatter

from .api import *  # noqa
from .environ import config, get_sentry_integrations

# Build paths inside the project, so further paths can be defined relative to
# the code root.
DJANGO_PROJECT_DIR = Path(__file__).resolve(strict=True).parents[2]
BASE_DIR = DJANGO_PROJECT_DIR.parents[1]

#
# Core Django settings
#
SITE_ID = config("SITE_ID", default=1)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY")

# NEVER run with DEBUG=True in production-like environments
DEBUG = config("DEBUG", default=False)

# = domains we're running on
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="", split=True)

IS_HTTPS = config("IS_HTTPS", default=not DEBUG)

# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/

LANGUAGE_CODE = "nl-nl"

TIME_ZONE = "UTC"  # note: this *may* affect the output of DRF datetimes

USE_I18N = True

USE_L10N = True

USE_TZ = True

USE_THOUSAND_SEPARATOR = True

#
# DATABASE and CACHING setup
#
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", "opennotificaties"),
        "USER": config("DB_USER", "opennotificaties"),
        "PASSWORD": config("DB_PASSWORD", "opennotificaties"),
        "HOST": config("DB_HOST", "localhost"),
        "PORT": config("DB_PORT", 5432),
    }
}

# TODO: switch to BigAutoField after the Django 3.2 upgrade and generate migrations
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{config('CACHE_DEFAULT', 'localhost:6379/0')}",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
        },
    },
    "axes": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{config('CACHE_AXES', 'localhost:6379/0')}",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
        },
    },
    "oidc": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{config('CACHE_DEFAULT', 'localhost:6379/0')}",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
        },
    },
}

#
# APPLICATIONS enabled for this project
#
INSTALLED_APPS = [
    # Note: contenttypes should be first, see Django ticket #10827
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    # Note: If enabled, at least one Site object is required
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Optional applications.
    "ordered_model",
    "django_admin_index",
    "django.contrib.admin",
    # 'django.contrib.admindocs',
    # 'django.contrib.humanize',
    # External applications.
    "axes",
    "django_filters",
    "corsheaders",
    "vng_api_common",  # before drf_yasg to override the management command
    "vng_api_common.authorizations",
    "vng_api_common.notifications",
    "notifications_api_common",
    "drf_yasg",
    "rest_framework",
    "solo",
    "django_jsonform",
    "mozilla_django_oidc",
    "mozilla_django_oidc_db",
    "zgw_consumers",
    "django_setup_configuration",
    # Project applications.
    "nrc.accounts",
    "nrc.api",
    "nrc.config",
    "nrc.datamodel",
    "nrc.utils",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # 'django.middleware.locale.LocaleMiddleware',
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "vng_api_common.middleware.AuthMiddleware",
    "mozilla_django_oidc_db.middleware.SessionRefresh",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "vng_api_common.middleware.APIVersionHeaderMiddleware",
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "nrc.urls"

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
)

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [DJANGO_PROJECT_DIR / "templates"],
        "APP_DIRS": False,  # conflicts with explicity specifying the loaders
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "nrc.utils.context_processors.settings",
            ],
            "loaders": TEMPLATE_LOADERS,
        },
    }
]

WSGI_APPLICATION = "nrc.wsgi.application"

# Translations
LOCALE_PATHS = (DJANGO_PROJECT_DIR / "conf" / "locale",)

#
# SERVING of static and media files
#

STATIC_URL = "/static/"

STATIC_ROOT = BASE_DIR / "static"

# Additional locations of static files
STATICFILES_DIRS = [DJANGO_PROJECT_DIR / "static"]

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

MEDIA_ROOT = BASE_DIR / "media"

MEDIA_URL = "/media/"

FIXTURE_DIRS = [DJANGO_PROJECT_DIR / "fixtures"]

#
# Sending EMAIL
#
EMAIL_HOST = config("EMAIL_HOST", default="localhost")
EMAIL_PORT = config(
    "EMAIL_PORT", default=25
)  # disabled on Google Cloud, use 487 instead
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=False)
EMAIL_TIMEOUT = 10

DEFAULT_FROM_EMAIL = "opennotificaties@example.com"

#
# LOGGING
#
LOGGING_DIR = BASE_DIR / "log"
LOG_REQUESTS = config("LOG_REQUESTS", default=False)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s %(levelname)s %(name)s %(module)s %(process)d %(thread)d  %(message)s"
        },
        "timestamped": {"format": "%(asctime)s %(levelname)s %(name)s  %(message)s"},
        "simple": {"format": "%(levelname)s  %(message)s"},
        "performance": {"format": "%(asctime)s %(process)d | %(thread)d | %(message)s"},
        "outgoing_requests": {"()": HttpFormatter},
    },
    "filters": {"require_debug_false": {"()": "django.utils.log.RequireDebugFalse"}},
    "handlers": {
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
        "null": {"level": "DEBUG", "class": "logging.NullHandler"},
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "timestamped",
        },
        "django": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGGING_DIR / "django.log",
            "formatter": "verbose",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 10,
        },
        "project": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGGING_DIR / "nrc.log",
            "formatter": "verbose",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 10,
        },
        "performance": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGGING_DIR / "performance.log",
            "formatter": "performance",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 10,
        },
        "notifications": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGGING_DIR / "notifications.log",
            "formatter": "performance",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 10,
        },
        "log_outgoing_requests": {
            "level": "DEBUG",
            "formatter": "outgoing_requests",
            "class": "logging.StreamHandler",  # to write to stdout
        },
        "save_outgoing_requests": {
            "level": "DEBUG",
            # enabling saving to database
            "class": "log_outgoing_requests.handlers.DatabaseOutgoingRequestsHandler",
        },
    },
    "loggers": {
        "nrc": {"handlers": ["project"], "level": "INFO", "propagate": True},
        "nrc.api.serializers": {
            "handlers": ["notifications"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {"handlers": ["django"], "level": "ERROR", "propagate": True},
        "django.template": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "mozilla_django_oidc": {
            "handlers": ["project"],
            "level": "DEBUG",
        },
        "log_outgoing_requests": {
            "handlers": ["log_outgoing_requests", "save_outgoing_requests"]
            if LOG_REQUESTS
            else [],
            "level": "DEBUG",
            "propagate": True,
        },
    },
}

LOG_OUTGOING_REQUESTS_DB_SAVE = config("LOG_OUTGOING_REQUESTS_DB_SAVE", default=False)
LOG_OUTGOING_REQUESTS_DB_SAVE_BODY = config(
    "LOG_OUTGOING_REQUESTS_DB_SAVE_BODY", default=False
)
LOG_OUTGOING_REQUESTS_EMIT_BODY = config(
    "LOG_OUTGOING_REQUESTS_EMIT_BODY", default=False
)


#
# AUTH settings - user accounts, passwords, backends...
#
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Allow logging in with both username+password and email+password
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesBackend",
    "nrc.accounts.backends.UserModelEmailBackend",
    "django.contrib.auth.backends.ModelBackend",
    "mozilla_django_oidc_db.backends.OIDCAuthenticationBackend",
]

SESSION_COOKIE_NAME = "opennotificaties_sessionid"

LOGIN_URL = reverse_lazy("admin:login")
LOGIN_REDIRECT_URL = reverse_lazy("admin:index")
LOGOUT_REDIRECT_URL = reverse_lazy("admin:index")

#
# SECURITY settings
#
SESSION_COOKIE_SECURE = IS_HTTPS
SESSION_COOKIE_HTTPONLY = True

CSRF_COOKIE_SECURE = IS_HTTPS

X_FRAME_OPTIONS = "DENY"

#
# Silenced checks
#
SILENCED_SYSTEM_CHECKS = [
    "rest_framework.W001",
    "debug_toolbar.W006",
]

#
# Custom settings
#
PROJECT_NAME = "Open Notificaties"
SITE_TITLE = "API dashboard"

ENVIRONMENT = None
ENVIRONMENT_SHOWN_IN_ADMIN = True

LOG_NOTIFICATIONS_IN_DB = config("LOG_NOTIFICATIONS_IN_DB", default=False)

# Generating the schema, depending on the component
subpath = config("SUBPATH", None)
if subpath:
    if not subpath.startswith("/"):
        subpath = f"/{subpath}"
    SUBPATH = subpath

if "GIT_SHA" in os.environ:
    GIT_SHA = config("GIT_SHA", "")
# in docker (build) context, there is no .git directory
elif BASE_DIR.joinpath(".git").exists():
    try:
        import git
    except ImportError:
        GIT_SHA = None
    else:
        repo = git.Repo(search_parent_directories=True)
        GIT_SHA = repo.head.object.hexsha
else:
    GIT_SHA = None

RELEASE = config("RELEASE", GIT_SHA)

NUM_PROXIES = config(  # TODO: this also is relevant for DRF settings if/when we have rate-limited endpoints
    "NUM_PROXIES",
    default=1,
    cast=lambda val: int(val) if val is not None else None,
)

##############################
#                            #
# 3RD PARTY LIBRARY SETTINGS #
#                            #
##############################

# Django-axes
AXES_CACHE = "axes"  # refers to CACHES setting
AXES_FAILURE_LIMIT = 5  # Default: 3
AXES_LOCK_OUT_AT_FAILURE = True  # Default: True
AXES_COOLOFF_TIME = datetime.timedelta(minutes=5)
AXES_LOCKOUT_PARAMETERS = [["ip_address", "user_agent", "username"]]
# By default, Axes obfuscates values for formfields named "password", but the admin
# interface login formfield name is "auth-password", so we obfuscate that as well
AXES_SENSITIVE_PARAMETERS = ["password", "auth-password"]  # nosec

AXES_IPWARE_PROXY_COUNT = NUM_PROXIES - 1 if NUM_PROXIES else None
# The default meta precedence order
AXES_IPWARE_META_PRECEDENCE_ORDER = (
    "HTTP_X_FORWARDED_FOR",
    "X_FORWARDED_FOR",  # <client>, <proxy1>, <proxy2>
    "HTTP_CLIENT_IP",
    "HTTP_X_REAL_IP",
    "HTTP_X_FORWARDED",
    "HTTP_X_CLUSTER_CLIENT_IP",
    "HTTP_FORWARDED_FOR",
    "HTTP_FORWARDED",
    "HTTP_VIA",
    "REMOTE_ADDR",
)

#
# DJANGO-CORS-MIDDLEWARE
#
CORS_ALLOW_ALL_ORIGINS = config("CORS_ALLOW_ALL_ORIGINS", default=False)
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", split=True, default=[])
CORS_ALLOWED_ORIGIN_REGEXES = config(
    "CORS_ALLOWED_ORIGIN_REGEXES", split=True, default=[]
)
# Authorization is included in default_cors_headers
CORS_ALLOW_HEADERS = list(default_cors_headers) + config(
    "CORS_EXTRA_ALLOW_HEADERS", split=True, default=[]
)
# Django's SESSION_COOKIE_SAMESITE = "Lax" prevents session cookies from being sent
# cross-domain. There is no need for these cookies to be sent, since the API itself
# uses Bearer Authentication.

#
# SENTRY - error monitoring
#
SENTRY_DSN = config("SENTRY_DSN", None)

if SENTRY_DSN:
    SENTRY_CONFIG = {
        "dsn": SENTRY_DSN,
        "release": RELEASE or "RELEASE not set",
        "environment": ENVIRONMENT or "",
    }

    sentry_sdk.init(
        **SENTRY_CONFIG,
        integrations=get_sentry_integrations(),
        send_default_pii=True,
    )

# RabbitMQ
BROKER_URL = config("PUBLISH_BROKER_URL", "amqp://guest:guest@localhost:5672/%2F")

# Celery
CELERY_BROKER_URL = config("CELERY_BROKER_URL", "amqp://127.0.0.1:5672//")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
CELERY_BEAT_SCHEDULE = {
    "clean-old-notifications": {
        "task": "nrc.api.tasks.clean_old_notifications",
        # https://docs.celeryproject.org/en/v4.4.7/userguide/periodic-tasks.html#crontab-schedules
        "schedule": crontab(0, 0, day_of_month="1"),
    },
}

# Retry settings for delivering notifications to subscriptions
NOTIFICATION_DELIVERY_MAX_RETRIES = config("NOTIFICATION_DELIVERY_MAX_RETRIES", 5)
NOTIFICATION_DELIVERY_RETRY_BACKOFF = config("NOTIFICATION_DELIVERY_RETRY_BACKOFF", 3)
NOTIFICATION_DELIVERY_RETRY_BACKOFF_MAX = config(
    "NOTIFICATION_DELIVERY_RETRY_BACKOFF_MAX", 48
)

#
# DJANGO-ADMIN-INDEX
#
ADMIN_INDEX_SHOW_REMAINING_APPS_TO_SUPERUSERS = False
ADMIN_INDEX_AUTO_CREATE_APP_GROUP = False


#
# OpenZaak configuration
#

OPENNOTIFICATIES_API_CONTACT_EMAIL = "support@maykinmedia.nl"
OPENNOTIFICATIES_API_CONTACT_URL = "https://www.maykinmedia.nl"

#
# Mozilla Django OIDC DB settings
#
OIDC_AUTHENTICATION_CALLBACK_URL = "oidc_authentication_callback"
OIDC_AUTHENTICATE_CLASS = "mozilla_django_oidc_db.views.OIDCAuthenticationRequestView"
MOZILLA_DJANGO_OIDC_DB_CACHE = "oidc"
MOZILLA_DJANGO_OIDC_DB_CACHE_TIMEOUT = 5 * 60

#
# Delete Notifications
#
NOTIFICATION_NUMBER_OF_DAYS_RETAINED = config(
    "NOTIFICATION_NUMBER_OF_DAYS_RETAINED", 30
)

#
# Elastic APM
#
ELASTIC_APM_SERVER_URL = config("ELASTIC_APM_SERVER_URL", None)
ELASTIC_APM = {
    "SERVICE_NAME": f"Open Notificaties - {ENVIRONMENT}",
    "SECRET_TOKEN": config("ELASTIC_APM_SECRET_TOKEN", "default"),
    "SERVER_URL": ELASTIC_APM_SERVER_URL,
    "TRANSACTION_SAMPLE_RATE": config("ELASTIC_APM_TRANSACTION_SAMPLE_RATE", 0.1),
}
if not ELASTIC_APM_SERVER_URL:
    ELASTIC_APM["ENABLED"] = False
    ELASTIC_APM["SERVER_URL"] = "http://localhost:8200"
else:
    MIDDLEWARE = ["elasticapm.contrib.django.middleware.TracingMiddleware"] + MIDDLEWARE
    INSTALLED_APPS = INSTALLED_APPS + [
        "elasticapm.contrib.django",
    ]

#
# ZGW-CONSUMERS
#
ZGW_CONSUMERS_TEST_SCHEMA_DIRS = [
    DJANGO_PROJECT_DIR / "tests" / "schemas",
]

#
# Django setup configuration
#
SETUP_CONFIGURATION_STEPS = [
    "nrc.config.site.SiteConfigurationStep",
    "nrc.config.authorization.AuthorizationStep",
    "nrc.config.authorization.OpenZaakAuthStep",
]

#
# Open Notificaties settings
#

# Settings for setup_configuration command
# sites config
SITES_CONFIG_ENABLE = config("SITES_CONFIG_ENABLE", default=True)
OPENNOTIFICATIES_DOMAIN = config("OPENNOTIFICATIES_DOMAIN", "")
OPENNOTIFICATIES_ORGANIZATION = config("OPENNOTIFICATIES_ORGANIZATION", "")
# notif -> OZ auth config
AUTHORIZATION_CONFIG_ENABLE = config("AUTHORIZATION_CONFIG_ENABLE", default=True)
AUTORISATIES_API_ROOT = config("AUTORISATIES_API_ROOT", "")
NOTIF_OPENZAAK_CLIENT_ID = config("NOTIF_OPENZAAK_CLIENT_ID", "")
NOTIF_OPENZAAK_SECRET = config("NOTIF_OPENZAAK_SECRET", "")
# OZ -> notif config
OPENZAAK_NOTIF_CONFIG_ENABLE = config("OPENZAAK_NOTIF_CONFIG_ENABLE", default=True)
OPENZAAK_NOTIF_CLIENT_ID = config("OPENZAAK_NOTIF_CLIENT_ID", "")
OPENZAAK_NOTIF_SECRET = config("OPENZAAK_NOTIF_SECRET", "")
