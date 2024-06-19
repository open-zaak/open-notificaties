"""
Staging environment settings module.

This *should* be nearly identical to production.
"""

import os

os.environ.setdefault("ENVIRONMENT", "staging")
os.environ.setdefault("DISABLE_2FA", "no")

from .production import *  # noqa
