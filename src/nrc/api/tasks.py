import json

from django.core.management import call_command
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.translation import gettext_lazy as _

import requests
import structlog
from notifications_api_common.autoretry import add_autoretry_behaviour
from structlog.contextvars import bind_contextvars
from zgw_consumers.client import build_client
from zgw_consumers.models import Service

from nrc.celery import app
from nrc.datamodel.models import (
    Abonnement,
    CloudEvent,
    CloudEventResponse,
    NotificatieResponse,
)

from .types import CloudEventKwargs, SendNotificationTaskKwargs

logger = structlog.stdlib.get_logger(__name__)


class NotificationException(Exception):
    pass


class CloudEventException(Exception):
    pass


def service_from_abonnement(abonnement: Abonnement) -> Service:
    return Service(
        api_root=abonnement.callback_url,
        auth_type=abonnement.auth_type,
        header_key="Authorization",
        header_value=abonnement.auth,
        client_id=abonnement.client_id,
        secret=abonnement.secret,
        oauth2_token_url=abonnement.oauth2_token_url,
        oauth2_scope=abonnement.oauth2_scope,
    )


@app.task(bind=True)
def deliver_message(
    self, sub_id: int, msg: SendNotificationTaskKwargs, **kwargs
) -> None:
    """
    send msg to subscriber

    The delivery-result is logged in "NotificatieResponse"
    """
    notificatie_id: int = kwargs.pop("notificatie_id", None)

    # `task_attempt_count` is the number of times the same task was automatically retried
    # `notification_attempt_count` is the number of tasks that were started for this notification (without counting automatic retries)
    task_attempt_count = self.request.retries + 1
    notification_attempt_count = kwargs.get("attempt", 1)
    bind_contextvars(subscription_pk=sub_id, notification_id=notificatie_id)

    try:
        sub = Abonnement.objects.get(pk=sub_id)
    except Abonnement.DoesNotExist:
        logger.error("subscription_does_not_exist")
        return

    bind_contextvars(subscription_callback=sub.callback_url)

    try:
        service = service_from_abonnement(sub)
        client = build_client(service)

        response = client.post(
            "",
            data=json.dumps(msg, cls=DjangoJSONEncoder),
            headers={
                "Content-Type": "application/json",
            },
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
                task_attempt_count=task_attempt_count,
                notification_attempt_count=notification_attempt_count,
            )
            raise NotificationException(exception_message)
        else:
            logger.info(
                "notification_successful",
                notification_attempt_count=notification_attempt_count,
                task_attempt_count=task_attempt_count,
            )
    except requests.RequestException as e:
        response_init_kwargs = {"exception": str(e)}
        logger.exception(
            "notification_error",
            exc_info=e,
            notification_attempt_count=notification_attempt_count,
            task_attempt_count=task_attempt_count,
        )
        raise
    finally:
        # Only log if a top-level object is provided
        if notificatie_id:
            NotificatieResponse.objects.create(
                notificatie_id=notificatie_id,
                abonnement=sub,
                attempt=notification_attempt_count,
                **response_init_kwargs,
            )


@app.task(bind=True)
def deliver_cloudevent(
    self, sub_id: int, cloudevent: CloudEventKwargs, **kwargs
) -> None:
    """
    send cloud event to subscriber

    The delivery-result is logged in "CloudEventResponse"
    """
    cloudevent_id: int = kwargs.pop("cloudevent_id", None)
    notificatie_id: int = kwargs.pop("notificatie_id", None)

    # `task_attempt_count` is the number of times the same task was automatically retried
    # `cloudevent_attempt_count` is the number of tasks that were started for this cloud event (without counting automatic retries)
    task_attempt_count = self.request.retries + 1
    cloudevent_attempt_count = kwargs.get("attempt", 1)
    bind_contextvars(subscription_pk=sub_id)

    try:
        sub = Abonnement.objects.get(pk=sub_id)
    except Abonnement.DoesNotExist:
        logger.error("subscription_does_not_exist")
        return

    bind_contextvars(subscription_callback=sub.callback_url)

    try:
        service = service_from_abonnement(sub)
        client = build_client(service)

        response = client.post(
            "",
            data=json.dumps(cloudevent, cls=DjangoJSONEncoder),
            headers={
                "Content-Type": "application/cloudevents+json",
            },
        )
        response_init_kwargs = {"response_status": response.status_code}

        if not 200 <= response.status_code < 300:
            exception_message = _(
                "Could not send couldevent: status {status_code} - {response}"
            ).format(status_code=response.status_code, response=response.text)
            response_init_kwargs["exception"] = exception_message[:1000]
            logger.warning(
                "cloudevent_failed",
                http_status_code=response.status_code,
                task_attempt_count=task_attempt_count,
                cloudevent_attempt_count=cloudevent_attempt_count,
            )
            raise CloudEventException(exception_message)
        else:
            logger.info(
                "cloudevent_successful",
                cloudevent_attempt_count=cloudevent_attempt_count,
                task_attempt_count=task_attempt_count,
            )
    except requests.RequestException as e:
        response_init_kwargs = {"exception": str(e)}
        logger.exception(
            "cloudevent_error",
            exc_info=e,
            cloudevent_attempt_count=cloudevent_attempt_count,
            task_attempt_count=task_attempt_count,
        )
        raise
    finally:
        # Only log if a top-level object is provided
        if cloudevent_id:
            CloudEventResponse.objects.create(
                cloudevent=CloudEvent.objects.get(id=cloudevent_id),
                abonnement=sub,
                attempt=cloudevent_attempt_count,
                **response_init_kwargs,
            )
        elif notificatie_id:
            NotificatieResponse.objects.create(
                notificatie_id=notificatie_id,
                abonnement=sub,
                attempt=cloudevent_attempt_count,
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

add_autoretry_behaviour(
    deliver_cloudevent,
    autoretry_for=(
        CloudEventException,
        requests.RequestException,
    ),
    retry_jitter=False,
)
