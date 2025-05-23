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
from pathlib import Path

import structlog
from dotenv import load_dotenv
from self_certifi import load_self_signed_certs as _load_self_signed_certs

_certs_initialized = False


def setup_env():
    # load the environment variables containing the secrets/config
    dotenv_path = Path(__file__).parents[2] / ".env"
    load_dotenv(dotenv_path)

    structlog.contextvars.bind_contextvars(source="app")

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nrc.conf.dev")

    load_self_signed_certs()


def load_self_signed_certs() -> None:
    global _certs_initialized
    if _certs_initialized:
        return

    # create target directory for resulting combined certificate file
    target_dir = tempfile.mkdtemp()
    _load_self_signed_certs(target_dir)
    _certs_initialized = True
