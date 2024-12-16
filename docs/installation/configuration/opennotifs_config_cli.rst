.. _installation_configuration_cli:

=====================================
Open Notificaties configuration (CLI)
=====================================

After deploying Open Notificaties, it needs to be configured to be fully functional. The
command line tool ``setup_configuration`` assist with this configuration by loading a
YAML file in which the configuration information is specified.

.. code-block:: bash

    src/manage.py setup_configuration --yaml-file /path/to/your/yaml

You can get the full command documentation with:

.. code-block:: bash

    src/manage.py setup_configuration --help

.. warning:: This command is declarative - if configuration is manually changed after
   running the command and you then run the exact same command again, the manual
   changes will be reverted.

Preparation
===========

The command executes the list of pluggable configuration steps, and each step
requires specific configuration information, that should be prepared.
Here is the description of all available configuration steps and the shape of the data,
used by each step.


Services configuration
----------------------

In order for Open Notificaties to make requests to external services (such as the Autorisaties API),
``Services`` must be configured. To enable this step, set ``zgw_consumers_config_enable`` to ``true`` in your
configuration file and specify a list of ``Services``, for example:

.. code-block:: yaml

    zgw_consumers_config_enable: true
    zgw_consumers:
    services:
      # all possible configurable fields
      - identifier: objecten-test
        label: Objecten API test
        api_root: http://objecten.local/api/v1/
        api_connection_check_path: objects
        api_type: orc
        auth_type: api_key
        header_key: Authorization
        header_value: Token foo
        client_id: client
        secret: super-secret
        nlx: http://some-outway-adress.local:8080/
        user_id: open-formulieren
        user_representation: Open Formulieren
        timeout: 5
      # minimum required fields
      - identifier: objecttypen-test
        label: Objecttypen API test
        api_root: http://objecttypen.local/api/v1/
        api_type: orc
        auth_type: api_key

Client credentials
------------------

TODO: add generated documentation for ``JWTSecretsConfigurationStep``


Autorisaties API configuration
------------------------------

Open Notificaties uses Autorisaties API to check permissions of the clients that
make requests to Open Notificaties.

This step configures Open Notificaties to use the specified Autorisaties API (see also :ref:`installation_configuration`). It is
dependent on the `Services configuration`_ step to load a ``Service`` for this Autorisaties API,
which is referred to in this step by ``authorizations_api_service_identifier``.
To enable this step, set ``autorisaties_api_config_enable`` to ``true`` in your
configuration file and specify which ``Service`` to use as the Autorisaties API, for example:

.. code-block:: yaml

    autorisaties_api_config_enable: True
    autorisaties_api:
      authorizations_api_service_identifier: autorisaties-api

.. _installation_configuration_cli_retry:

Notificaties configuration
--------------------------

TODO: add generated documentation


Sites configuration
-------------------

TODO: add generated documentation

Execution
=========

Open Notificaties configuration
-------------------------------

With the full command invocation, all defined configuration steps are applied. Each step is idempotent,
so it's safe to run the command multiple times. The steps will overwrite any manual changes made in
the admin if you run the command after making these changes.

.. note:: Due to a cache-bug in the underlying framework, you need to restart all
   replicas for part of this change to take effect everywhere.
