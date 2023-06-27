Architecture
============

**Open Notificaties** is based on the `reference implementation of the "API's voor
Zaakgericht werken"`_ made by `VNG Realisatie`_. The overall architecture
remains faithful to the `Common Ground`_ principles and all API specifications.

The architecture of **Open Notificaties** focusses on excellent performance,
optimal stability and to guarantee data integrity. Under the hood, it uses
`RabbitMQ`_ as message broker with just a light weight REST API on top of it.

It largely resembles the original reference implementation and remains its own
component to scale separately from any other component.

.. _reference implementation of the "API's voor Zaakgericht werken": https://github.com/VNG-Realisatie/gemma-zaken
.. _VNG Realisatie: https://www.vngrealisatie.nl/
.. _Common Ground: https://commonground.nl/
.. _`VNG standards for "API's voor Zaakgericht werken"`: https://vng-realisatie.github.io/gemma-zaken/
.. _`RabbitMQ`: https://www.rabbitmq.com/
