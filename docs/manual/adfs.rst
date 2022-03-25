.. _manual_adfs:

==============================
ADFS (On premise) Configureren
==============================

Open Notificaties ondersteunt Single Sign On (SSO) via ADFS voor de beheerinterface.

Gebruikers kunnen op die manier inloggen op Open Notificaties met hun ADFS account. In
deze flow:

1. Klikt een gebruiker op het inlogscherm op *Inloggen met ADFS*
2. De gebruiker wordt naar de ADFS omgeving geleid waar ze inloggen met gebruikersnaam
   en wachtwoord (en eventuele Multi Factor Authorization)
3. De ADFS omgeving stuurt de gebruiker terug naar Open Notificaties (waar de account
   aangemaakt wordt indien die nog niet bestaat)
4. Een beheerder in Open Notificaties kent de juiste groepen toe aan deze gebruiker als
   deze voor het eerst inlogt.

.. note:: Standaard krijgen deze gebruikers **geen** toegang tot de beheerinterface.
   Deze rechten moeten door een (andere) beheerder ingesteld worden. De account is wel
   aangemaakt indien deze nog niet bestond.

.. _manual_adfs_appgroup:

Configureren van ADFS zelf
==========================

Contacteer de IAM/ADFS-beheerders in je organisatie om een *Application Group* aan te
maken in de ADFS omgeving. Er zijn
`configuratiehandleidingen (Engels) <https://django-auth-adfs.readthedocs.io/en/latest/config_guides.html>`_ beschikbaar.

Voor de **Redirect URI** vul je ``https://open-notificaties.gemeente.nl/adfs/callback``
in, waarbij je ``open-notificaties.gemeente.nl`` vervangt door het relevante domein.

Aan het eind van dit proces moet je de volgende gegevens hebben (on premise):

* Server adres, bijvoorbeeld ``login.gemeente.nl``
* Client ID, bijvoorbeeld ``3ae1852d-bf76-4731-9c41-1a31928cf6a6``

Configureren van ADFS in Open Notificaties
==========================================

Zorg dat je de volgende :ref:`gegevens <manual_adfs_appgroup>` hebt:

* Server adres
* Client ID

Navigeer vervolgens in de admin naar **Configuratie** > **ADFS Confiugration**.

1. Vink *Enable* aan om ADFS in te schakelen.
2. Vul bij **Server (on premise)** het server adres in, bijvoorbeeld
   ``login.gemeente.nl``.
3. Vul bij **Client ID** het Client ID in, bijvoorbeeld
   ``3ae1852d-bf76-4731-9c41-1a31928cf6a6``.
4. Vul bij **Relying Party ID** opnieuw het Client ID in, bijvoorbeeld
   ``3ae1852d-bf76-4731-9c41-1a31928cf6a6``.
5. Laat bij **Claim mapping** de standaardwaarden staan.
6. Vul bij **Username claim** de waarde ``winaccountname`` in.

Klik tot slot rechtsonder op **Opslaan**.

Je kan vervolgens het makkelijkst testen of alles werkt door in een incognitoscherm
naar https://open-notificaties.gemeente.nl/admin/ te navigeren en op *Inloggen met ADFS*
te klikken.
