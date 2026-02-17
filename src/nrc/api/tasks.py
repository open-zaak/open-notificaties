import json
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.management import call_command
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import CharField, F, Value
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

import requests
import structlog
from celery import chord
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
    CloudEventFilterGroup,
    CloudEventResponse,
    FilterGroup,
    NotificatieResponse,
    NotificationTypes,
    ScheduledNotification,
)

from .types import CloudEventKwargs, NotificationMessage, SendNotificationTaskKwargs

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
    except (requests.RequestException, OAuth2Error) as e:
        response_init_kwargs = {"exception": str(e)}
        logger.exception(
            "notification_error",
            exc_info=e,
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
    except (requests.RequestException, OAuth2Error) as e:
        response_init_kwargs = {"exception": str(e)}
        logger.exception(
            "cloudevent_error",
            exc_info=e,
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
def handle_result(subs: set[int], scheduled_notif_id: int):
    try:
        scheduled_notif = ScheduledNotification.objects.get(id=scheduled_notif_id)
    except ScheduledNotification.DoesNotExist:
        logger.error("scheduled_notification_does_not_exist")
        return

    failed_subs = [sub for sub in subs if sub is not None]

    if failed_subs:
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
        scheduled_notif.subs.set(failed_subs)
        scheduled_notif.save()
    else:
        scheduled_notif.delete()


def _transform_to_cloudevent(notif: NotificationMessage) -> CloudEventKwargs:
    return {
        "id": str(uuid.uuid4()),
        "source": notif["source"],
        "specversion": settings.CLOUDEVENT_SPECVERSION,
        "type": f"nl.overheid.{notif['kanaal']}.{notif['resource']}.{notif['actie']}",
        "datacontenttype": "application/json",
        "subject": notif["resourceUrl"].rsplit("/", 1)[
            1
        ],  # TODO the whole resourceUrl would make the location of the resource clearer.
        "time": notif["aanmaakdatum"],
        "data": {
            **notif["kenmerken"],
            "hoofdObject": notif["hoofdObject"],
        },
    }


@app.task
def send_to_sub(sub_id: int, scheduled_notif_id: int, task_kwargs):  # TODO rename
    try:
        scheduled_notif = ScheduledNotification.objects.get(id=scheduled_notif_id)
    except ScheduledNotification.DoesNotExist:
        logger.error("scheduled_notification_does_not_exist")
        return None

    try:
        sub = Abonnement.objects.get(id=sub_id)
    except ScheduledNotification.DoesNotExist:
        logger.error("subscription_does_not_exist")
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

    if sub.send_cloudevents:
        if scheduled_notif.type == NotificationTypes.notification:
            msg = _transform_to_cloudevent(msg)

        bind_contextvars(
            id=msg["id"],
            source=msg["source"],
            type=msg["type"],
            subject=msg.get("subject"),
        )

    try:
        if sub.send_cloudevents:
            deliver_cloudevent(
                sub,
                msg,
                **task_kwargs,
            )
        else:
            deliver_message(sub, msg, **task_kwargs)
    except Exception:
        return sub_id

    return None


def _get_notification_subs(msg: NotificationMessage) -> set[Abonnement]:
    # define subs
    msg_filters = msg["kenmerken"]
    subs = set()
    filter_groups = (
        FilterGroup.objects.filter(
            kanaal__naam=msg["kanaal"],
        )
        .select_related("abonnement")
        .prefetch_related("filters")
    )
    for group in filter_groups:
        if group.match_pattern(msg_filters):
            subs.add(group.abonnement)

    return subs


def _get_cloudevent_subs(msg: CloudEventKwargs) -> set[Abonnement]:
    msg_filters = msg.get("data", {})
    subs: set[Abonnement] = set()
    filter_groups = (
        CloudEventFilterGroup.objects.select_related("abonnement")
        .prefetch_related("filters")
        .annotate(type=Value(msg["type"], CharField()))
        .filter(type__contains=F("type_substring"), abonnement__send_cloudevents=True)
    )
    for group in filter_groups:
        if group.match_pattern(msg_filters):
            subs.add(group.abonnement)
    return subs


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
    config = NotificationsConfig.get_solo()

    scheduled_notifications = ScheduledNotification.objects.filter(
        execute_after__lte=timezone.now()
    )
    for scheduled_notif in scheduled_notifications.iterator():
        if scheduled_notif.attempt > (config.notification_delivery_max_retries + 1):
            scheduled_notif.delete()
            continue

        if scheduled_notif.subs.exists():
            subs = set(scheduled_notif.subs.all())
        else:
            subs = (
                _get_notification_subs(scheduled_notif.task_args)
                if scheduled_notif.type == NotificationTypes.notification
                else _get_cloudevent_subs(scheduled_notif.task_args)
            )

        task_kwargs = _get_task_kwargs(scheduled_notif)

        chord(
            send_to_sub.s(sub.id, scheduled_notif.id, task_kwargs) for sub in list(subs)
        )(handle_result.s(scheduled_notif.id))
