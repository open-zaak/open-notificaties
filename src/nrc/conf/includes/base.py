import os

from celery.schedules import crontab

os.environ["_USE_STRUCTLOG"] = "True"

from open_api_framework.conf.base import *  # noqa
from open_api_framework.conf.utils import config

from .api import *  # noqa

#
# Core Django settings
#

#
# APPLICATIONS enabled for this project
#
INSTALLED_APPS = INSTALLED_APPS + [
    "maykin_common",
    "capture_tag",
    # `django.contrib.sites` added at the project level because it has been removed at the packages level.
    # This component is deprecated and should be completely removed.
    # To determine the project's domain, use the `SITE_DOMAIN` environment variable.
    "django.contrib.sites",
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
MIDDLEWARE += ["vng_api_common.middleware.APIVersionHeaderMiddleware"]

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

NOTIFICATION_REQUESTS_TIMEOUT = config(
    "NOTIFICATION_REQUESTS_TIMEOUT",
    default=10,
    help_text="Timeout in seconds for HTTP requests.",
    group="Notifications",
)


CLOUDEVENT_SPECVERSION = "1.0"


# Default (connection timeout, read timeout) for the requests library (in seconds)
REQUESTS_DEFAULT_TIMEOUT = (10, 30)


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
    "execute-notifications": {
        "task": "nrc.api.tasks.execute_notifications",
        "schedule": crontab("*", "*", "*", "*", "*"),
    },
}
CELERY_RESULT_EXPIRES = config(
    "CELERY_RESULT_EXPIRES",
    3600,
    help_text=(
        "How long the results of tasks will be stored in Redis (in seconds),"
        " this can be set to a lower duration to lower memory usage for Redis."
    ),
    group="Celery",
)

# Add (by default) 5 (soft), 15 (hard) minute timeouts to all Celery tasks.
CELERY_TASK_TIME_LIMIT = config(
    "CELERY_TASK_HARD_TIME_LIMIT",
    default=15 * 60,
    help_text=(
        "If a celery task exceeds this time limit, the worker processing the task will "
        "be killed and replaced with a new one."
    ),
    group="Celery",
)  # hard
CELERY_TASK_SOFT_TIME_LIMIT = config(
    "CELERY_TASK_SOFT_TIME_LIMIT",
    default=5 * 60,
    help_text=(
        "If a celery task exceeds this time limit, the ``SoftTimeLimitExceeded`` exception will be raised."
    ),
    group="Celery",
)  # soft

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
    "nrc.setup_configuration.authorization.AuthorizationStep",
    "vng_api_common.contrib.setup_configuration.steps.JWTSecretsConfigurationStep",
    "nrc.setup_configuration.kanalen.KanaalConfigurationStep",
    "nrc.setup_configuration.steps.NotificationConfigurationStep",
    "notifications_api_common.contrib.setup_configuration.steps.NotificationSubscriptionConfigurationStep",
    "nrc.setup_configuration.abonnementen.AbonnementConfigurationStep",
    "django_setup_configuration.contrib.sites.steps.SitesConfigurationStep",
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

#
# NOTIFICATIONS-API-COMMON
#
NOTIFICATIONS_API_GET_DOMAIN = "nrc.utils.get_domain"

#
# DJANGO-STRUCTLOG
#
DJANGO_STRUCTLOG_IP_LOGGING_ENABLED = False
DJANGO_STRUCTLOG_CELERY_ENABLED = True


TIME_LEEWAY = config(
    "TIME_LEEWAY",
    default=0,
    help_text=(
        "Some validation & JWT validation has a time aspect (usually in the form of the ``iat`` and "
        "``nbf`` claims). Clock drift between server and client can occur. This setting allows "
        "specifying the leeway in seconds, and defaults to ``0`` (no leeway). It is advised to "
        "not make this larger than a couple of minutes."
    ),
)

JWT_EXPIRY = config(
    "JWT_EXPIRY",
    default=3600,
    help_text="duration a JWT is considered to be valid, in seconds.",
)

#
# Django-Admin-Index
#
ADMIN_INDEX_DISPLAY_DROP_DOWN_MENU_CONDITION_FUNCTION = (
    "maykin_common.django_two_factor_auth.should_display_dropdown_menu"
)


#
# SECURITY settings
#
CSRF_FAILURE_VIEW = "maykin_common.views.csrf_failure"

# This setting is used by the csrf_failure view (accounts app).
# You can specify any path that should match the request.path
# Note: the LOGIN_URL Django setting is not used because you could have
# multiple login urls defined.
LOGIN_URLS = [reverse_lazy("admin:login")]
