.. _api_experimental:

==========================================
Experimental features of Open Notificaties
==========================================

Open Notificaties, which adhere to :ref:`VNG standards <api_index>`.
Moreover it provides extra features which are not included in the standards.
All such features are marked as "experimental" (or "experimenteel") in the OAS.
 
There are no breaking changes from the VNG standards and these changes are mostly small
additions for the convenience of the clients. Below is the full list of deviations.

Abonnement
==========

No deviation from the standard

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

No deviation from the standard
