import uuid as _uuid

from django.contrib.postgres.fields import ArrayField
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Max
from django.utils.translation import gettext_lazy as _

from djangorestframework_camel_case.util import camelize
from rest_framework.fields import DateTimeField


class Kanaal(models.Model):
    uuid = models.UUIDField(
        unique=True,
        default=_uuid.uuid4,
        help_text=_("Unique resource identifier (UUID4)"),
    )
    naam = models.CharField(
        _("Name"),
        max_length=50,
        unique=True,
        help_text=_(
            'Name of the KANAAL (also called "Exchange") that represents the source.'
        ),
    )
    documentatie_link = models.URLField(
        _("Documentation link"), blank=True, help_text=_("URL to documentation.")
    )
    filters = ArrayField(
        models.CharField(max_length=100),
        verbose_name=_("filters"),
        blank=True,
        default=list,
        help_text=_(
            "List of possible filter attributes for a KANAAL. These filter attributes "
            "can be used when creating an ABONNEMENT"
        ),
    )

    class Meta:
        verbose_name = _("kanaal")
        verbose_name_plural = _("kanalen")

    def __str__(self) -> str:
        return f"{self.naam}"

    def match_filter_names(self, obj_filters: list) -> bool:
        set_kanaal_filters = set(self.filters)
        set_obj_filters = set(obj_filters)
        return (
            set_kanaal_filters <= set_obj_filters
            or set_kanaal_filters >= set_obj_filters
        )


class Abonnement(models.Model):
    uuid = models.UUIDField(
        unique=True,
        default=_uuid.uuid4,
        help_text=_("Unique resource identifier (UUID4)"),
    )
    callback_url = models.URLField(
        _("Callback URL"),
        help_text=_(
            "The URL to which notifications should be sent. This URL should point to an "
            "API that is suitable to receive notifications."
        ),
    )
    auth = models.CharField(
        _("Authorisation header"),
        max_length=1000,
        help_text=_(
            "Content of the Authorization header when sending notifications to "
            'the "Callback URL", for example: Bearer a4daa31...'
        ),
    )
    client_id = models.CharField(
        _("Client ID"),
        max_length=100,
        blank=True,
        help_text=_("Client ID extracted from Auth header"),
    )

    class Meta:
        verbose_name = _("abonnement")
        verbose_name_plural = _("abonnementen")

    def __str__(self) -> str:
        return self.callback_url

    @property
    def kanalen(self):
        return {f.kanaal for f in self.filter_groups.all()}


class FilterGroup(models.Model):
    """
    link between filters, kanalen and abonnementen
    """

    abonnement = models.ForeignKey(
        Abonnement, on_delete=models.CASCADE, related_name="filter_groups"
    )
    kanaal = models.ForeignKey(
        Kanaal, on_delete=models.CASCADE, related_name="filter_groups"
    )

    class Meta:
        verbose_name = _("filter")
        verbose_name_plural = _("filters")

    def match_pattern(self, msg_filters: dict) -> bool:
        abon_filters = {
            abon_filter.key: abon_filter.value for abon_filter in self.filters.all()
        }
        # to ignore case during matching let's camelize abon filter keys
        # msg filters are already camelized in MessageSerializer.validate
        abon_filters = camelize(abon_filters)
        for abon_filter_key, abon_filter_value in abon_filters.items():
            if abon_filter_key in msg_filters:
                if not (
                    abon_filter_value == "*"
                    or abon_filter_value == msg_filters[abon_filter_key]
                ):
                    return False
        return True


class Filter(models.Model):
    key = models.CharField(_("Sleutel"), max_length=100)
    value = models.CharField(_("Waarde"), max_length=1000)
    filter_group = models.ForeignKey(
        FilterGroup, on_delete=models.CASCADE, related_name="filters"
    )

    def __str__(self) -> str:
        return f"{self.key}: {self.value}"

    class Meta:
        ordering = ("id",)
        verbose_name = _("filter-onderdeel")
        verbose_name_plural = _("filter-onderdelen")
        unique_together = ["filter_group", "key"]


class Notificatie(models.Model):
    forwarded_msg = models.JSONField(encoder=DjangoJSONEncoder)
    kanaal = models.ForeignKey(Kanaal, on_delete=models.CASCADE)

    @property
    def last_attempt(self):
        return (
            self.notificatieresponse_set.aggregate(Max("attempt"))["attempt__max"] or 0
        )

    @property
    def created_date(self):
        aanmaakdatum = self.forwarded_msg.get("aanmaakdatum")
        if not aanmaakdatum:
            return None

        return DateTimeField().to_internal_value(aanmaakdatum)

    def __str__(self) -> str:
        return f"Notificatie ({self.kanaal})"


class NotificatieResponse(models.Model):
    notificatie = models.ForeignKey(Notificatie, on_delete=models.CASCADE)
    abonnement = models.ForeignKey(Abonnement, on_delete=models.CASCADE)
    attempt = models.PositiveSmallIntegerField(
        default=1,
        verbose_name=_("attempt"),
        help_text=_("Indicates to which delivery attempt this response belongs."),
    )
    exception = models.CharField(max_length=1000, blank=True)
    response_status = models.IntegerField(null=True)

    def __str__(self) -> str:
        return f"{self.abonnement} {self.response_status or self.exception}"


class CloudEvent(models.Model):
    int_id = models.BigAutoField(
        primary_key=True, serialize=False, verbose_name="ID", help_text=_("internal id")
    )

    id = models.CharField(_("id"), max_length=255, help_text=_("event id"))
    source = models.CharField(_("source"), max_length=255, help_text=_("event source"))
    specversion = models.CharField(
        _("specversion"),
        max_length=50,
        validators=[RegexValidator(regex=r"^(\d+)\.(\d+)")],
        help_text=_("cloudevent spec version used by the event"),
    )
    type = models.CharField(
        _("type"),
        max_length=255,
        help_text=_(
            "event type on which can be subscribed. Example: nl.overheid.zaken.zaak.created"
        ),
    )

    datacontenttype = models.CharField(
        _("datacontent"),
        max_length=255,
        blank=True,
        help_text=_(
            "content type of the (optional) cloudevent data. Example: application/json"
        ),
    )
    dataschema = models.CharField(
        _("dataschema"),
        max_length=255,
        blank=True,
        help_text=_("A schema that the data must follow"),
    )
    subject = models.CharField(
        _("subject"),
        max_length=255,
        blank=True,
        help_text=_("the events subject. Example: an uuid of a zaak"),
    )
    time = models.DateTimeField(
        _("time"),
        blank=True,
        null=True,
        help_text=_("the timestamp of when the event happened"),
    )
    data = models.TextField(
        _("data"),
        blank=True,
        null=True,
        help_text=_("extra data using the format defined in datacontentype"),
    )

    def __str__(self) -> str:
        return f"{self.id}:{self.source}:{self.type}:{self.subject}"

    class Meta:
        unique_together = ["id", "source"]


class CloudEventFilterGroup(models.Model):
    abonnement = models.ForeignKey(
        Abonnement, on_delete=models.CASCADE, related_name="cloudevent_filtergroups"
    )

    type_substring = models.CharField(
        _("type substring"),
        max_length=255,
        help_text=_(
            "a substring of an event type that the subscription will watch for"
        ),
    )

    def __str__(self):
        return self.type_substring
