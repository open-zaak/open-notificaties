=======
Changes
=======

1.1.6 (2021-??-??)
==================

.. warning::

   Manual intervention required
   
   k8s the correct pod securityGroupContext needs to be specified and on plain Docker 
   deploys the permissions of the volumes will probably have to be fixed. 


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
