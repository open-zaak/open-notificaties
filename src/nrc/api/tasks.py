import inspect
import json
import logging
from urllib.parse import urlparse
from uuid import UUID

from django.conf import settings
from django.core.mail import send_mail
from django.core.serializers.json import DjangoJSONEncoder
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

import requests
from celery.exceptions import Ignore, Retry
from celery.utils.time import get_exponential_backoff_interval
from vine.utils import wraps
from vng_api_common.notifications.models import NotificationsConfig

from nrc.celery import app
from nrc.datamodel.models import Abonnement, NotificatieResponse

logger = logging.getLogger(__name__)


def add_autoretry_behaviour(task, **options):
    """
    Adapted from celery to use admin configurable autoretry settings
    """
    autoretry_for = tuple(
        options.get("autoretry_for", getattr(task, "autoretry_for", ()))
    )
    retry_kwargs = options.get("retry_kwargs", getattr(task, "retry_kwargs", {}))
    retry_jitter = options.get("retry_jitter", getattr(task, "retry_jitter", True))

    if autoretry_for and not hasattr(task, "_orig_run"):

        @wraps(task.run)
        def run(sub_id: int, msg: dict, **kwargs):
            config = NotificationsConfig.get_solo()
            max_retries = config.notification_delivery_max_retries
            retry_backoff = config.notification_delivery_retry_backoff
            retry_backoff_max = config.notification_delivery_retry_backoff_max

            task.max_retries = max_retries

            try:
                return task._orig_run(sub_id, msg, **kwargs)
            except Ignore:
                # If Ignore signal occurs task shouldn't be retried,
                # even if it suits autoretry_for list
                raise
            except Retry:
                raise
            except autoretry_for as exc:
                if retry_backoff:
                    retry_kwargs["countdown"] = get_exponential_backoff_interval(
                        factor=retry_backoff,
                        retries=task.request.retries,
                        maximum=retry_backoff_max,
                        full_jitter=retry_jitter,
                    )
                # Override max_retries
                if hasattr(task, "override_max_retries"):
                    retry_kwargs["max_retries"] = getattr(
                        task, "override_max_retries", max_retries
                    )

                try:
                    ret = task.retry(exc=exc, **retry_kwargs)
                    # Stop propagation
                    if hasattr(task, "override_max_retries"):
                        delattr(task, "override_max_retries")
                    raise ret
                except autoretry_for:
                    # Final retry failed, send email
                    send_email_to_admins.delay(sub_id, msg["uuid"])
                except Exception:
                    raise

        task._orig_run, task.run = task.run, run


class NotificationException(Exception):
    pass


@app.task
def send_email_to_admins(sub_id: int, notificatie_uuid: UUID) -> None:
    subscription = Abonnement.objects.get(pk=sub_id)
    config = NotificationsConfig.get_solo()

    if not config.failed_notification_admin_recipients:
        return

    parsed = urlparse(config.api_root)
    notifications_changelist = reverse("admin:datamodel_notificatie_changelist")

    body = inspect.cleandoc(
        """
        Notification {notificatie_uuid} to subscriber {sub_uuid} failed.

        See {admin_url} for more info
    """.format(
            notificatie_uuid=notificatie_uuid,
            sub_uuid=subscription.uuid,
            admin_url=f"{parsed.scheme}://{parsed.netloc}{notifications_changelist}",
        )
    )

    send_mail(
        f"Failed notification - {notificatie_uuid}",
        body,
        settings.DEFAULT_FROM_EMAIL,
        config.failed_notification_admin_recipients,
        fail_silently=False,
    )


@app.task
def deliver_message(sub_id: int, msg: dict, **kwargs) -> None:
    """
    send msg to subscriber

    The delivery-result is logged in "NotificatieResponse"
    """
    notificatie_id: int = kwargs.pop("notificatie_id", None)

    try:
        sub = Abonnement.objects.get(pk=sub_id)
    except Abonnement.DoesNotExist:
        logger.warning(
            "Could not retrieve abonnement %d, not delivering message", sub_id
        )
        return

    try:
        response = requests.post(
            sub.callback_url,
            data=json.dumps(msg, cls=DjangoJSONEncoder),
            headers={"Content-Type": "application/json", "Authorization": sub.auth},
        )
        response_init_kwargs = {"response_status": response.status_code}
        if not 200 <= response.status_code < 300:
            exception_message = _(
                "Could not send notification: status {status_code} - {response}"
            ).format(status_code=response.status_code, response=response.text)
            response_init_kwargs["exception"] = exception_message
            raise NotificationException(exception_message)
    except requests.RequestException as e:
        response_init_kwargs = {"exception": str(e)}
        raise
    finally:
        # log of the response of the call
        logger.debug(
            "Notification response for %d, %r: %r", sub_id, msg, response_init_kwargs
        )

        # Only log if a top-level object is provided
        if notificatie_id:
            NotificatieResponse.objects.create(
                notificatie_id=notificatie_id,
                abonnement=sub,
                attempt=kwargs.get("attempt", 1),
                **response_init_kwargs,
            )


add_autoretry_behaviour(
    deliver_message,
    autoretry_for=(
        NotificationException,
        requests.RequestException,
    ),
    retry_jitter=False,
)
