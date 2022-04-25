from nrc.datamodel.models import Notificatie

from .serializers import MessageSerializer


def send_notification(obj: Notificatie) -> None:
    MessageSerializer.send_notification(obj)
