"""
Continuous integration settings module.
"""

import os

os.environ.setdefault("IS_HTTPS", "no")
os.environ.setdefault("SECRET_KEY", "dummy")

from .includes.base import *  # noqa isort:skip

CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    # See: https://github.com/jazzband/django-axes/blob/master/docs/configuration.rst#cache-problems
    "axes": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"},
    "oidc": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}

for logger in LOGGING["loggers"].values():
    logger.update(
        {
            "level": "CRITICAL",
            "handlers": [],
            "propagate": False,
        }
    )
LOGGING["loggers"][""] = {"level": "CRITICAL", "handlers": []}

ENVIRONMENT = "CI"

TEST_CALLBACK_AUTH = False
