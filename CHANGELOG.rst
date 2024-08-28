=======
Changes
=======

1.7.0 (2024-08-26)
------------------

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

**Project maintaince**

* [#159] Added open-api-framework, which includes adding CSRF, CSP and HSTS settings.
* [#107, #163, #165] Refactored Settings module to use generic settings provided by Open API Framework
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
------------------

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
