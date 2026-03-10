.. _cloud_events_configuration_mijn_overheid:

==========================================
Configuring cloud events for Mijn Overheid
==========================================

Open Notificaties has experimental support for sending cloud events to subscribed webhooks.

This can be used to send cloud events to Mijn Overheid. In order to make this possible, some
configuration is required, which can be done manually or loaded using :ref:`setup_configuration <installation_configuration_cli>`.

Using ``setup_configuration``
-----------------------------

For ``setup_configuration``, a configuration similar to this could be used
(see the related configuration step
:ref:`documentation <ref_step_nrc.setup_configuration.abonnementen.AbonnementConfigurationStep>` for more details):

.. validate-config-example:: nrc.setup_configuration.abonnementen.AbonnementConfigurationStep

    notifications_abonnementen_config_enable: true
    notifications_abonnementen_config:
      items:
        - uuid: 02907e89-1ba8-43e9-a86c-d0534d461316  # Some generated UUID
          callback_url: https://example.com/api/webhook/  # the URL of the API of Mijn Overheid
          cloudevent_filters:
            # Filter on a specific zaaktype for the ``zaak-gemuteerd`` event
            # Repeat if needed for multiple zaaktypen
            - filters:
                zaaktype: https://openzaak.local/catalogi/api/v1/zaaktypen/d109cd8a-fe7b-4eb2-8cab-766712a4a267
              type_substring: nl.overheid.zaken.zaak-gemuteerd
          auth_type: oauth2_client_credentials
          auth_client_id: client-id  # client id as received from Logius
          secret: my-secret
          oauth2_token_url: https://auth.example.com/token
          send_cloudevents: true

If mutual TLS is required, the certificates for that have to be configured manually (see below),
as this is not possible via ``setup_configuration`` at the moment.

.. TODO::

    Ensure that certificates for mutual TLS can also be loaded using ``setup_configuration``

Manual configuration
--------------------

1. Make sure that PKIOverheid root certificate is added via the environment variable
   ``EXTRA_VERIFY_CERTS`` (see :ref:`installation_self_signed` for more information)
2. In the admin interface, navigate to **Notificaties > Abonnementen** and click **Abonnement toevoegen**.
3. Fill out the following fields

    * ``Callback URL``: enter the URL of the API of Mijn Overheid
    * ``Authorization type``: select ``OAuth2 client credentials flow``
    * ``Client id``: enter the client id as received from Logius
    * ``Secret``: enter the secret as received from Logius
    * ``OAuth2 token url``: enter the URL of the Logius authentication server token endpoint
    * (If mutual TLS is required): ``Client certificate`` click the ``+`` icon:

        * ``Label``: e.g. ``client certificate for Logius``
        * ``Type``: ``Key-pair``
        * ``Public certificate``: upload the public certificate to be used for mTLS
        * ``Private key``: upload the private key to be used for mTLS

    * (Alternative if step 1 was skipped): ``Server certificate`` click the ``+`` icon:

        * ``Label``: e.g. ``PKIOverheid root certificate``
        * ``Type``: ``Certificate only``
        * ``Public certificate``: upload the PKIOverheid root certificate

    * Check the checkbox ``Verstuur cloudevents``

    * Under **Cloud event filter groups**, add an entry with:

        * ``Type substring``: ``nl.overheid.zaken.zaak-gemuteerd``

    * To ensure that only events for specific zaaktypen are sent to Mijn Overheid, click
      **Opslaan en opnieuw bewerken** and under **Cloud event filter groups**
      click **Filters instellen**

        * Make sure the key is ``zaaktype`` and the value is the URL of the zaaktype
          for which events must be sent to Mijn Overheid

In order to add filters on multiple zaaktypen, repeat the last two steps for each
zaaktype.
