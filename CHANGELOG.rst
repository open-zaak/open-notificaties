=======
Changes
=======

1.15.0 (2026-02-06)
===================


**New features**

* [:open-notificaties:`351`] Add support for **OAuth2** authentication when sending notifications and cloud events to subscribers.
  New fields added to the **Abonnement** model to enable sending events to subscribed webhooks using OAuth2.
* [:open-notificaties:`353`] Support mutual **TLS** for sending notifications and cloud events to subscriptions.
* [:zgw-consumers:`128`] Make necessary **OAuth2** attributes configurable via setup_configuration

.. note::

    The **configuration step** for subscriptions now also supports these new fields.
    For detailed configuration, see :ref:`Abonnement Configuration Step <ref_step_nrc.setup_configuration.abonnementen.AbonnementConfigurationStep>`.

* [:open-notificaties:`356`] Extend cloud event filtering for Abonnement with additional attribute filters.

    * Allow configuring cloud event filters via setup config, see :ref:`Abonnement Configuration Step <ref_step_nrc.setup_configuration.abonnementen.AbonnementConfigurationStep>`.
    * Improve performance by adding missing ``select_related`` and ``prefetch_related``.

**Bugfixes**

* Fix 500 error when not specifying Abonnement.filters in API calls to ``/abonnementen``

**Project maintenance**

* Avoid using ``event`` key in uwsgi logs.
* Upgrade python dependencies

    * ``commonground-api-common`` to 2.10.7
    * ``notifications-api-common`` to 0.10.1
    * ``open-api-framework`` to 0.13.4
    * ``zgw-consumers`` to 1.1.2
    * ``asgiref`` to 3.11.0
    * ``cbor2`` to 5.8.0
    * ``django`` to 5.2.11
    * ``urllib3`` to 2.6.3

**Documentation**

* [:open-zaak:`2233`] Add docs for configuring cloud events for Mijn Overheid.
  See :ref:`cloud_events_configuration_mijn_overheid` for more informations.

1.14.0 (2025-12-02)
===================

.. warning::

    Changes to format of ``setup_configuration`` data for OpenID connect

    In this release, ``mozilla-django-oidc-db`` has been updated to version 1.1.0, which requires the new data format.
    The old format is deprecated and will be removed in future releases.

    The new configuration must be used, as it splits the previous solo model configuration into ``OIDCProvider`` and ``OIDCClient``
    configurations, making it easier to re-use identity provider settings across multiple client IDs.

    Additionally, any configuration using ``django-setup-configuration`` must be updated to reflect these changes,
    as it is now split into two distinct sections: one for ``providers`` and one for ``clients``.
    This separation also exists in the admin interface, so both sections can be configured directly through the user interface.
    For example:

    .. code-block:: yaml

        providers:
          - identifier: example-provider
            # other provider settings

        clients:
          - identifier: admin-oidc
            oidc_provider_identifier: example-provider
            # other client settings

    For detailed configuration, see :ref:`Admin OIDC Configuration Step  <ref_step_mozilla_django_oidc_db.setup_configuration.steps.AdminOIDCConfigurationStep>`.
    Make sure to check which fields are marked as ``DEPRECATED`` and replace them with the fields that are mentioned as replacements.


**New features**

    * [:open-api-framework:`152`] Add Open Telemetry support

    .. note::
        The OpenTelemetry SDK is **enabled by default**.
        If you do not have an endpoint to send system telemetry to, update your deployment to **disable it** by setting the environment variable:

        .. code-block:: bash

            OTEL_SDK_DISABLED=true

        If this is not done, warnings will be emitted to the container logs. The application will continue to function normally.
        All available metrics and details can be found in the :ref:`Observability documentation <installation_observability_index>`.

**Experimental features**

    * [:open-notificaties:`333`] Add support for cloudevents

        * Add cloudevent endpoint to pass cloudevents to subscriptions directly.
        * Add ``send_cloudevents`` field to ``Abonnement`` to be able to receive cloudevents on callback url and to transform incomming notifications to cloudevents.
        * Add optional field ``source`` to ``Notificatie`` needed to transform notifcations to cloudevents.
        * Add ``CloudeventFilterGroup`` to subscribe on substrings of cloudevent types.

**Project maintenance**

    * Upgrade python dependencies:

        * ``Django`` to 5.2.8
        * ``pip`` to 25.4 in dev dependencies
        * ``notifications-api-common`` to 0.10.0
        * ``open-api-framework`` to 0.13.2
        * [:open-api-framework:`85`] ``mozilla-django-oidc-db`` to 1.1.0
        * [:open-api-framework:`85`] ``django-setup-configuration`` to 0.11.0
        * [:commonground-api-common:`134`] commonground-api-common to 2.10.5
        * [:open-api-framework:`163`] ``maykin-common`` to 0.11.0

    * [:open-api-framework:`191`] Upgrade ``NodeJS`` to 24
    * [:open-api-framework:`163`] Integrate ``maykin-common``

        * New template for the landing page
        * Remove duplicate classes and functions that are already exists in the library

    * [:open-api-workflows:`31`] Update CI workflows
    * [:open-api-workflows:`30`] Use API Design Rules linter for api spec validation
    * [:commonground-api-common:`134`] Ensure API errors are sent to Sentry

1.13.0 (2025-10-06)
===================

.. warning::

     The default number of ``UWSGI_THREADS`` and ``UWSGI_PROCESSES`` has been increased from 2 to 4.

**New features**

* [:open-notificaties:`328`] Changes to logging of handled and unhandled exceptions (see :ref:`manual_logging_exceptions`)

  * Log events for handled API exceptions (e.g. HTTP 400) now include ``invalid_params``
  * Log events for unhandled API exceptions (e.g. HTTP 500) now include the traceback via ``exception``

* [:open-api-framework:`184`] ``setup_configuration`` now supports pulling values from
  environment variables in YAML configuration by using ``value_from`` (see `setup_configuration documentation`_ for more information)

.. TODO should be reference to readthedocs
.. _setup_configuration documentation: https://github.com/maykinmedia/django-setup-configuration/blob/main/README.rst#environment-variable-substitution

**Project maintenance**

* Upgrade python dependencies:

  * ``Django`` to 5.2.7
  * ``pip`` to 25.2 in dev dependencies
  * ``commonground-api-common`` to 2.10.1
  * ``django-csp`` to 4.0
  * ``open-api-framework`` to 0.13.1
  * ``structlog`` to 25.4.0
  * ``django-setup-configuration`` to 0.9.0

* [:open-notificaties:`328`] Use logging settings from ``open-api-framework``
* [:open-api-framework:`85`] Increase uwsgi worker numbers


1.12.0 (2025-09-02)
===================

.. warning::

  This version of Open Notificaties increases the default values of the notification retry
  parameters, leading to tasks that are scheduled further in the future. In order for this
  to work correctly, it is required to increase the ``consumer_timeout`` in RabbitMQ,
  see :ref:`delivery_guarantees_rabbitmq_config` for more information.

**New features**

* [:open-notificaties:`290`] Add configurable base factor exponential backoff for retry mechanism (see :ref:`delivery_guarantees`).
  This parameter is also configurable with ``setup_configuration`` via ``notification_delivery_base_factor`` (see :ref:`installation_env_config` > Configuration for Notificaties API).
* [:open-notificaties:`290`] Changed default values of retry mechanism parameters to make sure the retries cover a period of approximately 24 hours:

  * **Notification delivery max retries**: 7
  * **Notification delivery retry backoff**: 25
  * **Notification delivery retry backoff max**: 52000 seconds
  * **Notification delivery base factor**: 4

**Project maintenance**

* Use db connection pooling settings from OAF
* [:open-api-framework:`179`] Monkeypatch requests to set default timeout
* Upgrade python dependencies:

  * [:open-api-framework:`128`] ``celery`` to 5.5.3 to fix connection issues with Redis
  * ``notifications-api-common`` to 0.8.0
  * ``django-privates`` to 3.1.1
  * ``open-api-framework`` to 0.12.0
  * ``bleach`` to 6.2.0
  * ``commonground-api-common`` to 2.9.0
  * ``django-cors-headers`` to 4.7.0
  * ``django-markup`` to 1.10
  * ``django-redis`` to 6.0.0
  * ``redis`` to 6.4.0
  * ``djangorestframework-gis`` to 1.2.0
  * ``humanize`` to 4.12.3
  * ``zgw-consumers`` to 1.0.0
  * ``uwsgi`` to 2.0.30
  * ``pytz`` to 2025.2
  * ``billiard`` to 4.2.1

* Remove unused ``coreapi`` dependency

**Documentation**

* Fix incorrect default in docs for ``DB_CONN_MAX_AGE``
* [:open-api-framework:`118`] Remove deployment tooling/documentation
* [:open-api-framework:`148`] Add prerequisites docs page (including supported PostgreSQL, Redis and RabbitMQ versions)
* [:open-api-framework:`159`] Add UML diagrams for data models (see :ref:`uml_diagrams`)

1.11.0 (2025-07-04)
===================

**New features**

* [:open-zaak:`635`] Add ``TIME_LEEWAY`` environment varialbe for JWT & field validation (see :ref:`installation_env_config`)

* [:open-notificaties:`283`] Add db connection pooling environment variables (see :ref:`installation_env_config`)

  * DB_POOL_ENABLED
  * DB_POOL_MIN_SIZE
  * DB_POOL_MAX_SIZE
  * DB_POOL_TIMEOUT
  * DB_POOL_MAX_WAITING
  * DB_POOL_MAX_LIFETIME
  * DB_POOL_MAX_IDLE
  * DB_POOL_RECONNECT_TIMEOUT
  * DB_POOL_NUM_WORKERS

* [maykinmedia/objects-api#607] Add DB_CONN_MAX_AGE environment variable (see :ref:`installation_env_config`)

.. warning::

    **Experimental:** — connection pooling is *not yet recommended for production use*.
    It may not behave as expected when running uWSGI with multiple processes or threads.
    Use this feature cautiously and test thoroughly before deployment.
    See the :ref:`documentation <database_connections>` for details.

**Project maintenance**

* Upgrade dependencies

  * Django to 5.2.3
  * notifications-api-common to 0.7.3
  * commonground-api-common to 2.6.7
  * open-api-framework to 0.11.0
  * requests to 2.32.4
  * urllib3 to 2.5.0
  * vcrpy to 7.0.0

* [:open-notificaties:`297`] Fix duplicate / unstructured celery logs
* [:open-api-framework:`151`] Move ruff config to pyproject.toml
* [:open-api-framework:`139`] Integrate django-upgrade-check

**Bugfixes**

* [:open-api-framework:`149`] Fix dark/light theme toggle

1.10.0 (2025-06-03)
===================

.. warning::

    This release upgrades Django to version 5.2.1, which requires PostgreSQL version 14 or higher.
    Attempting to deploy with PostgreSQL <14 will cause errors during deployment.


**New features**

.. note::

  The logging format has been changed from unstructured to structured with `structlog <https://www.structlog.org/en/stable/>`_.
  For more information on the available log events and their context, see :ref:`manual_logging`.

* [:open-notificaties:`277`] Emit logs when receiving/sending notifications
* [:open-notificaties:`277`] Log the task autoretry attempt count for failed notifications

**Bugfixes/QOL**

* [:open-notificaties:`258`] Make ``notifications_api_service_identifier`` optional for ``setup_configuration``
  (see :ref:`Configuration for Notificaties API <ref_step_nrc.setup_configuration.steps.NotificationConfigurationStep>`)
* Do not use ``save_outgoing_requests`` log handler if ``LOG_REQUESTS`` is set to false

**Project maintenance**

* Upgraded dependencies

  * [:open-api-framework:`140`] python to 3.12
  * [:open-notificaties:`273`] Django to 5.2.1
  * setuptools to 78.1.1 to fix security issues
  * tornado to 6.5 to fix security issues
  * open-api-framework to 0.10.1
  * commonground-api-common to 2.6.4

* [:open-api-framework:`132`] Remove pytest and check_sphinx.py, replace with simpler commands
* [:open-notificaties:`279`] Make local docker-compose setup easier to work with
* [:open-notificaties:`279`] Add docker compose setup for observability (Grafana/Loki/Promtail)
* [:open-api-workflows:`24`] Replace OAS workflows with single workflow
* [:open-api-framework:`133`] Replace black, isort and flake8 with ruff and update code-quality workflow

1.9.0 (2025-05-15)
==================

**New features**

* [:open-notificaties:`240`] Add ``CELERY_RESULT_EXPIRES`` (see :ref:`installation_env_config`) environment variable to configure how long
  results for tasks will be stored in Redis. This duration can be lowered to avoid
  high memory consumption by Redis.

**Project maintenance**

* Upgrade packages

  * commonground-api-common to version 2.6.2
  * development dependency h11 to version 0.16.0 to fix security issue

* [:open-notificaties:`239`] Add overview of experimental API features (deviations from the Notificaties API standard)
  to the documentation. See :ref:`api_experimental` for more information.

1.8.2 (2025-04-03)
==================

**Project maintenance**

* [:open-api-framework:`59`] Add ``SITE_DOMAIN`` environment variable which will replace ``sites`` configuration in version 2.0
* [:open-api-framework:`115`] Fix OAS check github action
* [:open-api-framework:`116`] Fix codecov publish
* [:open-api-framework:`117`] Upgrade version of CI dependencies

  * Confirm support for Postgres 17
  * Confirm support for RabbitMQ 4.0
  * Development tools: black to 25.1.0, flake8 to 7.1.2 and isort to 6.0.1
  * Upgrade GHA versions

* Upgrade dependencies

  * Upgrade cryptography to 44.0.2
  * Upgrade jinja2 to 3.1.6
  * Upgrade kombu to 5.5.2
  * Upgrade django to 4.2.20
  * Upgrade django-setup-configuration to 0.7.2
  * Upgrade open-api-framework to 0.9.6
  * Upgrade notifications-api-common to 0.7.2
  * Upgrade commonground-api-common to 2.5.5

1.8.1 (2025-03-04)
==================

**Bugfixes and QOL**

* [:open-notificaties:`234`] Fix search functionality on Notificatie response admin page
* [:open-notificaties:`248`] Fix broken tooltip helptexts for datetime fields in admin
* [:open-notificaties:`251`] Hide ``Abonnement.client_id`` from admin, because this field is currently unused
* [:open-notificaties:`170`] Add unique constraint for ``(Filter.filter_group, Filter.key)`` fields.

.. warning::

    The unique constraint is added for ``(Filter.filter_group, Filter.key)``.
    If "datamodel.0017" migration is failing, remove duplicate entries manually from
    the ``Filter`` model and try to run it again.

**Documentation**

* [:open-notificaties:`210`] Add documentation for setup-configuration steps (see :ref:`installation_configuration_cli`)

**Project maintenance**

* Upgrading dependencies:

  * Upgrade node version from 16 to 20
  * Upgrade npm packages to fix vulnerabilities
  * Upgrade deployment deps to fix vulnerabilities
  * Upgrade python packages to fix vulnerabilities
  * Upgrade open-api-framework to 0.9.3
  * Upgrade commonground-api-common to 2.5.0
  * Upgrade notifications-api-common to 0.6.0
  * Upgrade zgw-consumers to 0.37.0
  * Upgrade mozilla-django-oidc-db to 0.22.0
  * Upgrade django-setup-configuration to 0.7.1
* Compile translations in Docker build
* Add bump-my-version to dev dependencies
* [:open-api-framework:`100`] Add quick-start workflow to test docker-compose.yml
* [:open-api-framework:`44`] add workflow to CI to auto-update open-api-framework
* [:maykin-charts:`165`] Remove unused celery worker command line args
* [:open-api-framework:`81`] Switch from pip-compile to UV

1.8.0 (2025-01-13)
==================

**New features**

* [#108] Admin action to check Abonnement callback status
* [#180] Provide an admin overview for notificatie responses
* [#207] Add experimental PUT and PATCH for Kanaal
* [#199] Add Admin OIDC Configuration step from django-setup-configuration
* [#204] Add SitesConfiguration step from django-setup-configuration
* [#200] Autorisaties-API configuration via django-setup-configuration
* [#202] Configuration Kanalen via django-setup-configuration
* [#202] Configuration Abonnementen via django-setup-configuration
* [#203] Configuration Notification settings via django-setup-configuration
* [maykinmedia/open-api-framework#46] Upgrade open-api-framework to 0.9.1

**Bugfixes and QOL**

* [maykinmedia/open-api-framework#66] Update zgw consumers to 0.36.0
* [#199] Upgrade mozilla-django-oidc-db to 0.21.1
* [#203] Upgrade notifications-api-common to 0.4.0
* [#204] Upgrade django-setup-configuration to 0.5.0
* [#200] Fix ``CELERY_LOGLEVEL`` not working
* [#200] Upgrade commonground-api-common to 2.2.0

.. warning::

    Configuring external services is now done through the `Service` model. This
    replaces the `APICredential` model in the admin interface. A data migration
    was added to move to the `Service` model. It is advised to verify the `Service`
    instances in the admin to check that the data migration was ran as expected.

.. warning::

    ``LOG_STDOUT`` configuration variable now defaults to ``True`` instead of ``False``

.. warning::

    The previous setup configurations are no longer supported.
    Make sure to replace the old configurations with the new ones. See :ref:`installation_configuration_cli`
    for the new configuration file format.

**Project maintenance**

* [maykinmedia/objects-api#463] Add trivy image scan
* [maykinmedia/open-api-framework#92] Fix docker latest tag publish
* [maykinmedia/open-api-framework#13] Consistent CI configuration across the different projects.

**Documentation**

* [#200] Update docs for setup configuration changes
* [maykinmedia/objects-api#403] Update delivery guarantee documentation

1.7.1 (2024-10-04)
==================

**Bugfixes and QOL**

* [#190] change SameSite session cookie to lax to fix OIDC login not working
* [#190] fix API schema not showing caused by CSP errors
* [#185] remove the need to manually configure Site.domain for the 2FA app title
* [#188] change all setup configuration to disabled by default

**Documentation**

* [#188] update config env var descriptions
* [#190, #191] remove broken links from documentation

1.7.0 (2024-09-02)
==================

**New features**

* [#169] Made user emails unique to prevent two users logging in with the same email, causing an error
* [#151] Added 2FA to the Admin
* [#157] Optimized deleting abonnement with a lot of notifications in the Admin

.. warning::

    User email addresses will now be unique on a database level. The database migration will fail if there are already
    two or more users with the same email address. You must ensure this is not the case before upgrading.

.. warning::

    Two-factor authentication is enabled by default. The ``DISABLE_2FA`` environment variable
    can be used to disable it if needed.


**Bugfixes**

* [#168] Fixed CSS style for help-text icon in the Admin
* [#166] Fixed ReadTheDocs build
* [#171] Fixed filtering subscribers for ``objecten`` channel and ``object_type`` filter

**Documentation**

* [#142] Updated and improved documentation to configure ON and its consumers
* [#174] Updated the documentation of environment variables using open-api-framework

**Project maintenance**

* [#159] Added open-api-framework, which includes adding CSRF, CSP and HSTS settings.
* [#107, #163, #165] Refactored Settings module to use generic settings provided by Open API Framework
* [#163] Allow providing the ``ENVIRONMENT`` via envvar to Sentry
* [#164] Updated Python to 3.11
* [#176, #179] Bumped python dependencies due to security issues: ampq, django, celery, certifi, maykin-2fa,
  mozilla-django-oidc-db, sentry-sdk, uwsgi and others
* [#172] Added OAS checks to CI
* [#177] Added celery healthcheck, the example how to use it can be found in ``docker-compose.yml``

.. warning::

    The default value for ``ELASTIC_APM_SERVICE_NAME`` changed from ``Open Notificaties - <ENVIRONMENT>`` to ``nrc - <ENVIRONMENT>``.
    The default values for ``DB_NAME``, ``DB_USER``, ``DB_PASSWORD`` changed from ``opennotificaties`` to ``nrc``.
    The default value for ``LOG_OUTGOING_REQUESTS_DB_SAVE`` changed from ``False`` to ``True``.

.. warning::

    SECURE_HSTS_SECONDS has been added with a default of 31536000 seconds, ensure that
    before upgrading to this version of open-api-framework, your entire application is served
    over HTTPS, otherwise this setting can break parts of your application (see https://docs.djangoproject.com/en/4.2/ref/middleware/#http-strict-transport-security)

1.6.0 (2024-05-28)
==================

**New features**

* [#135] Added ``createinitialsuperuser`` management command to create admin superuser
* [#87] Supported configuration of the API with a management command ``setup_configuration`` and environment variables
* [open-zaak/open-zaak#1203] Added configuration of retry variables with admin UI and with
  ``setup_configuration`` management command
* [open-zaak/open-zaak#1626] Displayed generated JWT in the admin

**Bugfixes**

* [#119] Upgraded commonground-api-common, which fixed the configuration view
* [#80, #153] Fixed scope view and removed duplicated scopes

**Project maintenance**

* [#124] Upgraded Django to 4.2 and bumped dependencies: django-redis, django-cors-headers,
  django-axes, django-admin-index, django-relative-delta
* [#130] Removed ADFS
* [#133] Added volume configuration to docker-compose as an example
* [#137] Updated test certificates
* [#139] Replaced ``drf-yasg`` with ``drf-spectacular``
* [open-zaak/open-zaak#1638] Converted ``env_config.md`` file to .rst
* [open-zaak/open-zaak#1629] Added missing environment variables

.. warning::

   Manual intervention required for ADFS/AAD users.

   In Open Notificaties 1.4.x we replaced the ADFS/Azure AD integration with the generic OIDC
   integration. If you are upgrading from an older version, you must first upgrade to
   the 1.4.x release series before upgrading to 1.6, and follow the manual intervention
   steps in the 1.4 release notes.

   After upgrading to 1.6, you can clean up the ADFS database entries by executing the
   ``bin/uninstall_adfs.sh`` script on your infrastructure.

    .. tabs::

     .. group-tab:: single-server

       .. code-block:: bash

           $ docker exec opennotificaties-0 /app/bin/uninstall_adfs.sh

           BEGIN
           DROP TABLE
           DELETE 3
           COMMIT


     .. group-tab:: Kubernetes

       .. code-block:: bash

           $ kubectl get pods
           NAME                                READY   STATUS    RESTARTS   AGE
           cache-79455b996-jxk9r               1/1     Running   0          2d9h
           opennotificaties-7b696c8fd5-hchbq   1/1     Running   0          2d9h
           opennotificaties-7b696c8fd5-kz2pb   1/1     Running   0          2d9h

           $ kubectl exec opennotificaties-7b696c8fd5-hchbq -- /app/bin/uninstall_adfs.sh

           BEGIN
           DROP TABLE
           DELETE 3
           COMMIT


1.5.2 (2024-02-07)
==================

**Project maintenance**

* [#127] Upgraded mozilla-django-oidc-db to 0.14.1 and mozilla-django-oidc to 4.0.0
* [#129] Bumped django to 3.2.24, jinja2 to 3.1.3 and cryptography to 41.0.7


1.5.1 (2023-12-07)
==================

Open Notificaties 1.5.1 is a patch release

**Bugfixes**

* [#120] Added back netcat to the Docker image to be abble to connect to RabbitMQ


1.5.0 (2023-11-30)
==================

Open Notificaties 1.5.0 is a release focused on security and update of dependencies

**New features**

* [#82] Allowed non-unique callback urls for subscriptions
* [#100] Cleaned old notifications with the periodic task
* [#106] Added links to Open Notificaties documentation and Github to the landing page

**Bugfixes**

* [#92] Fixed handling failed notifications with big error message

**Project maintenance**

* [#110] Bumped dependencies with latest (security) patches
* [#89] Bumped mozilla-django-oidc-db to 0.12.0
* [#77, #86] Replaced vng-api-common with commonground-api-common and notifications-api-common
* [#94] Added django-log-outgoing-requests
* [#98] Added Elastic APM support
* [#84] Cleaned up urls in unit tests
* [open-zaak/open-zaak#1502, open-zaak/open-zaak#1518] Added Trivy into the CI as an docker image scaner
* [open-zaak/open-zaak#1512] Moved the project from Python 3.9 to Python 3.10
* [open-zaak/open-zaak#1512] Removed Bootstrap and jQuery from the web interface
* [open-zaak/open-zaak#1512] Switched to Debian 12 as a base for the docker image

** Documentation**

* [#91] Updated links to ZGW API Standards

.. warning::

   Change in deployment is required. `/media/` volume should be configured to share OAS files.

   Explanation:

   The new version of ``zgw_consumers`` library adds ``oas_file`` filed to ``Service`` model.
   This field saves OAS file into ``MEDIA_ROOT`` folder.
   The deployment now should have a volume for it.
   Please look at the example in ``docker-compose.yml``


1.4.3 (2022-07-15)
==================

Fixed a number of bugs introduced in the 1.4.x series

* Accept 20x status codes from subscriber callbacks instead of only HTTP 204
* Bumped to vng-api-common 1.7.8 for future feature development
* [open-zaak/open-zaak#1207] Bumped to Django security release
* [#78] Added missing bleach dependency

1.4.2 (2022-07-01)
==================

Fixed a crash when using the OIDC integration.

Thanks @damm89 for reporting this and figuring out the cause!

1.4.1 (2022-06-24)
==================

Bugfix release following 1.4.0

* Fixed missing migration file for conversion from ADFS library to OpenID Connect library
* Fixed the CI build not producing ``latest`` image tags correctly

1.4.0 (2022-05-03)
==================

**New features**

* Implemented automatic delivery retry mechanism on failure (#1132)
* You can now manually (re)-send notifications from the admin interface (#1135)
* Improved admin interface for notifications (#1133)

**Documentation**

* document Open Notificaties message delivery guarantees (#1151)
* described subscription filters in docs (#1134)

**Project maintenance**

* Replace ADFS library with generic OpenID Connect library - please see the notes below! (#1139)
* Upgraded Python version from 3.7 to 3.9
* Upgraded to Django 3.2.13 (#1136)

.. warning::

   Manual intervention required for ADFS/AAD users.

   Open Notificaties replaces the ADFS/Azure AD integration with the generic OIDC integration.
   On update, Open Notificaties will attempt to automatically migrate your ADFS configuration,
   but this may fail for a number of reasons.

   We advise you to:

   * back up/write down the ADFS configuration BEFORE updating
   * verify the OIDC configuration after updating and correct if needed

   Additionally, on the ADFS/Azure AD side of things, you must update the Redirect URIs:
   ``https://open-notificaties.gemeente.nl/adfs/callback`` becomes
   ``https://open-notificaties.gemeente.nl/oidc/callback``.

   In release 1.6.0 you will be able to finalize the removal by dropping the relevant
   tables.

1.3.0 (2022-03-28)
==================

**New features**

* Upgraded to Django 3.2 LTS version (#1124)
* Confirmed support for PostgreSQL 13 and 14

**Project maintenance**

* Upgraded a number of dependencies to be compatible with Django 3.2 (#1124)

.. warning::

   Manual intervention required!

   **Admin panel brute-force protection**

   Due to the ugprade of a number of dependencies, there is a new environment variable
   ``NUM_PROXIES`` which defaults to ``1`` which covers a typical scenario of deploying
   Open Notificaties behind a single (nginx) reverse proxy. On Kubernetes this is
   typically the case when using an ingress. Other deployment layouts/network topologies
   may require tweaks if there are additional load balancers/reverse proxies in play.

   Failing to specify the correct number may result in:

   * login failures/brute-force attempts locking out your entire organization because one
     of the reverse proxies is now IP-banned - this happens if the number is too low.
   * brute-force protection may not be operational because the brute-forcer can spoof
     their IP address, this happens if the number is too high.

1.2.3 (2021-12-17)
==================

Fixed a container image bug

MIME-types of static assets (CSS, JS, SVG...) were not properly returned because of
the container base image not having the ``/etc/mime.types`` file.

1.2.2 (2021-12-07)
==================

Fixed a bug allowing for empty kenmerk values in notifications.

1.2.1 (2021-09-20)
==================

Open Notificaties 1.2.1 fixes a resource leak. See the below info box for more details.

.. note::

  Notifications are delivered to subscriptions via asynchronous background workers.
  These background tasks were incorrectly storing the execution metadata and result in
  the backend without consuming/ pruning them from  the result store. The symptoms
  should have been fixed with the 1.2.0 release where the default backend is switched
  to Redis instead of RabbitMQ (which normally does evict keys after a certain timeout)
  - but this release fixes the root cause. Result and metadata are now no longer stored.

1.2.0 (2021-09-15)
==================

**Fixes**

* Fixed the webserver and background worker processes not having PID 1
* Containers now run as un-privileged user rather than the root user (open-zaak/open-zaak#869)
* Added Celery Flower to the container images for background worker task monitoring

**New features**

* Added support for generic OpenID Connect admin authentication (open-zaak/open-zaak#1034)

1.1.5 (2021-04-15)
==================

Bugfix release

* Bumped ADFS libraries to support current state of Azure AD
* Fixed issue with self-signed certificates loading

1.1.4 (2021-03-25)
==================

Quality of life release

* Updated to pip-tools 6 internally for dependency management
* Bumped Django and Jinja2 dependencies to get their respective bug- and security fixes
* Added support for self-signed (root) certificates, see the documentation on readthedocs
  for more information.
* Clarified version numbers display in footer

1.1.3 (2021-03-17)
==================

Bugfix release fixing some deployment issues

* Fixed broken ``STATIC_URL`` and ``MEDIA_URL`` settings derived from ``SUBPATH``. This
  should fix CSS/Javascript assets not loading in
* Removed single-server documentation duplication (which was outdated too)
* Removed ``raven test`` command from documentation, it was removed.
* Made CORS set-up opt-in

1.1.2 (2020-12-17)
==================

Quality of life release, no functional changes.

* Updated deployment tooling to version 0.10.0. This adds support for CentOS/RHEL 7 and 8.
* Migrated CI from Travis CI to Github Actions
* Made PostgreSQL 10, 11 and 12 support explicit through build matrix

1.1.1 (2020-11-09)
==================

Small quality of life release.

* Updated documentation links in API Schema documentation
* Added missing Redis service to ``docker-compose.yml``
* Fixed ``docker-compose.yml`` (Postgres config, session cache...)
* Fixed version var in deploy config
* Fixed settings/config for hosting on a subpath
* Added management command for initial Open Notificaties setup (``setup_configuration``)
* Fixed broken links in docs
* Bumped dev-tools isort, black and pip-tools to latest versions
* Fixed tests by mocking HTTP calls that weren't mocked yet
* Fixed handling HTTP 401 responses on callback auth validation. Now both 403 and 401
  are valid responses.

1.1.0 (2020-03-16)
==================

Feature and small improvements release.

.. note:: The API remains unchanged.

* Removed unnecessary sections in documentation
* Updated deployment examples
* Tweak deployment to not conflict (or at least less likely :-) ) with Open Zaak install
  Open Zaak and Open Notificaties on the same machine are definitely supported
* Added support for ADFS Single Sign On (disabled by default)
* Added documentation build to CI

1.0.0 final (2020-02-07)
========================

🎉 First stable release of Open Notificaties.

Features:

* Notificaties API implementation
* Tested with Open Zaak integration
* Admin interface to view data created via the APIs
* Scalable notification delivery workers
* `NLX`_ ready (can be used with NLX)
* Documentation on https://open-notificaties.readthedocs.io/
* Deployable on Kubernetes, single server and as VMware appliance
* Automated test suite
* Automated deployment

.. _NLX: https://nlx.io/
