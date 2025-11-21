.. _manual_notifications:

================================
Handmatig notificaties versturen
================================

Via de admininterface van Open Notificaties kunnen ook handmatig notificaties aangemaakt
en verstuurd worden. Dit kan handig zijn om notificaties en abonnementen te testen.

Notificaties versturen
======================

Een nieuw notificatie aanmaken in de admininterface van Open Notificaties gaat als volgt:

1. Navigeer naar **Notificaties > Notificaties > Toevoegen**
2. Vul bij **Forwarded msg** het te versturen bericht in JSON formaat in, dit kan er als volgt uitzien:

   .. code-block:: json

         {
            "actie": "create",
            "kanaal": "objecten",
            "source": "objecten.maykin.nl",
            "resource": "object",
            "kenmerken": {"objectType": "https://example.com"},
            "hoofdObject": "https://example.com",
            "resourceUrl": "https://example.com",
            "aanmaakdatum": "2022-04-02T09:00:00Z"
         }

3. Selecteer bij **Kanaal** het kanaal waarvoor de notificatie gestuurd moet worden
4. Klik vervolgens op **Opslaan**, de nieuwe notificatie zal verschijnen bovenin de lijst
5. Klik op de notificatie, en zie de responses van de geabonneerde callbacks onder het kopje **Notificatie responses**

Bestaande notificaties opnieuw versturen
========================================

Het is ook mogelijk om bestaande notificaties opnieuw te versturen, dit kan handig zijn als
het sturen van een notificatie eerder gefaald is bijvoorbeeld. Een bestaande notificatie
opnieuw versturen in de admininterface van Open Notificaties gaat als volgt:

1. Navigeer in de admininterface naar **Notificaties > Notificatie**
2. Vink de notificatie of notificaties aan die verstuurd moeten worden
3. Selecteer vervolgens bij **Actie** **Re-send the selected notifications** en klik op **Uitvoeren**
4. Kijk per verzonden notificatie of deze nu wel goed zijn aangekomen bij de geabonneerde callbacks
