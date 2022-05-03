.. _delivery_guarantees:

Delivery guarantees
===================

Mechanism
---------

The Notificaties API standard (and by extension Open Notificaties) operates on a simple
yet powerful message delivery mechanism: webhooks_.

A webhook, in essence, is nothing more than and HTTP endpoint exposed by a server where
HTTP requests/messages can be sent to. Upon receiving such a request, the webhook
receiver is responsible for processing the content of this request appropriately.

Webhooks are registered by parties interested in receiving notifications. The webhook
registration is recorded and saved in Open Notificaties. Whenever (another) party
publishes a notification, it does so by making a ``HTTP POST`` call to the Open
Notificaties API. Open Notificaties, in turn, checks which parties should receive this
notification and forwards the message to the registered webhook.

.. _webhooks: https://en.wikipedia.org/wiki/Webhook

Failure modes
-------------

Even though the mechanism is simple, the underlying infrastructure is not. There is
always a chance that a message does not get properly delivered - a problem that all
*message broker* systems have.

The Notificaties API standard defines that recipients of a message/notification have to
reply with a HTTP 204 status code to confirm that the message was received. However,
to complicate things further, this confirmation response may also be lost. To summarize,
the following scenarios are possible:

* Open Notificaties delivers message and receives confirmation (happy flow)
* Open Notificaties delivers message but does not receive a confirmation (failure mode)
* Open Notificaties fails to deliver the message successfully (failure mode)

Now there are essentially two mitigation modes available:

* at-most-once delivery
* at-least-once delivery

Delivering a message exactly once is not possible since the underlying infrastructure
("the internet") may fail for whatever reason.

Mitigations
-----------

Open Notificaties operates in "at-least-once" delivery mode. This means that whenever
a delivery attempt succeeds, no more delivery attempts are made and whenever no
confirmation is received, another delivery attempt will be made.

A failure can be in the form of an HTTP status code that does **not** indicate
`success <https://developer.mozilla.org/en-US/docs/Web/HTTP/Status#successful_responses>`_
(so anything other than ``HTTP 200``, ``HTTP 201``, ``HTTP 202``, ``HTTP 204``) or
network errors such as connection or timeout errors (or anything else going wrong). In
practice, Open Notificaties will consider any ``2xx`` response status code as
"message is delivered, no further attempts must be made".

.. note:: Webhook subscribers must be able to handle multiple deliveries of the same message! If
   they received a message correctly but failed to reply with a success response, Open
   Notificaties will deliver the same message again.

**Retry mechanism**

On delivery failure, Open Notificaties will automatically retry delivery, with
exponential backoff. E.g. the first retry will be done after one second, the next after
two seconds and the third after 4 seconds.

The parameters for this can be :ref:`configured <installation_config_index>`:

* ``NOTIFICATION_DELIVERY_MAX_RETRIES``: the maximum number of automatic retries. After
  this amount of retries, Open Notificaties stops trying to deliver the message.
* ``NOTIFICATION_DELIVERY_RETRY_BACKOFF``: if specified, a factor applied to the
  exponential backoff. This allows you to tune how quickly automatic retries are
  performed.
* ``NOTIFICATION_DELIVERY_RETRY_BACKOFF_MAX``: an upper limit to the exponential
  backoff time.

On top of that, via the admin interface you can manually select notifications to retry
delivery for.

**Open Notificaties message broker**

Under the hood, notifications are distributed by background workers to ensure API
endpoint availability. For this we rely on RabbitMQ_ as internal message broker between
the API and background workers.

RabbitMQ is excellent in terms of message guarantees and can survive restarts. However,
configuring RabbitMQ for these kind of operation modes is in the scope of the infrastructure
you are running Open Notificaties on. We advise you to configure the persistent storage
appropriately for maximum robustness.

The *results* and metadata of the background tasks are stored in Redis, which is an
in-memory key-value store. Redis *can* be used as a message broker too, but Open
Notificaties only uses it as a cache and result store - RabbitMQ is the message broker.
However, you can also configure Redis appropriately so that it saves snapshots to disk
according to your reliability requirements. This also requires you to provide Redis with
a suitable persistent storage.

Task metadata is important for keeping track of automatic delivery retries, so it is
recommended to set up Redis as a highly-available and/or persistent storage.

.. _RabbitMQ: https://www.rabbitmq.com/
.. _Redis: https://redis.io/
