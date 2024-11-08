.. _installation_configuration_cli:

=====================================
Open Notificaties configuration (CLI)
=====================================

After deploying Open Notificaties, it needs to be configured to be fully functional. The
command line tool ``setup_configuration`` assists with this configuration:

* It uses environment variables for all configuration choices, therefore you can integrate this with your
  infrastructure tooling such as init containers and/or Kubernetes Jobs.
* The command can self-test the configuration to detect problems early on

You can get the full command documentation with:

.. code-block:: bash

    src/manage.py setup_configuration --help

.. warning:: This command is declarative - if configuration is manually changed after
   running the command and you then run the exact same command again, the manual
   changes will be reverted.


Preparation
===========

The command executes the list of pluggable configuration steps, and each step
requires specific environment variables, that should be prepared.
Here is the description of all available configuration steps and the environment variables,
use by each step.

Sites configuration
-------------------

Configure the domain where Open Notificaties is hosted

* ``SITES_CONFIG_ENABLE``: enable Site configuration. Defaults to ``False``.
* ``OPENNOTIFICATIES_DOMAIN``:  a ``[host]:[port]`` or ``[host]`` value. Required.
* ``OPENNOTIFICATIES_ORGANIZATION``: name of Open Notificaties organization. Required.

Authorization configuration
---------------------------

Open Notificaties uses Open Zaak Authorisaties API to check authorizations
of its consumers, therefore Open Notificaties should be able to request Open Zaak.
Make sure that the correct permissions are configured in Open Zaak Autorisaties API.

* ``OPENNOTIFICATIES_DOMAIN``:  a ``[host]:[port]`` or ``[host]`` value. Required.
* ``AUTHORIZATION_CONFIG_ENABLE``: enable Authorization configuration. Defaults
  to ``False``.
* ``AUTORISATIES_API_ROOT``: full URL to the Authorisaties API root, for example
  ``https://open-zaak.gemeente.local/autorisaties/api/v1/``. Required.
* ``NOTIF_OPENZAAK_CLIENT_ID``: a client id, which Open Notificaties uses to request
  Open Zaak, for example, ``open-notificaties``. Required.
* ``NOTIF_OPENZAAK_SECRET``: some random string. Required.

Open Zaak authentication configuration
--------------------------------------

Open Zaak published notifications to the Open Notificaties, therefore it should have access.
Make sure that the correct permissions are configured in Open Zaak Autorisaties API.

* ``OPENZAAK_NOTIF_CONFIG_ENABLE``: enable Open Zaak configuration. Defaults to ``False``.
* ``OPENZAAK_NOTIF_CLIENT_ID``: a client id, which Open Zaak uses to request Open Notificaties,
  for example, ``open-zaak``. Required.
* ``OPENZAAK_NOTIF_SECRET``: some random string. Required.

.. _installation_configuration_cli_retry:

Notification retry configuration
--------------------------------

Open Notifications has a retry mechanism to guarantee notification delivery, this mechanism
is described in :ref:`delivery_guarantees`. The parameters for this behavior can be configured via the
following environment variables.

* ``NOTIFICATION_RETRY_CONFIG_ENABLE``: enable Notification retry configuration. Defaults to ``False``.
* ``NOTIFICATION_DELIVERY_MAX_RETRIES``: the maximum number of retries Celery will do if sending a notification failed.
* ``NOTIFICATION_DELIVERY_RETRY_BACKOFF``: a boolean or a number. If this option is set to
  ``True``, autoretries will be delayed following the rules of exponential backoff. If
  this option is set to a number, it is used as a delay factor.
* ``NOTIFICATION_DELIVERY_RETRY_BACKOFF_MAX``: an integer, specifying number of seconds.
  If ``retry_backoff`` is enabled, this option will set a maximum delay in seconds
  between task autoretries. By default, this option is set to 48 seconds.

These settings can also later be changed via the admin interface, under ``Configuration > Notification component configuration``.

Execution
=========

With the full command invocation, everything is configured at once and immediately
tested. For all the self-tests to succeed, it's important that the configuration in the
Open Zaak is done before calling this command.

.. code-block:: bash

    src/manage.py setup_configuration


Alternatively, you can skip the self-tests by using the ``--no-selftest`` flag.

.. code-block:: bash

    src/manage.py setup_configuration --no-self-test


``setup_configuration`` command checks if the configuration already exists before changing it.
If you want to change some of the values of the existing configuration you can use ``--overwrite`` flag.

.. code-block:: bash

    src/manage.py setup_configuration --overwrite


.. note:: Due to a cache-bug in the underlying framework, you need to restart all
   replicas for part of this change to take effect everywhere.
