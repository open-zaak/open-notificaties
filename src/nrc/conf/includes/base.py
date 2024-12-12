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
    "nrc.setup_configuration",
    "nrc.datamodel",
    "nrc.utils",
]

MIDDLEWARE.insert(
    MIDDLEWARE.index("django.contrib.auth.middleware.AuthenticationMiddleware") + 1,
    "vng_api_common.authorizations.middleware.AuthMiddleware",
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

LOG_NOTIFICATIONS_IN_DB = config(
    "LOG_NOTIFICATIONS_IN_DB",
    default=False,
    help_text="indicates whether or not sent notifications should be saved to the database.",
    group="Notifications",
)


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
# TODO is this actually used?
BROKER_URL = config(
    "PUBLISH_BROKER_URL",
    "amqp://guest:guest@localhost:5672/%2F",
    help_text="the URL of the broker that will be used to actually send the notifications",
    group="Celery",
)

# Celery
CELERY_BROKER_URL = config(
    "CELERY_BROKER_URL",
    "amqp://127.0.0.1:5672//",
    help_text="the URL of the broker that will be used to actually send the notifications",
    group="Celery",
)
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
    "NOTIFICATION_NUMBER_OF_DAYS_RETAINED",
    30,
    help_text="the number of days for which you wish to keep notifications",
    group="Notifications",
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
    "mozilla_django_oidc_db.setup_configuration.steps.AdminOIDCConfigurationStep",
    "zgw_consumers.contrib.setup_configuration.steps.ServiceConfigurationStep",
    "vng_api_common.contrib.setup_configuration.steps.JWTSecretsConfigurationStep",
    "nrc.setup_configuration.authorization.AuthorizationStep",
    "nrc.setup_configuration.kanalen.KanaalConfigurationStep",
]

#
# self-certifi
#
# To make sure this variable appears in the documentation
config(
    "EXTRA_VERIFY_CERTS",
    "",
    help_text=(
        "a comma-separated list of paths to certificates to trust, "
        "If you're using self-signed certificates for the services that Open Notificaties "
        "communicates with, specify the path to those (root) certificates here, rather than "
        "disabling SSL certificate verification. Example: "
        "``EXTRA_VERIFY_CERTS=/etc/ssl/root1.crt,/etc/ssl/root2.crt``."
    ),
)
