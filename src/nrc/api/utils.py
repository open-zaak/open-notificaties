from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer

from nrc.datamodel.models import CloudEvent, Notificatie

from .serializers import CloudEventSerializer, MessageSerializer


def send_notification(obj: Notificatie) -> None:
    MessageSerializer.send_notification(obj)


def send_cloudevent(obj: CloudEvent) -> None:
    CloudEventSerializer.send_cloudevent(obj)


class CloudEventJSONParser(JSONParser):
    media_type = "application/cloudevents+json"


class CloudEventJSONRenderer(JSONRenderer):
    media_type = "application/cloudevents+json"
