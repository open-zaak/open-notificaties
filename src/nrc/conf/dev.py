import os
import sys
import warnings

os.environ.setdefault("DEBUG", "yes")
os.environ.setdefault("ALLOWED_HOSTS", "*")
os.environ.setdefault(
    "SECRET_KEY", "rt@lin*q6@wy)xd**5#xz)1p@sqcfj*@w77wn-in2+1zq6*a)m"
)
os.environ.setdefault("IS_HTTPS", "no")
os.environ.setdefault("RELEASE", "dev")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DISABLE_2FA", "True")

os.environ.setdefault("DB_NAME", "opennotificaties")
os.environ.setdefault("DB_USER", "opennotificaties")
os.environ.setdefault("DB_PASSWORD", "opennotificaties")

from .includes.base import *  # noqa isort:skip

#
# Standard Django settings.
#
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

LOGGING["loggers"].update(
    {
        "nrc": {"handlers": ["console"], "level": "DEBUG", "propagate": True},
        "django": {"handlers": ["console"], "level": "DEBUG", "propagate": True},
        "django.utils.autoreload": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["django"],
            "level": "DEBUG",
            "propagate": False,
        },
        "performance": {"handlers": ["console"], "level": "INFO", "propagate": True},
    }
)

#
# Library settings
#

# Django debug toolbar
INSTALLED_APPS += ["debug_toolbar"]
MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
INTERNAL_IPS = ("127.0.0.1",)
DEBUG_TOOLBAR_CONFIG = {"INTERCEPT_REDIRECTS": False}

# in memory cache and django-axes don't get along.
# https://django-axes.readthedocs.io/en/latest/configuration.html#known-configuration-problems
CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "axes": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"},
    "oidc": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] += (
    "rest_framework.renderers.BrowsableAPIRenderer",
)

warnings.filterwarnings(
    "error",
    r"DateTimeField .* received a naive datetime",
    RuntimeWarning,
    r"django\.db\.models\.fields",
)

if "test" in sys.argv:
    NOTIFICATIONS_DISABLED = True

# Override settings with local settings.
try:  # noqa: SIM105
    from .includes.local import *  # noqa
except ImportError:
    pass

TEST_CALLBACK_AUTH = False

ELASTIC_APM["DEBUG"] = config("DISABLE_APM_IN_DEV", default=True, add_to_docs=False)
