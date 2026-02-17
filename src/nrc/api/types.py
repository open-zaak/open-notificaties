from datetime import datetime
from typing import Any, NotRequired, TypedDict

from nrc.datamodel.models import Notificatie


class _BaseNotificationMessage(TypedDict):
    aanmaakdatum: datetime | str
    source: str
    actie: str
    hoofdObject: str
    kanaal: str
    kenmerken: dict[str, Any]
    resource: str
    resourceUrl: str
    notificatie: NotRequired[Notificatie | None]


class NotificationMessage(_BaseNotificationMessage):
    aanmaakdatum: datetime


class NotificationMessageKwargs(_BaseNotificationMessage):
    aanmaakdatum: str


class SendNotificationTaskKwargs(NotificationMessage):
    notificatie_id: NotRequired[int | None]


class CloudEventKwargs(TypedDict):
    id: str
    source: str
    specversion: str
    type: str
    datacontenttype: NotRequired[str]
    dataschema: NotRequired[str]
    subject: NotRequired[str]
    time: NotRequired[str]
    data: NotRequired[str | dict]
