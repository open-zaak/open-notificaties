=================
Open Notificaties
=================

:Version: 1.2.2
:Source: https://github.com/open-zaak/open-notificaties
:Keywords: zaken, zaakgericht werken, GEMMA, notificaties
:PythonVersion: 3.6

|build-status| |docs| |coverage| |black| |docker|

API voor het routeren van notificaties.

Ontwikkeld door `Maykin Media B.V.`_ in opdracht van Amsterdam, Rotterdam,
Utrecht, Tilburg, Arnhem, Haarlem, 's-Hertogenbosch, Delft en Hoorn,
Medemblik, Stede Broec, Drechteland, Enkhuizen (SED), onder regie van
`Dimpact`_.

Inleiding
=========

**Open Notificaties** is een modern en open source component voor het routeren van
berichten tussen componenten, systemen en applicaties. Het implementeert de
`gestandaardiseerde VNG Notificaties API`_.

Dit component is afhankelijk van een `Autorisaties API`_ voor regelen van autorisaties
en kan o.a. gebruikt worden in combinatie met de `API's voor Zaakgericht werken`_ zoals
geimplementeerd in `Open Zaak`_.

.. _`gestandaardiseerde VNG Notificaties API`: https://zaakgerichtwerken.vng.cloud/standaard/notificaties/index
.. _`API's voor Zaakgericht werken`: https://zaakgerichtwerken.vng.cloud/
.. _`Open Zaak`: https://github.com/open-zaak/open-zaak
.. _`Autorisaties API`: https://zaakgerichtwerken.vng.cloud/standaard/autorisaties/index

**Open Notificaties** gebruikt de code van de
`referentie implementaties van VNG Realisatie`_ als basis om een stabiele set API's te
realiseren die in productie gebruikt kunnen worden bij gemeenten.

.. _`referentie implementaties van VNG Realisatie`: https://github.com/VNG-Realisatie/gemma-zaken

Links
=====

* `Documentatie`_
* `Docker Hub`_

.. _`Documentatie`: https://open-notificaties.readthedocs.io/en/latest/
.. _`Docker Hub`: https://hub.docker.com/u/openzaak

Licentie
========

Licensed under the EUPL_

.. _EUPL: LICENSE.md
.. _Maykin Media B.V.: https://www.maykinmedia.nl
.. _Dimpact: https://www.dimpact.nl

.. |build-status| image:: https://travis-ci.org/open-zaak/open-notificaties.svg?branch=main
    :alt: Build status
    :target: https://travis-ci.org/open-zaak/open-notificaties

.. |docs| image:: https://readthedocs.org/projects/open-notificaties/badge/?version=latest
    :target: https://open-notificaties.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. |coverage| image:: https://codecov.io/github/open-zaak/open-notificaties/branch/main/graphs/badge.svg?branch=main
    :alt: Coverage
    :target: https://codecov.io/gh/open-zaak/open-notificaties

.. |black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black

.. |docker| image:: https://images.microbadger.com/badges/image/openzaak/open-notificaties.svg
    :target: https://microbadger.com/images/openzaak/open-notificaties

