.. _installation_configuration:

=======================================
Open Notificaties configuration (admin)
=======================================

Before you can work with Open Notificaties after installation, a few settings
need to be configured first.

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
      - **Component**: ``Notificatierouteringcomponent``

   c. Click **Opslaan**.

Adding new component to send notifications
------------------------------------------

For a complete example of setting up Open Zaak to send notifications to
Open Notificaties, see the `documentation of Open Zaak`_.

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

2. Finally, we need to allow Open Zaak to access Open Notificaties (for
   authentication purposes, so we can then check its authorizations):

   a. Navigate to **API Autorisaties > Client credentials**
   b. Click **Client credential toevoegen**.
   c. Fill out the form:

      - **Client ID**: *The same Client ID as given in Open Zaak step 2c*
      - **Secret**: *The same Secret as given in Open Zaak step 2c*

      Make sure Open Zaak is configured to use this Client ID and secret to
      access Open Notificaties.

   d. Click **Opslaan**.

All done!

.. _`documentation of Open Zaak`: https://open-zaak.readthedocs.io/en/latest/installation/config/openzaak_config.html#configure-notificaties-api
