.. _installation_hardware:

Hardware
========

Based on our initial :ref:`performance tests<performance_index>` in both a Kubernetes
environment and single machine setups, we can indicate some minimum system requirements
to reach a certain performance.

Notifications are likely to increase over time, due to more external components makes
use of it, or more subscribers want to receive notifications. Hence, we recommend a
Kubernetes setup since it will scale easier.

Determine what you need
-----------------------

Since notifications are typically only sent for update and create actions, the number
of notifications will most likely not be that high. Some functional views might cause
a series of create and/or update actions, so there is a short burst of notifications
which you will need to handle.

It really depends on how many consumers and other components will make use of Open
Notificaties but assuming 50 requests per second will probably be a good start for any
environment.

Minimum system requirements
---------------------------

* Platform: 64-bit
* Processor(s): 4 - 12 CPUs (see below) at 2.0 GHz
* RAM: 4 - 12 GB (see below)
* Hard disk space: 20 GB

Based on the number of requests per second you need, you can see what kind of hardware
you need to achieve this.

======================  ======  ==============
Requests per second     CPUs    Memory (GB)
----------------------  ------  --------------
50                      4       4
100                     6       6
200                     12      12
======================  ======  ==============

With these specifications you can run everything on a single machine or divided over
several instances.

General recommendations
~~~~~~~~~~~~~~~~~~~~~~~

* Use a seperate database server with roughly a third of the CPUs and memory as the
  main server. The database is usually the limiting factor.

Kubernetes recommendations
~~~~~~~~~~~~~~~~~~~~~~~~~~

* Preferably use 2 load balancer (like Traefik) replica's.
* Use as many replica's as available CPU's taking into account you need to have a few
  replica's for your load balancer, and possibly other services.
* RabbitMQ needs at least 256MB of memory - don't configure your resource limits lower
  than that amount.
