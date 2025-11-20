"""
Bootstrap the environment.

Load the secrets from the .env file and store them in the environment, so
they are available for Django settings initialization.

.. warning::

    do NOT import anything Django related here, as this file needs to be loaded
    before Django is initialized.
"""

import os
import tempfile
import warnings
from pathlib import Path

from django.conf import settings

import structlog
from dotenv import load_dotenv
from maykin_common.otel import setup_otel
from self_certifi import load_self_signed_certs as _load_self_signed_certs

_certs_initialized = False

logger = structlog.stdlib.get_logger(__name__)


def setup_env():
    # load the environment variables containing the secrets/config
    dotenv_path = Path(__file__).parents[2] / ".env"
    load_dotenv(dotenv_path)

    structlog.contextvars.bind_contextvars(source="app")

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nrc.conf.dev")
    if "OTEL_SERVICE_NAME" not in os.environ:
        warnings.warn(
            "No OTEL_SERVICE_NAME environment variable set, using a default. "
            "You should set a (distinct) value for each component (web, worker...)",
            RuntimeWarning,
            stacklevel=2,
        )
        os.environ.setdefault("OTEL_SERVICE_NAME", "opennotificaties")

    setup_otel()

    load_self_signed_certs()

    monkeypatch_requests()


def load_self_signed_certs() -> None:
    global _certs_initialized
    if _certs_initialized:
        return

    # create target directory for resulting combined certificate file
    target_dir = tempfile.mkdtemp()
    _load_self_signed_certs(target_dir)
    _certs_initialized = True


def monkeypatch_requests():
    """
    Add a default timeout for any requests calls.

    """
    try:
        from requests import Session
    except ModuleNotFoundError:
        logger.debug("Attempt to patch requests, but the library is not installed")
        return

    if hasattr(Session, "_original_request"):
        logger.debug(
            "Session is already patched OR has an ``_original_request`` attribute."
        )
        return

    Session._original_request = Session.request

    def new_request(self, *args, **kwargs):
        kwargs.setdefault("timeout", settings.REQUESTS_DEFAULT_TIMEOUT)
        return self._original_request(*args, **kwargs)

    Session.request = new_request
