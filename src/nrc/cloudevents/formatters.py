import json

from django.core.serializers.json import DjangoJSONEncoder

from furl import furl
from rest_framework.request import Request

from nrc.cloudevents.models import CloudEventConfig


def notification_to_cloudevent(notification, request: Request) -> dict:
    config = CloudEventConfig.get_solo()
    base_url = furl(request.build_absolute_uri())

    notification_content = notification.forwarded_msg

    converted_content = {
        "id": notification.id,
        "type": f"nl.vng.zgw.{notification_content['kanaal']}."
        f"{notification_content['resource']}."
        f"{notification_content['actie']}",
        "time": notification_content["aanmaakdatum"].strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "source": f"urn:nld:oin:{config.oin}:systeem:{base_url.host}",
        "data": json.dumps(notification_content, cls=DjangoJSONEncoder),
        "specversion": "1.0",
        "datacontenttype": "application/json",
    }
    kenmerken = notification_content.get("kenmerken")
    if kenmerken:
        for key, value in kenmerken.items():
            converted_content[f"nl.vng.zgw.{key}"] = value

    return converted_content
