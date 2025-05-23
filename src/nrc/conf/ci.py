"""
Continuous integration settings module.
"""

import os

from open_api_framework.conf.utils import mute_logging

os.environ.setdefault("IS_HTTPS", "no")
os.environ.setdefault("SECRET_KEY", "dummy")
os.environ.setdefault("ENVIRONMENT", "CI")

from .includes.base import *  # noqa isort:skip

CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    # See: https://github.com/jazzband/django-axes/blob/master/docs/configuration.rst#cache-problems
    "axes": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"},
    "oidc": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}

mute_logging(LOGGING)

TEST_CALLBACK_AUTH = False
