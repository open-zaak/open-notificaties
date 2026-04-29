import json
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.core.management import call_command
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

import requests
import structlog
import urllib3.exceptions
from celery import group
from notifications_api_common.exponential_backoff import (
    get_exponential_backoff_interval,
)
from notifications_api_common.models import NotificationsConfig
from oauthlib.oauth2.rfc6749.errors import OAuth2Error
from structlog.contextvars import bind_contextvars
from zgw_consumers.client import build_client
from zgw_consumers.models import Service

from nrc.celery import app
from nrc.datamodel.models import (
    Abonnement,
    CloudEvent,
    CloudEventResponse,
    NotificatieResponse,
    NotificationTypes,
    ScheduledNotification,
)

from .types import (
    CloudEventKwargs,
    SendNotificationTaskKwargs,
)

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
        client_certificate=abonnement.client_certificate,
        server_certificate=abonnement.server_certificate,
    )


def deliver_message(sub: Abonnement, msg: SendNotificationTaskKwargs, **kwargs) -> None:
    """
    send msg to subscriber

    The delivery-result is logged in "NotificatieResponse"
    """
    notificatie_id: int = kwargs.pop("notificatie_id", None)

    # `notification_attempt_count` is the amount of times this notification has been attempted
    notification_attempt_count = kwargs.get("attempt", 0) + 1
    bind_contextvars(subscription_pk=sub.id, notification_id=notificatie_id)

    bind_contextvars(subscription_callback=sub.callback_url)

    try:
        service = service_from_abonnement(sub)
        client = build_client(service)

        response = client.post(
            sub.callback_url,
            data=json.dumps(msg, cls=DjangoJSONEncoder),
            headers={
                "Content-Type": "application/json",
            },
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
                notification_attempt_count=notification_attempt_count,
            )
            raise NotificationException(exception_message)
        else:
            logger.info(
                "notification_successful",
                notification_attempt_count=notification_attempt_count,
            )
    except (
        requests.RequestException,
        OAuth2Error,
        urllib3.exceptions.MaxRetryError,
        requests.exceptions.ConnectionError,
        urllib3.exceptions.NameResolutionError,
    ) as e:
        response_init_kwargs = {"exception": str(e)}
        logger.error(
            "notification_error",
            exception=str(e),
            notification_attempt_count=notification_attempt_count,
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


def deliver_cloudevent(sub: Abonnement, cloudevent: CloudEventKwargs, **kwargs) -> None:
    """
    send cloud event to subscriber

    The delivery-result is logged in "CloudEventResponse"
    """
    cloudevent_id: int = kwargs.pop("cloudevent_id", None)
    notificatie_id: int = kwargs.pop("notificatie_id", None)

    # `cloudevent_attempt_count` is the amount of times this cloudevent has been attempted
    cloudevent_attempt_count = kwargs.get("attempt", 0) + 1
    bind_contextvars(subscription_pk=sub.id)

    bind_contextvars(subscription_callback=sub.callback_url)

    try:
        service = service_from_abonnement(sub)
        client = build_client(service)

        response = client.post(
            sub.callback_url,
            data=json.dumps(cloudevent, cls=DjangoJSONEncoder),
            headers={
                "Content-Type": "application/cloudevents+json",
            },
            timeout=settings.NOTIFICATION_REQUESTS_TIMEOUT,
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
                cloudevent_attempt_count=cloudevent_attempt_count,
            )
            raise CloudEventException(exception_message)
        else:
            logger.info(
                "cloudevent_successful",
                cloudevent_attempt_count=cloudevent_attempt_count,
            )
    except (
        requests.RequestException,
        OAuth2Error,
        urllib3.exceptions.MaxRetryError,
        requests.exceptions.ConnectionError,
        urllib3.exceptions.NameResolutionError,
    ) as e:
        response_init_kwargs = {"exception": str(e)}
        logger.error(
            "cloudevent_error",
            exception=str(e),
            cloudevent_attempt_count=cloudevent_attempt_count,
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


@app.task
def send_to_sub(scheduled_notif_id: int, task_kwargs):
    """
    Sends a scheduled notification to a single subscription.

    A cloudevent will always be sent as a cloudevent,
    but a notification can be sent as itself or as a cloudevent
    based on if the subscription is configured to receive cloudevents.
    """
    try:
        scheduled_notif = ScheduledNotification.objects.get(id=scheduled_notif_id)
    except ScheduledNotification.DoesNotExist:
        logger.error("scheduled_notification_does_not_exist")
        return None

    msg = scheduled_notif.task_args

    if scheduled_notif.type == NotificationTypes.notification:
        bind_contextvars(
            channel_name=msg["kanaal"],
            resource=msg["resource"],
            resource_url=msg["resourceUrl"],
            main_object_url=msg["hoofdObject"],
            creation_date=msg["aanmaakdatum"],
            action=msg["actie"],
            additional_attributes=msg.get("kenmerken"),
        )

    if scheduled_notif.sub.send_cloudevents:
        bind_contextvars(
            id=msg["id"],
            source=msg["source"],
            type=msg["type"],
            subject=msg.get("subject"),
        )

    try:
        if scheduled_notif.sub.send_cloudevents:
            deliver_cloudevent(
                scheduled_notif.sub,
                msg,
                **task_kwargs,
            )
        else:
            deliver_message(scheduled_notif.sub, msg, **task_kwargs)
    except Exception:
        _fail_scheduled_notification(scheduled_notif)
    else:
        scheduled_notif.delete()


def _fail_scheduled_notification(scheduled_notif: ScheduledNotification):
    config = NotificationsConfig.get_solo()

    scheduled_notif.execute_after += timedelta(
        seconds=get_exponential_backoff_interval(
            factor=config.notification_delivery_retry_backoff,
            retries=scheduled_notif.attempt,
            maximum=config.notification_delivery_retry_backoff_max,
            base=config.notification_delivery_base_factor,
            full_jitter=False,
        )
    )
    scheduled_notif.attempt += 1
    if scheduled_notif.attempt > config.notification_delivery_max_retries:
        scheduled_notif.delete()
    else:
        scheduled_notif.in_progress = False
        scheduled_notif.save()


def _get_task_kwargs(scheduled_notif: ScheduledNotification) -> dict:
    task_kwargs: dict[str, str | int] = {
        "attempt": scheduled_notif.attempt,
    }
    if scheduled_notif.cloudevent:
        task_kwargs.update(
            {
                "cloudevent_id": scheduled_notif.cloudevent.id,
            }
        )
    if scheduled_notif.notificatie:
        task_kwargs.update(
            {
                "notificatie_id": scheduled_notif.notificatie.id,
            }
        )

    return task_kwargs


@app.task
def execute_notifications() -> None:
    """
    Starts a task for each sub of a notification that should be executed based on 'execute_after'

    If a ScheduledNotification does not have subs saved they will be fetched based on the notification type.
    """
    # celery beat will create multiple execute_notifications if the queue is full (even with expire).
    lock_key = "execute_notifications_lock"
    acquired = cache.add(lock_key, "1", timeout=settings.NOTIFICATION_SEC_INTERVAL - 1)
    if not acquired:
        logger.debug("execute_notifications_blocked")
        return

    config = NotificationsConfig.get_solo()

    cutoff = timezone.now() - timedelta(
        seconds=settings.NOTIFICATION_REQUESTS_TIMEOUT * 10
    )

    waiting_count = ScheduledNotification.objects.filter(
        in_progress=False,
        execute_after__lte=timezone.now(),
    ).count()

    stuck_count = ScheduledNotification.objects.filter(
        in_progress=True, execute_after__lte=cutoff
    ).count()

    in_progress_count = ScheduledNotification.objects.filter(
        in_progress=True, execute_after__gt=cutoff
    ).count()

    limit = max(0, int(settings.NOTIFICATION_LIMIT - in_progress_count))

    # Fetches two types of scheduled notifications:
    # 1. Notifications that are not currently in progress and should be executed
    # 2. Notifications that are currently in progress but have been for a long time (10 * NOTIFICATION_REQUESTS_TIMEOUT) so task probably failed.
    scheduled_notifications = (
        ScheduledNotification.objects.filter(
            Q(
                in_progress=False,
                execute_after__lte=timezone.now(),
            )
            | Q(in_progress=True, execute_after__lte=cutoff)
        )
        .order_by("execute_after", "attempt")[:limit]
        .all()
    )

    notification_ids = list(scheduled_notifications.values_list("id", flat=True))

    # execute_after is updated so that if the scheduled notification failed, the timeout gets added to the time it was actually executed and not when the scheduled notification was created.
    # It is also necessary for scheduled notifications that were stuck (type 2) so that they will not get started again on the next run.
    ScheduledNotification.objects.filter(
        id__in=notification_ids,
    ).update(in_progress=True, execute_after=timezone.now())

    tasks = list()
    for scheduled_notif in ScheduledNotification.objects.filter(
        id__in=notification_ids
    ).iterator():
        if scheduled_notif.attempt > config.notification_delivery_max_retries:
            logger.debug(
                "execute_notifications_max_retries", scheduled_notif=scheduled_notif
            )
            scheduled_notif.delete()
            continue
        else:
            tasks.append(
                send_to_sub.s(scheduled_notif.id, _get_task_kwargs(scheduled_notif))
            )

    if tasks:
        group(tasks)()

    logger.info(
        "executed_notifications",
        waiting=waiting_count,
        stuck=stuck_count,
        in_progress=in_progress_count,
        started=len(tasks),
    )

    cache.delete(lock_key)
