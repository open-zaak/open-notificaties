=================
Open Notificaties
=================

:Version: 1.15.0
:Source: https://github.com/open-zaak/open-notificaties
:Keywords: zaken, zaakgericht werken, GEMMA, notificaties
:PythonVersion: 3.12

|build-status| |docs| |coverage| |code-style| |codeql| |ruff| |docker| |python-versions|

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

.. |code-style| image:: https://github.com/open-zaak/open-notificaties/actions/workflows/code_quality.yml/badge.svg?branch=main
    :alt: Code style
    :target: https://github.com/open-zaak/open-notificaties/actions/workflows/code_quality.yml

.. |codeql| image:: https://github.com/open-zaak/open-notificaties/actions/workflows/codeql-analysis.yml/badge.svg?branch=main
    :alt: CodeQL scan
    :target: https://github.com/open-zaak/open-notificaties/actions/workflows/codeql-analysis.yml

.. |python-versions| image:: https://img.shields.io/badge/python-3.12%2B-blue.svg
    :alt: Supported Python version

.. |ruff| image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
    :target: https://github.com/astral-sh/ruff
    :alt: Ruff

.. |docker| image:: https://img.shields.io/docker/image-size/openzaak/open-notificaties
    :target: https://hub.docker.com/r/openzaak/open-notificaties

