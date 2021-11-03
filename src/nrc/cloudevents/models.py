from django.db import models
from django.utils.translation import ugettext_lazy as _

from solo.models import SingletonModel


class CloudEventConfig(SingletonModel):
    """
    Configure values required for sending cloud events
    """

    oin = models.CharField(
        _("OIN"),
        help_text=_("The OIN that will be used in the source field of the cloudevent."),
        max_length=20,
    )

    class Meta:
        verbose_name = _("CloudEvents configuration")
        verbose_name_plural = _("CloudEvents configurations")
