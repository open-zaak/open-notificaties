import json
import logging

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.translation import gettext_lazy as _

import requests

from nrc.celery import app
from nrc.datamodel.models import Abonnement, NotificatieResponse

logger = logging.getLogger(__name__)


class NotificationException(Exception):
    pass


@app.task(
    autoretry_for=(
        NotificationException,
        requests.exceptions.RequestException,
    ),
    max_retries=settings.CELERY_MAX_RETRIES,
    retry_backoff=settings.CELERY_RETRY_BACKOFF,
    retry_backoff_max=settings.CELERY_RETRY_BACKOFF_MAX,
)
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
        if response.status_code != 204:
            exception_message = _(
                "Could not send notification: status {status_code} - {response}"
            ).format(status_code=response.status_code, response=response.text)
            response_init_kwargs["exception"] = exception_message
            raise NotificationException(exception_message)
    except requests.exceptions.RequestException as e:
        response_init_kwargs = {"exception": str(e)}
        raise e
    finally:
        # log of the response of the call
        logger.debug(
            "Notification response for %d, %r: %r", sub_id, msg, response_init_kwargs
        )

        # Only log if a top-level object is provided
        if notificatie_id:
            NotificatieResponse.objects.create(
                notificatie_id=notificatie_id, abonnement=sub, **response_init_kwargs
            )
