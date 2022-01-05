.. _installation_self_signed:

Using self-signed certificates
==============================

Open Notificaties supports self-signed certificates in two ways:

* Hosting Open Notificaties using self-signed certificates - this is the classic route where
  your web server/ingress is configured appropriately
* Consuming services hosted with self-signed certificates - this is what this guide is
  about.

.. note::

   Some background!

   Open Notificaties communicates with external services such as Open Zaak, Github and
   of course any notification subscribers. It does this using ``https`` - using http is
   insecure.

   When Open Notificaties makes these requests, the SSL certificates are verified for their
   validity - e.g. expired certificates or certificates signed by an unkonwn Certificate
   Authority (CA) will throw errors (as they should!).

   When you're using self-signed certificates, you are essentially using an unkonwn CA,
   and this breaks the functionality of Open Notificaties.


Adding your own certificates or CA (root) certificate
-----------------------------------------------------

Open Notificaties supports adding extra, custom certificates to the provided CA bundle. You do
this by setting an environment variable ``EXTRA_VERIFY_CERTS``, which must be a
comma-separated list of paths to certificate files in PEM format.

An example of such a certificate is:

.. code-block:: none

    -----BEGIN CERTIFICATE-----
    MIIByDCCAW8CFBRCXMlcdJAPb8XkG4cYMNL+Ku17MAoGCCqGSM49BAMCMGcxCzAJ
    BgNVBAYTAk5MMRYwFAYDVQQIDA1Ob29yZC1Ib2xsYW5kMRIwEAYDVQQHDAlBbXN0
    ZXJkYW0xEjAQBgNVBAoMCU9wZW4gWmFhazEYMBYGA1UEAwwPT3BlbiBaYWFrIFRl
    c3RzMB4XDTIxMDMxOTExMDYyM1oXDTI0MDMxODExMDYyM1owZzELMAkGA1UEBhMC
    TkwxFjAUBgNVBAgMDU5vb3JkLUhvbGxhbmQxEjAQBgNVBAcMCUFtc3RlcmRhbTES
    MBAGA1UECgwJT3BlbiBaYWFrMRgwFgYDVQQDDA9PcGVuIFphYWsgVGVzdHMwWTAT
    BgcqhkjOPQIBBggqhkjOPQMBBwNCAASzDq7C9atfN3uxoAGOCro8RfzWloVusDeO
    bwXztxUC/wBu4WgfRsYjg65eVzaJWQKvIKn5W9rGyuIAYbJZJtMZMAoGCCqGSM49
    BAMCA0cAMEQCIHKCp4qVEzF3WgaL6jY4tf60HBThnQTaXC99P7TaIFhxAiASMBVV
    tmukm/NP8zSMrNpEGLnGIFa8uU/d8VwNNPFhtA==
    -----END CERTIFICATE-----

Typically you would do this by (bind) mounting a volume in the Open Notificaties container
containing these certificates, and then specify their paths in the container, for
example:

.. code-block:: bash

    docker run \
        -it \
        -v /etc/ssl/certs:/certs:ro \
        -e EXTRA_VERIFY_CERTS=/certs/root1.crt,/certs/root2.crt
        openzaak/open-notificaties:latest

Of course, you will need to adapt this solution to your deployment method (Helm,
Kubernetes, single-server...).
