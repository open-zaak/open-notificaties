from datetime import datetime
from typing import Any, NotRequired, TypedDict

from nrc.datamodel.models import Notificatie


class NotificationMessage(TypedDict):
    aanmaakdatum: str | datetime
    actie: str
    hoofdObject: str
    kanaal: str
    kenmerken: dict[str, Any]
    resource: str
    resourceUrl: str
    notificatie: NotRequired[Notificatie | None]


class SendNotificationTaskKwargs(NotificationMessage):
    notificatie_id: NotRequired[int | None]
