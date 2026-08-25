import os
from datetime import timedelta

from celery.schedules import crontab
from maykin_common.branding import ProductDefinition
from maykin_common.config import DocumentationParams

os.environ["_USE_STRUCTLOG"] = "True"

from open_api_framework.conf.base import *  # noqa
from open_api_framework.conf.utils import config
from maykin_common.health_checks import default_health_check_apps
from .api import *  # noqa

#
# Core Django settings
#

#
# APPLICATIONS enabled for this project
#
INSTALLED_APPS = INSTALLED_APPS + [
    "maykin_common",
    # health check + plugins
    *default_health_check_apps,
    "maykin_common.health_checks.celery",
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
    documentation=DocumentationParams(
        help_text="indicates whether or not sent notifications should be saved to the database.",
        group="Notifications",
    ),
)

NOTIFICATION_REQUESTS_TIMEOUT = config(
    "NOTIFICATION_REQUESTS_TIMEOUT",
    default=10,
    documentation=DocumentationParams(
        help_text="Timeout in seconds for HTTP requests.", group="Notifications"
    ),
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

# Celery
CELERY_BROKER_URL = config(
    "CELERY_BROKER_URL",
    default="amqp://127.0.0.1:5672//",
    documentation=DocumentationParams(
        help_text="the URL of the broker that will be used to actually send the notifications",
        group="Celery",
    ),
)

NOTIFICATION_SEC_INTERVAL = max(
    5,
    config(
        "NOTIFICATION_SEC_INTERVAL",
        default=20,
        documentation=DocumentationParams(
            help_text="The amount of seconds between starting the ``execute_notifications`` task that creates the actual notification request tasks (minimum 5 seconds).",
            group="Celery",
        ),
    ),
)

NOTIFICATION_LIMIT = config(
    "NOTIFICATION_LIMIT",
    default=500,
    documentation=DocumentationParams(
        help_text="the maximum of scheduled notifications to be handled during ``execute_notifications``.",
        group="Celery",
    ),
)


CELERY_REDIS_SOCKET_TIMEOUT = config(
    "CELERY_REDIS_SOCKET_TIMEOUT",
    default=10,
    documentation=DocumentationParams(
        help_text="Socket timeout for reading/writing operations to the Redis server in seconds (int/float), used by the redis result backend.",
        group="Celery",
    ),
)
CELERY_REDIS_SOCKET_CONNECT_TIMEOUT = config(
    "CELERY_REDIS_SOCKET_CONNECT_TIMEOUT",
    default=None,
    documentation=DocumentationParams(
        help_text="Socket timeout for connections to Redis from the result backend in seconds (int/float)",
        group="Celery",
    ),
)

CELERY_BEAT_SCHEDULE = {
    "clean-old-notifications": {
        "task": "nrc.api.tasks.clean_old_notifications",
        # https://docs.celeryproject.org/en/v4.4.7/userguide/periodic-tasks.html#crontab-schedules
        "schedule": crontab(0, 0, day_of_month="1"),
    },
    "execute-notifications": {
        "task": "nrc.api.tasks.execute_notifications",
        "schedule": timedelta(seconds=NOTIFICATION_SEC_INTERVAL),
        "options": {
            "expires": NOTIFICATION_SEC_INTERVAL
            - 1,  # added for when worker is offline and queue gets filled with tasks
        },
    },
}
CELERY_RESULT_EXPIRES = config(
    "CELERY_RESULT_EXPIRES",
    default=3600,
    documentation=DocumentationParams(
        help_text=(
            "How long the results of tasks will be stored in Redis (in seconds),"
            " this can be set to a lower duration to lower memory usage for Redis."
        ),
        group="Celery",
    ),
)

# Add (by default) 5 (soft), 15 (hard) minute timeouts to all Celery tasks.
CELERY_TASK_TIME_LIMIT = config(
    "CELERY_TASK_HARD_TIME_LIMIT",
    default=15 * 60,
    documentation=DocumentationParams(
        help_text=(
            "If a celery task exceeds this time limit, the worker processing the task will "
            "be killed and replaced with a new one."
        ),
        group="Celery",
    ),
)  # hard
CELERY_TASK_SOFT_TIME_LIMIT = config(
    "CELERY_TASK_SOFT_TIME_LIMIT",
    default=5 * 60,
    documentation=DocumentationParams(
        help_text=(
            "If a celery task exceeds this time limit, the ``SoftTimeLimitExceeded`` exception will be raised."
        ),
        group="Celery",
    ),
)  # soft

#
# Delete Notifications
#
NOTIFICATION_NUMBER_OF_DAYS_RETAINED = config(
    "NOTIFICATION_NUMBER_OF_DAYS_RETAINED",
    default=30,
    documentation=DocumentationParams(
        help_text="the number of days for which you wish to keep notifications",
        group="Notifications",
    ),
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
    default="",
    documentation=DocumentationParams(
        help_text=(
            "a comma-separated list of paths to certificates to trust, "
            "If you're using self-signed certificates for the services that Open Notificaties "
            "communicates with, specify the path to those (root) certificates here, rather than "
            "disabling SSL certificate verification. Example: "
            "``EXTRA_VERIFY_CERTS=/etc/ssl/root1.crt,/etc/ssl/root2.crt``."
        )
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
    documentation=DocumentationParams(
        help_text=(
            "Some validation & JWT validation has a time aspect (usually in the form of the ``iat`` and "
            "``nbf`` claims). Clock drift between server and client can occur. This setting allows "
            "specifying the leeway in seconds, and defaults to ``0`` (no leeway). It is advised to "
            "not make this larger than a couple of minutes."
        )
    ),
)

JWT_EXPIRY = config(
    "JWT_EXPIRY",
    default=3600,
    documentation=DocumentationParams(
        help_text="duration a JWT is considered to be valid, in seconds."
    ),
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


#
# MAYKIN-COMMON branding
#
MKN_BRANDING_PRODUCT_DEFINITION = ProductDefinition(
    name="Open Notificaties",
    hyperlink="https://github.com/open-zaak/open-notificaties",
    logo_path="ico/open-notificaties-icon.svg",
)

custom_product_name: str = config(
    "CUSTOM_PRODUCT_NAME",
    default="",
    documentation=DocumentationParams(
        help_text=(
            "Specify the custom product name when redistributing the application, e.g. "
            "as part of your own software suite."
        ),
        group="Branding",
    ),
)
custom_product_url: str = config(
    "CUSTOM_PRODUCT_URL",
    default="",
    documentation=DocumentationParams(
        help_text=(
            "Optional link for the custom product when redistributing the "
            "application. If provided, the product name will be clickable."
        ),
        group="Branding",
    ),
)
custom_product_logo_path: str = config(
    "CUSTOM_PRODUCT_LOGO_PATH",
    default="",
    documentation=DocumentationParams(group="Branding"),
)
custom_product_logo_url: str = config(
    "CUSTOM_PRODUCT_LOGO_URL",
    default="",
    documentation=DocumentationParams(
        help_text=(
            "Optional link for the custom product logo when redistributing the "
            "application. When using externally hosted assets, note that you may "
            "need to tweak the Content-Security-Policy settings."
        ),
        group="Branding",
    ),
)
MKN_BRANDING_DERIVED_PRODUCT_DEFINITION = (
    ProductDefinition(
        name=custom_product_name,
        hyperlink=custom_product_url,
        logo_path=custom_product_logo_path,
        logo_url=custom_product_logo_url,
    )
    if custom_product_name
    else None
)

#
# MAYKIN-COMMON health checks
#
MKN_HEALTH_CHECKS_BEAT_LIVENESS_FILE = BASE_DIR / "tmp" / "celery_beat.live"
MKN_HEALTH_CHECKS_WORKER_EVENT_LOOP_LIVENESS_FILE = (
    BASE_DIR / "tmp" / "celery_worker_event_loop.live"
)
MKN_HEALTH_CHECKS_WORKER_READINESS_FILE = BASE_DIR / "tmp" / "celery_worker.ready"
