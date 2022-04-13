# Environment configuration reference

Open Notificaties can be ran both as a Docker container or directly on a VPS or
dedicated server. It relies on other services, such as database and cache
backends, which can be configured through environment variables.

## Available environment variables

### Required

* `DJANGO_SETTINGS_MODULE`: which environment settings to use. Available options:
  - `nrc.conf.production`
  - `nrc.conf.staging`
  - `nrc.conf.docker`
  - `nrc.conf.dev`
  - `nrc.conf.ci`

* `SECRET_KEY`: secret key that's used for certain cryptographic utilities. You
  should generate one via
  [miniwebtool](https://www.miniwebtool.com/django-secret-key-generator/)

* `ALLOWED_HOSTS`: a comma separated (without spaces!) list of domains that
  serve the installation. Used to protect against `Host` header attacks.

**Docker**

Additionally, the following optional envvars MUST be set/changed when running
on Docker, since `localhost` is contained within the container:

* `CACHE_DEFAULT`
* `CACHE_AXES`
* `EMAIL_HOST`

### Optional

* `SITE_ID`: defaults to `1`. The database ID of the site object. You usually
  won't have to touch this.

* `DEBUG`: defaults to `False`. Only set this to `True` on a local development
  environment. Various other security settings are derived from this setting!

* `IS_HTTPS`: defaults to the inverse of `DEBUG`. Used to construct absolute
  URLs and controls a variety of security settings.

* `DB_HOST`: hostname of the PostgreSQL database. Defaults to `localhost`,
  unless you're using the `docker` environment, then it defaults to `db`.

* `DB_USER`: username of the database user. Defaults to `opennotificaties`,
  unless you're using the `docker` environment, then it defaults to `postgres`.

* `DB_PASSWORD`: password of the database user. Defaults to `opennotificaties`,
  unless you're using the `docker` environment, then it defaults to no password.

* `DB_NAME`: name of the PostgreSQL database. Defaults to `opennotificaties`,
  unless you're using the `docker` environment, then it defaults to `postgres`.

* `DB_PORT`: port number of the database, defaults to `5432`.

* `NUM_PROXIES`: the number of reverse proxies in front of Open Notificaties, as an
  integer. This is used to determine the actual client IP adres. Defaults to 1, which
  should be okay on Kubernetes when using an Ingress.

* `CACHE_DEFAULT`: redis cache address for the default cache. Defaults to
  `localhost:6379/0`.

* `CACHE_AXES`: redis cache address for the brute force login protection cache.
  Defaults to `localhost:6379/0`.

* `EMAIL_HOST`: hostname for the outgoing e-mail server. Defaults to
  `localhost`.

* `EMAIL_PORT`: port number of the outgoing e-mail server. Defaults to `25`.
  Note that if you're on Google Cloud, sending e-mail via port 25 is completely
  blocked and you should use 487 for TLS.

* `EMAIL_HOST_USER`: username to connect to the mail server. Default empty.

* `EMAIL_HOST_PASSWORD`: password to connect to the mail server. Default empty.

* `EMAIL_USE_TLS`: whether to use TLS or not to connect to the mail server.
  Defaults to `False`. Should be `True` if you're changing the `EMAIL_PORT` to
  `487`.

* `SENTRY_DSN`: URL of the sentry project to send error reports to. Default
  empty, i.e. -> no monitoring set up. Highly recommended to configure this.

* `EXTRA_VERIFY_CERTS`: a comma-separated list of paths to certificates to trust, empty
  by default. If you're using self-signed certificates for the services that Open Notificaties
  communicates with, specify the path to those (root) certificates here, rather than
  disabling SSL certificate verification. Example:
  `EXTRA_VERIFY_CERTS=/etc/ssl/root1.crt,/etc/ssl/root2.crt`.

* `LOG_NOTIFICATIONS_IN_DB`: indicates whether or not sent notifications should be saved to the database (default: `False`).

### Celery

* `CELERY_BROKER_URL`: the URL of the broker that will be used to actually send the notifications (default: `amqp://127.0.0.1:5672//`).

* `CELERY_RESULT_BACKEND`: the backend where the results of tasks will be stored (default: `redis://localhost:6379/1`)

* `NOTIFICATION_DELIVERY_MAX_RETRIES`: the maximum number of retries Celery will do if sending a notification failed.

* `NOTIFICATION_DELIVERY_RETRY_BACKOFF`: a boolean or a number. If this option is set to
  `True`, autoretries will be delayed following the rules of exponential backoff. If
  this option is set to a number, it is used as a delay factor.

* `NOTIFICATION_DELIVERY_RETRY_BACKOFF_MAX`: an integer, specifying number of seconds.
  If ``retry_backoff`` is enabled, this option will set a maximum delay in seconds
  between task autoretries. By default, this option is set to 48 seconds.

### Cross-Origin-Resource-Sharing

The following parameters control the CORS policy.

* `CORS_ALLOW_ALL_ORIGINS`: allow cross-domain access from any client. Defaults to `False`.

* `CORS_ALLOWED_ORIGINS`: explicitly list the allowed origins for cross-domain requests.
  Defaults to an empty list. Example: `http://localhost:3000,https://some-app.gemeente.nl`.

* `CORS_ALLOWED_ORIGIN_REGEXES`: same as `CORS_ALLOWED_ORIGINS`, but supports regular
  expressions.

* `CORS_EXTRA_ALLOW_HEADERS`: headers that are allowed to be sent as part of the cross-domain
  request. By default, `Authorization`, `Accept-Crs` and `Content-Crs` are already
  included. The value of this variable is added to these already included headers.
  Defaults to an empty list.

## Specifying the environment variables

There are two strategies to specify the environment variables:

* provide them in a `.env` file
* start the Open Notificaties processes (with uwsgi/gunicorn/celery) in a process
  manager that defines the environment variables

### Providing a .env file

This is the most simple setup and easiest to debug. The `.env` file must be
at the root of the project - i.e. on the same level as the `src` directory (
NOT _in_ the `src` directory).

The syntax is key-value:

```
SOME_VAR=some_value
OTHER_VAR="quoted_value"
```

### Provide the envvars via the process manager

If you use a process manager (such as supervisor/systemd), use their techniques
to define the envvars. The Open Notificaties implementation will pick them up out of
the box.
