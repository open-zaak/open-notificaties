.. _cloud_events_configuration_mijn_overheid:

==========================================
Configuring cloud events for Mijn Overheid
==========================================

Open Notificaties has experimental support for sending cloud events to subscribed webhooks.

This can be used to send cloud events to Mijn Overheid. In order to make this possible, some
configuration is required.

1. Make sure that PKIOverheid root certificate is added via the environment variable
   ``EXTRA_VERIFY_CERTS`` (see :ref:`installation_self_signed` for more information)
2. In the admin interface, navigate to **Notificaties > Abonnementen** and click **Abonnement toevoegen**.
3. Fill out the following fields

    * ``Label``: e.g.: ``Mijn Overheid``
    * ``Callback URL``: enter the URL of the API of Mijn Overheid
    * ``Authorization type``: select ``OAuth2 client credentials flow``
    * ``Client id``: enter the client id as received from Logius
    * ``Secret``: enter the secret as received from Logius
    * ``OAuth2 token url``: enter the URL of the Logius authentication server token endpoint
    * (Optional if mutual TLS is required): ``Client certificate`` click the ``+`` icon:

        * ``Label``: e.g. ``client certificate for Logius``
        * ``Type``: ``Key-pair``
        * ``Public certificate``: upload the public certificate to be used for mTLS
        * ``Private key``: upload the private key to be used for mTLS

    * (Alternative if step 1 was skipped): ``Server certificate`` click the ``+`` icon:

        * ``Label``: e.g. ``PKIOverheid root certificate``
        * ``Type``: ``Certificate only``
        * ``Public certificate``: upload the PKIOverheid root certificate

    * Under **Cloud event filter groups**, add an entry with:

        * ``Type substring``: ``nl.overheid.zaken.zaak-gemuteerd``

    * To ensure that only events for specific zaaktypen are sent to Mijn Overheid, click
      **Opslaan en opnieuw bewerken** and under **Cloud event filter groups**
      click **Filters instellen**

        * Make sure the key is ``zaaktype`` and the value is the URL of the zaaktype
          for which events must be sent to Mijn Overheid

In order to add filters on multiple zaaktypen, repeat the last two steps for each
zaaktype.
