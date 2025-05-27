.. _manual_logging:

Logging
=======

Format
------

Open Notificaties emits structured logs (using `structlog <https://www.structlog.org/en/stable/>`_).
A log line can be formatted like this:

.. code-block:: json

    {
        "event":"notification_received",
        "channel_name":"zaken",
        "resource":"zaak",
        "user_id":null,
        "resource_url":"http://openzaak.local/zaken/api/v1/zaken/1234",
        "additional_attributes":{
            "bronorganisatie":"000000000",
            "zaaktype":"http://openzaak.local/catalogi/api/v1/zaaktypen/1234",
            "zaaktype.catalogus":"http://openzaak.local/catalogi/api/v1/catalogussen/1234",
            "vertrouwelijkheidaanduiding":"openbaar"
        },
        "action":"create",
        "request_id":"5aa21b5c-d113-4dfa-a3c1-164ce7f325c8",
        "main_object_url":"http://openzaak.local/zaken/api/v1/zaken/1234",
        "creation_date":"2025-05-23T12:18:25.162276Z",
        "timestamp":"2025-05-23T12:18:25.162276Z",
        "logger":"nrc.api.serializers",
        "level":"info"
    }

Each log line will contain an ``event`` type, a ``timestamp`` and a ``level``.
Dependent on your configured ``LOG_LEVEL`` (see :ref:`installation_env_config` for more information),
only log lines with of that level or higher will be emitted.

Open Notificaties log events
----------------------------

Below is the list of logging ``event`` types that Open Notificaties can emit. In addition to the mentioned
context variables, these events will also have the **request bound metadata** described in the :ref:`django-structlog documentation <request_events>`.

API
~~~

* ``notification_received``: a notification was received via the ``/notificaties`` endpoint. Additional context:

    * ``channel_name``
    * ``resource``
    * ``resource_url``
    * ``main_object_url``
    * ``creation_date``
    * ``action``
    * ``additional_attributes``

* ``notification_successful``: a notification was successfully forwarded to a subscribed callback URL. Additional context:

    * ``channel_name``
    * ``resource``
    * ``resource_url``
    * ``main_object_url``
    * ``creation_date``
    * ``action``
    * ``additional_attributes``
    * ``subscription_pk``
    * ``notification_id``
    * ``subscription_callback``
    * ``notification_attempt_count`` the amount of times this task has been started for this notification
    * ``task_attempt_count``: the number of times this specific task has been attempted

* ``notification_failed``: a non success status code was returned while sending the notification to a subscribed callback URL. Additional context:

    * ``channel_name``
    * ``resource``
    * ``resource_url``
    * ``main_object_url``
    * ``creation_date``
    * ``action``
    * ``additional_attributes``
    * ``subscription_pk``
    * ``notification_id``
    * ``subscription_callback``
    * ``http_status_code``
    * ``notification_attempt_count`` the amount of times this task has been started for this notification
    * ``task_attempt_count``: the number of times this specific task has been attempted

* ``notification_error``: an error occurred while trying to send the notification to a subscribed callback URL. Additional context:

    * ``channel_name``
    * ``resource``
    * ``resource_url``
    * ``main_object_url``
    * ``creation_date``
    * ``action``
    * ``additional_attributes``
    * ``subscription_pk``
    * ``notification_id``
    * ``subscription_callback``
    * ``exc_info``
    * ``notification_attempt_count`` the amount of times this task has been started for this notification
    * ``task_attempt_count``: the number of times this specific task has been attempted

* ``subscription_does_not_exist``: could not retrieve an ``Abonnement`` for this pk and can therefore not deliver a message to this subscriber. Additional context:

    * ``channel_name``
    * ``resource``
    * ``resource_url``
    * ``main_object_url``
    * ``creation_date``
    * ``action``
    * ``additional_attributes``
    * ``subscription_pk``
    * ``notification_id``

Setup configuration
~~~~~~~~~~~~~~~~~~~

* ``subscription_created``: successfully created an Abonnement (subscription). Additional context: ``subscription_uuid``, ``subscription_pk``.
* ``subscription_updated``: successfully updated an Abonnement (subscription). Additional context: ``subscription_uuid``, ``subscription_pk``.
* ``channel_created``: successfully created a Kanaal (channel). Additional context: ``channel_name``, ``channel_pk``.
* ``channel_updated``: successfully updated a Kanaal (channel). Additional context: ``channel_name``, ``channel_pk``.

Schema generation
~~~~~~~~~~~~~~~~~

* ``unknown_openapi_action``: when generating the API schema, an unknown action was encountered and therefore no error responses can be shown. Additional context: ``action``.

Third party library events
--------------------------

For more information about log events emitted by third party libraries, refer to the documentation
for that particular library

* :ref:`Django (via django-structlog) <request_events>`
* :ref:`Celery (via django-structlog) <request_events>`
