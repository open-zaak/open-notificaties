from celery.schedules import crontab
from open_api_framework.conf.base import *  # noqa
from open_api_framework.conf.utils import config

from .api import *  # noqa

init_sentry()

#
# Core Django settings
#

#
# APPLICATIONS enabled for this project
#
INSTALLED_APPS = INSTALLED_APPS + [
    # External applications.
    "vng_api_common.authorizations",
    "vng_api_common.notifications",
    # Project applications.
    "nrc.accounts",
    "nrc.api",
    "nrc.config",
    "nrc.datamodel",
    "nrc.utils",
]

MIDDLEWARE.insert(
    MIDDLEWARE.index("django.contrib.auth.middleware.AuthenticationMiddleware") + 1,
    "vng_api_common.middleware.AuthMiddleware",
)
MIDDLEWARE = MIDDLEWARE + ["vng_api_common.middleware.APIVersionHeaderMiddleware"]

#
# LOGGING
#
#
LOGGING["handlers"]["notifications"] = {
    "level": "INFO",
    "class": "logging.handlers.RotatingFileHandler",
    "filename": LOGGING_DIR / "notifications.log",
    "formatter": "performance",
    "maxBytes": 1024 * 1024 * 10,  # 10 MB
    "backupCount": 10,
}
LOGGING["loggers"]["nrc.api.serializers"] = {
    "handlers": ["notifications"],
    "level": LOG_LEVEL,
    "propagate": False,
}

# using `SESSION_COOKIE_NAME` from OAF would change the name to `nrc_sessionid`
SESSION_COOKIE_NAME = "opennotificaties_sessionid"

#
# Custom settings
#
PROJECT_NAME = "Open Notificaties"
SITE_TITLE = "API dashboard"

LOG_NOTIFICATIONS_IN_DB = config("LOG_NOTIFICATIONS_IN_DB", default=False)


##############################
#                            #
# 3RD PARTY LIBRARY SETTINGS #
#                            #
##############################

#
# MAYKIN-2FA
#
# Uses django-two-factor-auth under the hood, so relevant upstream package settings
# apply too.
#

# we run the admin site monkeypatch instead.
# Relying Party name for WebAuthn (hardware tokens)
# NOTE: We override this setting from open-api-framework, because removing
# this would change the name to `nrc - admin`
TWO_FACTOR_WEBAUTHN_RP_NAME = "Open Notificaties - admin"
# add entries from AUTHENTICATION_BACKENDS that already enforce their own two-factor
# auth, avoiding having some set up MFA again in the project.

# RabbitMQ
BROKER_URL = config("PUBLISH_BROKER_URL", "amqp://guest:guest@localhost:5672/%2F")

# Celery
CELERY_BROKER_URL = config("CELERY_BROKER_URL", "amqp://127.0.0.1:5672//")
CELERY_BEAT_SCHEDULE = {
    "clean-old-notifications": {
        "task": "nrc.api.tasks.clean_old_notifications",
        # https://docs.celeryproject.org/en/v4.4.7/userguide/periodic-tasks.html#crontab-schedules
        "schedule": crontab(0, 0, day_of_month="1"),
    },
}

#
# Delete Notifications
#
NOTIFICATION_NUMBER_OF_DAYS_RETAINED = config(
    "NOTIFICATION_NUMBER_OF_DAYS_RETAINED", 30
)

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
    "nrc.config.notification_retry.NotificationRetryConfigurationStep",
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

# setup configuration for Notification retry
# Retry settings for delivering notifications to subscriptions
NOTIFICATION_RETRY_CONFIG_ENABLE = config(
    "NOTIFICATION_RETRY_CONFIG_ENABLE", default=True
)
NOTIFICATION_DELIVERY_MAX_RETRIES = config("NOTIFICATION_DELIVERY_MAX_RETRIES", None)
NOTIFICATION_DELIVERY_RETRY_BACKOFF = config(
    "NOTIFICATION_DELIVERY_RETRY_BACKOFF", None
)
NOTIFICATION_DELIVERY_RETRY_BACKOFF_MAX = config(
    "NOTIFICATION_DELIVERY_RETRY_BACKOFF_MAX", None
)
