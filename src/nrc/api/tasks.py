import json
import logging

from django.conf import settings
from django.core.management import call_command
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.translation import gettext_lazy as _

import requests
from notifications_api_common.autoretry import add_autoretry_behaviour

from nrc.celery import app
from nrc.datamodel.models import Abonnement, NotificatieResponse

logger = logging.getLogger(__name__)


class NotificationException(Exception):
    pass


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
            timeout=settings.NOTIFICATION_REQUESTS_TIMEOUT,
        )
        response_init_kwargs = {"response_status": response.status_code}
        if not 200 <= response.status_code < 300:
            exception_message = _(
                "Could not send notification: status {status_code} - {response}"
            ).format(status_code=response.status_code, response=response.text)
            response_init_kwargs["exception"] = exception_message[:1000]
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


@app.task
def clean_old_notifications() -> None:
    """
    cleans up old "Notificatie" and "NotificatieResponse"
    """
    call_command("clean_old_notifications")


add_autoretry_behaviour(
    deliver_message,
    autoretry_for=(
        NotificationException,
        requests.RequestException,
    ),
    retry_jitter=False,
)
