.. _api_experimental:

==========================================
Experimental features of Open Notificaties
==========================================

Open Notificaties implements the Notificaties API which adheres to the :ref:`VNG standard <api_index>`.
Moreover it provides extra features which are not included in this standard.
All such features are marked as "experimental" (or "experimenteel") in the OAS.

There are no breaking changes from the VNG standards and these changes are mostly small
additions for the convenience of the clients. Below is the full list of deviations.

Abonnement
==========

New Fields are added:

* ``send_cloudevents`` Whether to send cloudevents to the ``abonnement``.
* ``cloudevent_filters`` A list of cloudevent type substrings to filter what cloudevents will be send to the ``abonnement``.

Kanaal
======

Endpoints
---------

New endpoints are added:

* PUT ``/api/v1/kanaal/{uuid}``
* PATCH ``/api/v1/kanaal/{uuid}``

These endpoints allow updating existing ``Kanaal`` objects.
Only components that publish notifications should create or modify ``Kanaal``.
The updated ``Kanaal`` can then be shared with consumers to subscribe to notifications.

Notificaties
============

New Fields are added:

* ``source`` The identifier of the origin of the notification, a system or organisation.

Cloudevents
===========

The ``cloudevents`` endpoint has been added to the Open Notificaties API and supports POST.

* ``/api/v1/cloudevents``
