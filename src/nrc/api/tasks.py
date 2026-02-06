import json
import uuid
from contextlib import contextmanager
from datetime import timedelta

from django.conf import settings
from django.core.management import call_command
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import CharField, F, Value
from django.forms import model_to_dict
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

import requests
import structlog
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

    # `task_attempt_count` is the number of times the same task was automatically retried
    # `notification_attempt_count` is the number of tasks that were started for this notification (without counting automatic retries)
    notification_attempt_count = kwargs.get("attempt", 1)
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

    # `cloudevent_attempt_count` is the number of tasks that were started for this cloud event (without counting automatic retries)
    cloudevent_attempt_count = kwargs.get("attempt", 1)
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


def _get_notification_subs(msg) -> set[Abonnement]:
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


@contextmanager
def _context(msg: NotificationMessage | CloudEventKwargs, is_cloudevent: bool = False):
    if is_cloudevent:
        with structlog.contextvars.bound_contextvars(
            id=msg["id"],
            source=msg["source"],
            type=msg["type"],
            subject=msg["subject"],
        ):
            yield
    else:
        with structlog.contextvars.bound_contextvars(
            channel_name=msg["kanaal"],
            resource=msg["resource"],
            resource_url=msg["resourceUrl"],
            main_object_url=msg["hoofdObject"],
            creation_date=msg["aanmaakdatum"],
            action=msg["actie"],
            additional_attributes=msg.get("kenmerken"),
        ):
            yield


def _send_to_subs(
    scheduled_notif: ScheduledNotification, subs, config: NotificationsConfig
):
    task_kwargs = {
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

    with _context(
        scheduled_notif.task_args, scheduled_notif.type == NotificationTypes.cloudevent
    ):
        for sub in list(subs):
            try:
                if sub.send_cloudevents:
                    cloudevent = scheduled_notif.task_args
                    if scheduled_notif.type == NotificationTypes.notification:
                        "Transform cloudevent & add cloudevent log context vars"
                        cloudevent = _transform_to_cloudevent(scheduled_notif.task_args)
                        bind_contextvars(
                            id=cloudevent["id"],
                            source=cloudevent["source"],
                            type=cloudevent["type"],
                            subject=cloudevent["subject"],
                        )

                    deliver_cloudevent(
                        sub,
                        cloudevent,
                        **task_kwargs,
                    )
                else:
                    deliver_message(sub, scheduled_notif.task_args, **task_kwargs)
            except Exception:
                """
                create new ScheduledNotification with the failed subscription.
                """

                if scheduled_notif.attempt >= config.notification_delivery_max_retries:
                    continue

                data = model_to_dict(
                    scheduled_notif, exclude=("id", "notificatie", "cloudevent", "sub")
                )
                data["notificatie_id"] = scheduled_notif.notificatie_id
                data["cloudevent_id"] = scheduled_notif.cloudevent_id
                data["sub_id"] = sub.id
                data["attempt"] += 1
                data["execute_at"] = timezone.now() +  timedelta(get_exponential_backoff_interval(
                    factor=config.notification_delivery_retry_backoff,
                    retries=data["attempt"],
                    maximum=config.notification_delivery_retry_backoff_max,
                    base=config.notification_delivery_base_factor,
                    # full_jitter=retry_jitter, TODO
                ))
                ScheduledNotification.objects.create(**data)


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
def execute_notifications() -> None:
    config = NotificationsConfig.get_solo()

    scheduled_notifications = ScheduledNotification.objects.filter(
        execute_at__lte=timezone.now()
    )

    for scheduled_notif in scheduled_notifications.filter().iterator():
        if scheduled_notif.sub:
            subs = [scheduled_notif.sub]
        else:
            subs = (
                _get_notification_subs(scheduled_notif.task_args)
                if scheduled_notif.type == NotificationTypes.notification
                else _get_cloudevent_subs(scheduled_notif.task_args)
            )

        _send_to_subs(scheduled_notif, subs, config)

        scheduled_notif.delete()
