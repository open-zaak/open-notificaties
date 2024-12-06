.. _installation_configuration_cli:

=====================================
Open Notificaties configuration (CLI)
=====================================

After deploying Open Notificaties, it needs to be configured to be fully functional. The
command line tool ``setup_configuration`` assist with this configuration by loading a
YAML file in which the configuration information is specified.

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

TODO: add generated documentation for ``zgw_consumers.ServiceConfigurationStep``

Client credentials
------------------

TODO: add generated documentation for ``JWTSecretsConfigurationStep``


Autorisaties API configuration
------------------------------

TODO: add generated documentation

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

.. code-block:: bash

    src/manage.py setup_configuration

.. note:: Due to a cache-bug in the underlying framework, you need to restart all
   replicas for part of this change to take effect everywhere.
