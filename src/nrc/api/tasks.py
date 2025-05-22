import json

from django.conf import settings
from django.core.management import call_command
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.translation import gettext_lazy as _

import requests
import structlog
from notifications_api_common.autoretry import add_autoretry_behaviour
from structlog.contextvars import bind_contextvars

from nrc.celery import app
from nrc.datamodel.models import Abonnement, NotificatieResponse

from .types import SendNotificationTaskKwargs

logger = structlog.stdlib.get_logger(__name__)


class NotificationException(Exception):
    pass


@app.task(bind=True)
def deliver_message(
    self, sub_id: int, msg: SendNotificationTaskKwargs, **kwargs
) -> None:
    """
    send msg to subscriber

    The delivery-result is logged in "NotificatieResponse"
    """
    notificatie_id: int = kwargs.pop("notificatie_id", None)

    # `autoretry_attempt_number` is the number of times the same task was automatically retried
    # `attempt_number` is the number of tasks that were started for this notification (without counting automatic retries)
    autoretry_attempt_number = self.request.retries + 1
    attempt_number = kwargs.get("attempt", 1)
    bind_contextvars(subscription_pk=sub_id, notification_id=notificatie_id)

    try:
        sub = Abonnement.objects.get(pk=sub_id)
    except Abonnement.DoesNotExist:
        logger.warning("subscription_does_not_exist")
        return

    bind_contextvars(subscription_callback=sub.callback_url)

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
            logger.warning(
                "notification_failed",
                http_status_code=response.status_code,
                autoretry_attempt_number=autoretry_attempt_number,
                attempt_number=attempt_number,
            )
            raise NotificationException(exception_message)
        else:
            logger.info(
                "notification_successful",
                attempt_number=attempt_number,
                autoretry_attempt_number=autoretry_attempt_number,
            )
    except requests.RequestException as e:
        response_init_kwargs = {"exception": str(e)}
        logger.exception(
            "notification_error",
            exc_info=e,
            attempt_number=attempt_number,
            autoretry_attempt_number=autoretry_attempt_number,
        )
        raise
    finally:
        # Only log if a top-level object is provided
        if notificatie_id:
            NotificatieResponse.objects.create(
                notificatie_id=notificatie_id,
                abonnement=sub,
                attempt=attempt_number,
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
