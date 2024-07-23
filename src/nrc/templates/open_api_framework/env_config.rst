{% extends "open_api_framework/env_config.rst" %}

{% block intro %}
Open Notificaties can be ran both as a Docker container or directly on a VPS or
dedicated server. It relies on other services, such as database and cache
backends, which can be configured through environment variables.
{% endblock %}

{% block extra %}
---------------------
Initial configuration
---------------------

Open Notificaties supports ``setup_configuration`` management command, which allows configuration via
environment variables.
All these environment variables are described at :ref:`installation_configuration_cli`.
{% endblock %}