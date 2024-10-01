.. _deployment_containers:

============================
Deploying on a single server
============================

Open Notificaties can be deployed on a single machine - either a dedicated server
(DDS) or virtual private server (VPS). The required hardware can be rented from a
hosting provider or be provided in your environment. Please see
:ref:`installation_hardware` to determine the hardware requirements.

This documentation describes the architecture, prerequisites and how to deploy
Open Notificaties on a server. Additionally, it documents the possible configuration
options.

.. note:: The default settings allow Open Notificaties to be deployed to the same
   machine as Open Zaak.

Architecture
============

The application is deployed as Docker containers, of which the images are
available on `docker hub`_. Traffic is routed to the server, where the web
server (nginx) handles SSL termination and proxies the requests to the
application containers.

Data is stored in a PostgreSQL database. By default, the database is installed
on the same machine (running on the host), but you can make use of a hosted
database (Google Cloud, AWS, Azure...). See the :ref:`containers_config_params`
for more information.

Prerequisites
=============

Before you can deploy, you need:

A server
--------

Ensure you have a server with ``root`` privileges. We assume you can directly
ssh to the machine as ``root`` user. If that's not the case, a user with
``sudo`` will also work. Python 3 must be available on the server.

.. note:: Make sure there is enough space in ``/var/lib/docker``. You need at
   least 8 GB to download all Docker container images.

**Supported operating systems**

Support for different Linux flavours is maintained in the `Ansible collection`_ used
for deployment.

Currently the following OS flavours are supported:

- Debian: buster (10, actively supported), stretch (9, actively supported), jessie (8)
- Ubuntu: eoan (EOL), disco (EOL), cosmic (EOL), bionic (18.04 LTS). focal (20.04 LTS)
  is not tested yet
- SUSE Enterprise Linux: 15 (actively supported)
- OpenSUSE: 15.1
- Red Hat: 7, 8
- CentOS: 7, 8 (actively supported)

.. _Ansible collection: https://github.com/open-zaak/ansible-collection

.. _deployment_containers_tooling:

A copy of the deployment configuration
--------------------------------------

You can either clone the https://github.com/open-zaak/open-notificaties
repository, or download and extract the latest ZIP:
https://github.com/open-zaak/open-notificaties/archive/main.zip

Python and a Python virtualenv
------------------------------

You will need to have at least Python 3.5 installed on your system. In the
examples, we assume you have Python 3.6.

Create a virtualenv with:

.. code-block:: shell

    [user@laptop]$ python3.6 -m venv env/
    [user@laptop]$ source env/bin/activate

Make sure to install the deployment tooling. In your virtualenv, install the
dependencies:

.. code-block:: shell

    (env) [user@laptop]$ pip install -r deployment/requirements.txt
    (env) [user@laptop]$ ansible-galaxy collection install -r requirements.yml
    (env) [user@laptop]$ ansible-galaxy role install -r requirements.yml

Deployment
==========

Deployment is done with an Ansible playbook, performing the following steps:

1. Install and configure PostgreSQL database server
2. Install the Docker runtime
3. Install the SSL certificate with Let's Encrypt
4. Setup Open Notificaties with Docker
5. Install and configure nginx as reverse proxy

Initial steps
-------------

Make sure the virtualenv is activated:

.. code-block:: shell

    [user@laptop]$ source env/bin/activate

Navigate to the correct deployment directory:

.. code-block:: shell

    (env) [user@laptop]$ cd deployment/single-server

Create the ``vars/open-notificaties.yml`` file - you can find an example in
``vars/open-notificaties.yml.example``. Generate a secret key using the
django secret key generator and put the value between single
quotes.

Configure the host by creating the ``hosts`` file from the example:

.. code-block:: shell

    (env) [user@laptop]$ cp hosts.example hosts

Edit the ``open-notificaties.gemeente.nl`` to point to your actual domain name. You must
make sure that the DNS entry for this domain points to the IP address of your
server.

.. warning:: It's important to use the correct domain name, as the SSL certificate
   will be generated for this domain and only this domain will be whitelisted
   by Open Notificaties! If you are using a private DNS name, then no SSL certificate
   can be created via Letsencrypt - make sure to disable it by setting
   ``certbot_create_if_missing=false``.

.. _deployment_containers_playbook:

Running the deployment
----------------------

Execute the playbook by running:

.. code-block:: shell

    (env) [user@laptop]$ ansible-playbook open-notificaties.yml

.. hint::

   * If you have your secrets Ansible vault encrypted, make sure you have either:

     * set the ``ANSIBLE_VAULT_PASSWORD_FILE`` environment variable, or
     * pass ``--ask-vault-pass`` flag to ``ansible-playbook``.

   * If you need to override any deployment variables (see
     :ref:`containers_config_params`), you can pass variables to
     ``ansible-playbook`` using the syntax:
     ``--extra-vars "some_var=some_value other_var=other_value"``.

   * If you want to run the deployment from the same machine as where it will
     run (ie. install to itself), you can pass ``--connection local`` to
     ``ansible-playbook``.

   * If you cannot connect as ``root`` to the target machine, you can pass
     ``--user <user> --become --become-method=sudo --ask-become-pass`` which
     will connect as user ``<user>`` that needs ``sudo``-rights on the target
     machine to install the requirements.

A full example might look like this:

.. code-block:: shell

    (env) [user@laptop]$ ansible-playbook open-notificaties.yml \
        --user admin
        --inventory my-hosts \  # Use inventory file ``my-hosts`` instead of ``hosts``.
        --limit open-notificaties.gemeente.nl \  # Only pick open-notificaties.gemeente.nl from the inventory file.
        --extra-vars "certbot_create_if_missing=false app_db_name=opennotificaties-test app_db_user=opennotificaties-test" \
        --connection local \
        --become \
        --become-method=sudo \
        --ask-become-pass

.. note:: You can run the deployment multiple times, it will not affect the final
   outcome. If you decide to change configuration parameters, you do not have
   to start from scratch.

Environment configuration
-------------------------

After the initial deployment, some initial configuration is required. This
configuration is stored in the database and is only needed once.

**Create a superuser**

A superuser allows you to perform all administrative tasks.

1. Log in to the server:

   .. code-block:: shell

       [user@laptop]$ ssh root@open-notificaties.gemeente.nl

2. Create the superuser (interactive on the shell). Note that the password you
   type in will not be visible - not even with asterisks. This is normal.

   .. code-block:: shell

       [root@open-notificaties.gemeente.nl]# docker exec -it opennotificaties-0 src/manage.py createsuperuser
       Gebruikersnaam: demo
       E-mailadres: admin@open-notificaties.gemeente.nl
       Password:
       Password (again):
       Superuser created successfully.

**Configure Open Notificaties Admin**

See the :ref:`installation_configuration` on how to configure Open Notificaties
post-installation.

.. _containers_config_params:

Configuration parameters
========================

At deployment time, you can configure a number of parts of the deployment by
overriding variables. You can override variables on the command line (using the
``-e "..."`` syntax) or by overriding them in ``vars/secrets.yml``.

.. note:: Tweaking configuration parameters is considered advanced usage.

Generic variables
-----------------

* ``certbot_admin_email``: e-mail address to use to accept the Let's Encrypt
  terms and conditions.
* ``certbot_create_if_missing``: whether to use Let's Encrypt to create an SSL
  certificate for your domain. Set to ``false`` if you want to use an existing
  certificate.

Open Notificaties specific variables
------------------------------------

The default values can be found in ``roles/opennotificaties/defaults/main.yml``.

* ``opennotificaties_db_port``: database port. If you are running multiple PostgreSQL versions
  on the same machine, you'll have to point to the correct port.
* ``opennotificaties_db_host``: specify the hostname if you're using a cloud database
  or a database on a different server.
* ``opennotificaties_db_name``: specify a different database name.
* ``opennotificaties_secret_key``: A Django secret key. Used for cryptographic
  operations - this may NOT leak, ever. If it does leak, change it.

**Scaling**

The ``opennotificaties_replicas`` variable controls scaling on backend services. If
your hardware allows it, you can create more replicas. By default, 3 replicas
are running.

The format of each replica is:

.. code-block:: yaml

    name: opennotificaties-i
    port: 900i

The port number must be available on the host - i.e. you may not have other
services already listening on that port.

The ``opennotificaties_worker_replicas`` variable controls the scaling of the queue
workers - these are responsible for actually distributing the notifications. By default,
3 replicas spin up.

The format of each replica is:

.. code-block:: yaml

    name: opennotificaties-worker-i

.. _docker hub: https://hub.docker.com/u/openzaak
.. _deployment_containers_updating:

Updating an Open Notificaties installation
==========================================

Make sure you have the deployment tooling installed - see
:ref:`the installation steps<deployment_containers_tooling>` for more details.

If you have an existing environment (from the installation), make sure to update it:

.. code-block:: shell

    # fetch the updates from Github
    [user@host]$ git fetch origin

    # checkout the tag of the version you wish to update to, e.g. 1.0.0
    [user@host]$ git checkout X.Y.z

    # activate the virtualenv
    [user@host]$ source env/bin/activate

    # ensure all (correct versions of the) dependencies are installed
    (env) [user@host]$ pip install -r requirements.txt
    (env) [user@host]$ ansible-galaxy install -r requirements.yml

Open Notificaties deployment code defines variables to specify the Docker image tag to
use. This is synchronized with the git tag you're checking out.

Next, to perform the upgrade, you run the ``open-notificaties.yml`` playbook just like
with the installation in :ref:`deployment_containers_playbook`:

.. code-block:: shell

    (env) [user@laptop]$ ansible-playbook open-notificaties.yml

.. note::
    This will instruct the docker containers to restart using a new image. You may
    notice some brief downtime (order of seconds to minutes) while the new image is
    being downloaded and containers are being restarted.
