.. _installation_configuration:

=======================================
Open Notificaties configuration (admin)
=======================================

Before you can work with Open Notificaties after installation, a few settings
need to be configured first. We assume that Open Notificaties is used together with Open
Zaak.

Configure Notificaties API
==========================

Open Notificaties uses the Autorisaties API to check if the sender is
authorized to send notifications. Open Zaak offers an Autorisaties API and
below we assume you use this one.

1. Configure the Open Zaak Autorisaties API endpoint (so Open Notificaties
   knows where to check for the proper autorisations):

   a. Navigate to **Configuratie > Autorisatiecomponentconfiguratie**
   b. Fill out the form:

      - **API root**: *The URL to the Notificaties API. For example:*
        ``https://open-zaak.gemeente.local/autorisaties/api/v1/``.
      - **Component**: ``Notificaties API``

   c. Click **Opslaan**.

Adding new component to send notifications
------------------------------------------

Below are the general steps to allow an application to send notifications and
using Open Zaak as the example.

1. Configure the credentials for the Open Zaak Autorisaties API (so Open
   Notificaties can access the Autorisaties API):

   a. Navigate to **API Autorisaties > Externe API credentials**
   b. Click **Externe API credential toevoegen**.
   c. Fill out the form:

      - **API root**: *The URL of the Open Zaak Autorisaties API endpoint*
      - **Label**: *For example:* ``Open Zaak Autorisaties``

      - **Client ID**: *For example:* ``open-notificaties``
      - **Secret**: *Some random string*
      - **User ID**: *Same as the Client ID*
      - **User representation**: *For example:* ``Open Notificaties``

      Make sure Open Notificaties is authorized in Open Zaak to access the
      Autorisaties API by using the same Client ID and Secret as given here.

   d. Click **Opslaan**.

2. Then we need to allow Open Zaak to access Open Notificaties (for
   authentication purposes, so we can then check its authorizations):

   a. Navigate to **API Autorisaties > Client credentials**
   b. Click **Client credential toevoegen**.
   c. Fill out the form:

      - **Client ID**: *For example:* ``open-zaak``
      - **Secret**: *Some random string*

      Make sure Open Zaak is configured to use this Client ID and secret to
      access Open Notificaties.

   d. Click **Opslaan**.

3. After that, we need to configure the **Notificatiescomponentconfiguratie**.

   a. Navigate to **Configuratie > Notificatiescomponentconfiguratie** and add a new **Notifications api service**
   b. Fill out the form and use the client ID and secret from step 1c
   c. Click **Opslaan** on the **Service** form
   d. Click **Opslaan** on the **Notificatiescomponentconfiguratie** form

4. Finally, we need to add the client ID and secret from step 1c under **API Autorisaties > Autorisatiegegevens > Autorisatiegegeven toevoegen**

Configure Open Zaak
===================

In case Open Zaak is not configured yet, refer to `configuration of Open Zaak`_. Use the following as input for the management command:

   - **notifications-api-app-client-id**: client ID from step 1c above
   - **notifications-api-app-secret**: secret from step 1c above
   - **notifications-api-client-id**: client ID from step 2c above
   - **notifications-api-secret**: secret from from step 2c above

Add notification consumers
==========================

In order to add new consumer webhooks that are subscribed to specific channels, follow these steps:

1. Ensure your consumer webhook can handle the notification body (see `API specification`_)
2. Ensure your consumer webhook responds to notifications with a status code in the range 200-209
3. (Optional) If no **Kanaal** exists for the resource, create it via the admin interface

   a. Navigate to **Notificaties** > **Kanalen** > **Kanaal toevoegen**
   b. Fill out the form:

      - **Naam**: the name of the channel
      - **Documentatie link**: optional, URL that points towards documentation about the channel
      - **Filters**: optional, comma separated list of attributes on which subscriptions can filter

4. Configure an **Abonnement** for the consumer webhook

   a. Navigate to **Notificaties > Abonnementen > Abonnement toevoegen**
   b. Fill out the form:

     - **Callback URL**: the URL of the consumer webhook to which Open Notificaties will send notifications
     - **Autorisatie header**: the authorization header that Open Notificaties will use for its requests to the callback URL
     - **Client ID**: optional, the client identifier used in the authorization header (in case of JWT)
     - **Filters > Kanaal**: the channels to which the consumer webhook should be subscribed

   .. warning:: The `manual`_ describes how to add **Abonnementen**, but the mechanism to support authentication (JWT or otherwise) does not function properly at the moment. The method to add **Abonnementen** as described above is a workaround for this issue


All done!

.. _`documentation of Open Zaak`: https://open-zaak.readthedocs.io/en/latest/installation/config/openzaak_config.html#configure-notificaties-api
.. _`configuration of Open Zaak`: https://open-zaak.readthedocs.io/en/stable/installation/config/openzaak_config_cli.html#open-zaak-configuration
.. _`manual`: https://open-notificaties.readthedocs.io/en/stable/manual/subscriptions.html#aanmaken-abonnement
.. _`API specification`: https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/open-zaak/open-notificaties/1.0.0/src/openapi.yaml#tag/notificaties