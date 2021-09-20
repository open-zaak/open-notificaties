import json
import logging

from django.core.serializers.json import DjangoJSONEncoder

import requests

from nrc.celery import app
from nrc.datamodel.models import Abonnement, NotificatieResponse

logger = logging.getLogger(__name__)


@app.task(ignore_result=True)
def deliver_message(sub_id: int, msg: dict, **kwargs) -> None:
    """
    send msg to subscriber

    The delivery-result is logged in "NotificatieResponse"
    """
    notificatie_id: int = kwargs.pop("notificatie_id", None)

    try:
        sub = Abonnement.objects.get(pk=sub_id)
    except Abonnement.DoesNotExist:
        logger.warning(
            "Could not retrieve abonnement %d, not delivering message", sub_id
        )
        return

    try:
        response = requests.post(
            sub.callback_url,
            data=json.dumps(msg, cls=DjangoJSONEncoder),
            headers={"Content-Type": "application/json", "Authorization": sub.auth},
        )
        response_init_kwargs = {"response_status": response.status_code}
    except requests.exceptions.RequestException as e:
        # log of the response of the call
        response_init_kwargs = {"exception": str(e)}

    logger.debug(
        "Notification response for %d, %r: %r", sub_id, msg, response_init_kwargs
    )

    # Only log if a top-level object is provided
    if notificatie_id:
        NotificatieResponse.objects.create(
            notificatie_id=notificatie_id, abonnement=sub, **response_init_kwargs
        )
