.. _manual_subscriptions:

======================
Abonnementen toevoegen
======================

Om te kunnen beginnen met het definiëren van Abonnementen in Open Notificaties, zijn de volgende
zaken nodig (naast Open Notificaties zelf):

* Een Autorisaties API
* Een component dat notificaties kan versturen naar Open Notificaties (in deze handleiding is dit de Autorisaties API)
* Een component dat notificaties kan ontvangen via een webhook callback (beveiligd met JWT authenticatie)

Vastleggen credentials
======================

Allereerst moeten de credentials van alle componenten vastgelegd zijn in de Autorisaties API.
Het gaat om de volgende credentials:

* Er moet een ``Applicatie`` zijn die Open Notificaties de scopes **autorisaties.lezen**, **notificaties.consumeren** en
  **notificaties.publiceren** geeft.
* Er moet een ``Applicatie`` zijn die de API die notificaties gaat versturen (in dit geval Autorisaties API)
  de scope **notificaties.publiceren** geeft.

In het geval dat de Autorisaties API van Open Zaak gebruikt wordt, moeten er ook
``Services`` aangemaakt worden die gebruik maken van de aangemaakte ``Applicaties``,
zie `Open Zaak documentatie`_.

Aanmaken kanaal
===============

Vervolgens moet het ``Kanaal``, waarvoor de notificaties verstuurd gaan worden, aangemaakt worden
in de API van Open Notificaties. In het geval van Autorisaties API heet dit kanaal **autorisaties**.

In Open Zaak is er een makkelijke manier om kanalen te registreren, zie `Open Zaak documentatie over kanalen`_

Aanmaken abonnement
===================

.. warning::

   Het aanmaken van abonnementen via de admininterface is bedoeld voor debug-doeleinden,
   idealiter worden abonnementen aangemaakt via de API.

Het abonnement kan aangemaakt worden door in de admininterface van Open Notificaties
te navigeren naar **Configuratie > Webhook subscriptions > Toevoegen**.

Vul vervolgens het formulier in:

1. Kies bij **Config** de enige optie, namelijk het endpoint van de Open Notificaties API zelf
2. Vul bij **Callback url** de callback URL in van het component dat notificaties moet
   gaan ontvangen (de abonnee)
3. Vul bij **Client ID** het client ID in waarmee het JWT gemaakt wordt
   dat gebruikt wordt om de callback URL aan te spreken
4. Vul bij **Client secret** het client secret in waarmee het JWT gemaakt wordt
   dat gebruikt wordt om de callback URL aan te spreken
5. Vul bij **Channels** de kanalen in waarop geabonneerd moet worden (bijv. ``autorisaties``)

Klik vervolgens op de **Opslaan** knop. Tot slot moet de webhook geregistreerd worden,
dit gaat als volgt:

1. Vink de aangemaakte **Webhook subscription** aan in de lijst,
2. Klik op het dropdown menu **Acties** en selecteer ``Register the webhooks``
3. Klik op **Uitvoeren**

Vanaf nu zullen alle notificaties voor het gekozen ``Kanaal`` doorgestuurd worden naar de geconfigureerde webhook.

Filters instellen
=================

Per abonnement kunnen filteropties ingesteld worden, waarmee gefilterd kan worden op waardes van kenmerken
die meegegeven worden met de notificaties. De kenmerken waarop gefilterd kan worden zijn gedefinieerd per
kanaal, bijvoorbeeld: `kenmerken <https://github.com/VNG-Realisatie/zaken-api/blob/stable/1.0.x/src/notificaties.md>`_ voor het kanaal ``zaken``.

Filters kunnen toegevoegd worden aan abonnementen door in de admininterface van Open Notificaties
te navigeren naar **Notificaties > Abonnementen**.

1. Klik op de UUID van het abonnement waarvoor filters toegevoegd moeten worden
2. Klik onder het kopje **Filters** op **Nog een Filter toevoegen**
3. Selecteer het kanaal waarvoor dit filter geldt (bijv. ``zaken``) en klik op **Opslaan en opnieuw bewerken**
4. Klik vervolgens voor het aangemaakte filter onder **Acties** op **Filters instellen**
5. Klik onder het kopje **Filter-onderdelen** op **Nog een filter-onderdeel toevoegen** en vul in:

   - **Sleutel**: de naam van het kenmerk (bijv. ``bronorganisatie``)
   - **Waarde**: de waarde waarop gefilterd moet worden (bijv. ``123456789``)

6. Klik op **Opslaan**

Vanaf nu worden notificaties voor het gekozen kanaal alleen verstuurd naar de geabonneerde callback
als de waarde van het gekozen kenmerk van deze notificaties gelijk is aan de instelde waarde.

.. note::
   Om voor hetzelfde kenmerk te filteren op meerdere waardes, moeten er een nieuw **Filter**
   toegevoegd worden per waarde (volgens de bovenstaande stappen)

.. _`Open Zaak documentatie`: https://open-zaak.readthedocs.io/en/stable/installation/config/openzaak_config.html#open-zaak
.. _`Open Zaak documentatie over kanalen`: https://open-zaak.readthedocs.io/en/stable/installation/config/openzaak_config.html#register-notification-channels
