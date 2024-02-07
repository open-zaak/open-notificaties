=================
Open Notificaties
=================

:Version: 1.5.2
:Source: https://github.com/open-zaak/open-notificaties
:Keywords: zaken, zaakgericht werken, GEMMA, notificaties
:PythonVersion: 3.10

|build-status| |docs| |coverage| |black| |docker|

API voor het routeren van notificaties.

Ontwikkeld door `Maykin B.V.`_ in opdracht van Amsterdam, Rotterdam,
Utrecht, Tilburg, Arnhem, Haarlem, 's-Hertogenbosch, Delft en Hoorn,
Medemblik, Stede Broec, Drechteland, Enkhuizen (SED) en Dimpact.

Inleiding
=========

**Open Notificaties** is een modern en open source component voor het routeren van
berichten tussen componenten, systemen en applicaties. Het implementeert de
`gestandaardiseerde VNG Notificaties API`_.

Dit component is afhankelijk van een `Autorisaties API`_ voor regelen van autorisaties
en kan o.a. gebruikt worden in combinatie met de `API's voor Zaakgericht werken`_ zoals
geimplementeerd in `Open Zaak`_.

.. _`gestandaardiseerde VNG Notificaties API`: https://vng-realisatie.github.io/gemma-zaken/standaard/notificaties/
.. _`API's voor Zaakgericht werken`: https://vng-realisatie.github.io/gemma-zaken/
.. _`Open Zaak`: https://github.com/open-zaak/open-zaak
.. _`Autorisaties API`: https://vng-realisatie.github.io/gemma-zaken/standaard/autorisaties/

**Open Notificaties** is gebaseerd op de broncode van de
`referentie implementatie van VNG Realisatie`_ om stabiele API te realiseren die in 
productie gebruikt kan worden bij gemeenten.

.. _`referentie implementatie van VNG Realisatie`: https://github.com/VNG-Realisatie/gemma-zaken

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
.. _Maykin B.V.: https://www.maykinmedia.nl

.. |build-status| image:: https://github.com/open-zaak/open-notificaties/workflows/Run%20CI/badge.svg
    :alt: Build status
    :target: https://github.com/open-zaak/open-notificaties/actions?query=workflow%3A%22Run+CI%22

.. |docs| image:: https://readthedocs.org/projects/open-notificaties/badge/?version=latest
    :target: https://open-notificaties.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. |coverage| image:: https://codecov.io/github/open-zaak/open-notificaties/branch/main/graphs/badge.svg?branch=main
    :alt: Coverage
    :target: https://codecov.io/gh/open-zaak/open-notificaties

.. |black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black

.. |docker| image:: https://img.shields.io/docker/image-size/openzaak/open-notificaties
    :target: https://hub.docker.com/r/openzaak/open-notificaties

