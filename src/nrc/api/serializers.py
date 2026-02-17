from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.forms.models import model_to_dict
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

import structlog
from djangorestframework_camel_case.util import camelize, underscoreize
from notifications_api_common.api.serializers import NotificatieSerializer
from rest_framework import fields, serializers
from rest_framework.validators import UniqueValidator
from vng_api_common.utils import get_help_text
from vng_api_common.validators import IsImmutableValidator, URLValidator

from nrc.datamodel.models import (
    Abonnement,
    CloudEvent,
    CloudEventFilter,
    CloudEventFilterGroup,
    Filter,
    FilterGroup,
    Kanaal,
    Notificatie,
    NotificationTypes,
    ScheduledNotification,
)

from ..utils.help_text import mark_experimental
from .fields import JSONOrStringField, URIField, URIRefField
from .types import CloudEventKwargs, NotificationMessage
from .validators import CallbackURLAuthValidator, CallbackURLValidator

logger = structlog.stdlib.get_logger(__name__)


class FiltersField(fields.DictField):
    child = fields.CharField(
        label=_("kenmerk"),
        max_length=1000,
        help_text=_("Een waarde behorende bij de sleutel."),
    )

    def to_representation(self, instance):
        qs = instance.all()
        return dict(qs.values_list("key", "value"))

    def to_internal_value(self, data):
        return [self.Meta.model(key=k, value=v) for k, v in data.items()]

    class Meta:
        model = Filter


class CloudEventFiltersField(FiltersField):
    class Meta:
        model = CloudEventFilter


class KanaalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kanaal
        fields = ("url", "naam", "documentatie_link", "filters")
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "naam": {
                "validators": [
                    UniqueValidator(queryset=Kanaal.objects.all()),
                    IsImmutableValidator(),
                ]
            },
            "documentatie_link": {"required": False, "validators": [URLValidator()]},
            "filters": {"required": False},
        }


class FilterGroupSerializer(serializers.ModelSerializer):
    naam = serializers.CharField(
        source="kanaal.naam",
        help_text=_(
            "De naam van het KANAAL (`KANAAL.naam`) waarop een "
            "abonnement is of wordt genomen."
        ),
    )
    filters = FiltersField(
        required=False,
        help_text=_(
            "Map van kenmerken (sleutel/waarde) waarop notificaties "
            "gefilterd worden. Alleen notificaties waarvan de "
            "kenmerken voldoen aan het filter worden doorgestuurd naar "
            "de afnemer van het ABONNEMENT."
        ),
    )

    class Meta:
        model = FilterGroup
        fields = ("filters", "naam")

        # delete unique validator for naam field - process it manually in AbonnementSerializer.create()
        extra_kwargs = {"naam": {"validators": []}}


class CloudEventFilterGroupSerializer(serializers.ModelSerializer):
    filters = CloudEventFiltersField(
        required=False,
        help_text=_(
            "Map van kenmerken (sleutel/waarde) waarop notificaties "
            "gefilterd worden. Alleen notificaties waarvan de "
            "kenmerken voldoen aan het filter worden doorgestuurd naar "
            "de afnemer van het ABONNEMENT."
        ),
    )

    class Meta:
        model = CloudEventFilterGroup
        fields = (
            "type_substring",
            "filters",
        )


class AbonnementSerializer(serializers.HyperlinkedModelSerializer):
    kanalen = FilterGroupSerializer(
        source="filter_groups",
        many=True,
        help_text=_(
            "Een lijst van kanalen en filters waarop het ABONNEMENT wordt afgenomen."
        ),
        required=False,
    )

    cloudevent_filters = CloudEventFilterGroupSerializer(
        source="cloudevent_filtergroups",
        many=True,
        help_text=mark_experimental(
            "Een lijst van cloudevent type substrings waarop gefilterd wordt"
        ),
        required=False,
    )

    class Meta:
        model = Abonnement
        fields = (
            "url",
            "callback_url",
            "auth",
            "kanalen",
            "send_cloudevents",
            "cloudevent_filters",
        )
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "callback_url": {"validators": [CallbackURLAuthValidator()]},
            "auth": {"write_only": True, "required": True},
        }
        validators = [CallbackURLValidator("callback_url", "auth")]

    def validate(self, attrs):
        validated_attrs = super().validate(attrs)
        for group_data in validated_attrs.get("filter_groups", []):
            kanaal_data = group_data["kanaal"]

            # check kanaal exists
            try:
                kanaal = Kanaal.objects.get(naam=kanaal_data["naam"])
            except ObjectDoesNotExist:
                raise serializers.ValidationError(
                    {"naam": _("Kanaal met deze naam bestaat niet.")},
                    code="kanaal_naam",
                )

            if not (filters := group_data.get("filters")):
                continue

            # check abonnement filters are consistent with kanaal filters
            abon_filter_names = [f.key for f in filters]
            if not kanaal.match_filter_names(abon_filter_names):
                raise serializers.ValidationError(
                    {
                        "filters": _(
                            "abonnement filters aren't consistent with kanaal filters"
                        )
                    },
                    code="inconsistent-abonnement-filters",
                )

        return validated_attrs

    def _create_kanalen_filters(self, abonnement, validated_data):
        for group_data in validated_data:
            kanaal_data = group_data.pop("kanaal")
            filters: list[Filter] = group_data.pop("filters", [])

            kanaal = Kanaal.objects.get(naam=kanaal_data["naam"])
            filter_group = FilterGroup.objects.create(
                kanaal=kanaal, abonnement=abonnement
            )
            for filter in filters:
                filter.filter_group = filter_group
                filter.save()

    def _create_cloudevent_filters(self, abonnement, validated_data):
        for ce_filter in validated_data:
            filters = ce_filter.pop("filters", {})

            filter_group = CloudEventFilterGroup.objects.create(
                abonnement=abonnement, type_substring=ce_filter["type_substring"]
            )
            for filter in filters:
                filter.cloud_event_filter_group = filter_group
                filter.save()

    @transaction.atomic
    def create(self, validated_data):
        groups = validated_data.pop("filter_groups", [])
        cloudevent_filters = validated_data.pop("cloudevent_filtergroups", [])
        abonnement = super().create(validated_data)
        self._create_kanalen_filters(abonnement, groups)
        self._create_cloudevent_filters(abonnement, cloudevent_filters)
        return abonnement

    @transaction.atomic
    def update(self, instance, validated_data):
        groups = validated_data.pop("filter_groups", [])
        cloudevent_filters = validated_data.pop("cloudevent_filtergroups", [])
        abonnement = super().update(instance, validated_data)

        # in case of update - delete all related kanalen and filters
        # and create them from request data
        abonnement.filter_groups.all().delete()
        abonnement.cloudevent_filtergroups.all().delete()

        self._create_kanalen_filters(abonnement, groups)
        self._create_cloudevent_filters(abonnement, cloudevent_filters)
        return abonnement


class MessageSerializer(NotificatieSerializer):
    def validate(self, attrs):
        validated_attrs = super().validate(attrs)
        # check if exchange exists
        try:
            kanaal = Kanaal.objects.get(naam=validated_attrs["kanaal"])
        except ObjectDoesNotExist:
            raise serializers.ValidationError(
                {"kanaal": _("Kanaal met deze naam bestaat niet.")},
                code="message_kanaal",
            )

        # check if msg kenmerken are consistent with kanaal filters
        kenmerken_names = list(validated_attrs["kenmerken"].keys())
        if not kanaal.match_filter_names(kenmerken_names):
            raise serializers.ValidationError(
                {"kenmerken": _("Kenmerken aren't consistent with kanaal filters")},
                code="kenmerken_inconsistent",
            )

        # ensure we're still camelCasing
        return camelize(validated_attrs)

    def _get_cloudevent_subs(self, msg) -> set[Abonnement]:
        """
        Fetches the notification subs that want cloudevents.
        """
        # define subs
        msg_filters = msg["kenmerken"]
        subs = set()
        filter_groups = (
            FilterGroup.objects.filter(
                kanaal__naam=msg["kanaal"], abonnement__send_cloudevents=True
            )
            .select_related("abonnement")
            .prefetch_related("filters")
        )
        for group in filter_groups:
            if group.match_pattern(msg_filters):
                subs.add(group.abonnement)

        return subs

    def _schedule_notification(
        self,
        msg: NotificationMessage,
        notificatie: Notificatie | None = None,
    ):
        ScheduledNotification.objects.create(
            type=NotificationTypes.notification,
            task_args=msg,
            execute_after=timezone.now(),
            attempt=0,
            notificatie=notificatie,
        )

    def _validate_source(self, validated_data) -> None:
        if not validated_data.get("source"):
            if any(self._get_cloudevent_subs(validated_data)):
                logger.error(
                    "no_notification_source",
                    action=validated_data["actie"],
                    channel_name=validated_data["kanaal"],
                    resource=validated_data["resource"],
                    resource_url=validated_data["resourceUrl"],
                )
                raise serializers.ValidationError(
                    _(
                        "Notification does not have a source, cannot transform message to a cloudevent"
                    )
                )

    def create(self, validated_data: NotificationMessage) -> NotificationMessage:
        notificatie: Notificatie | None = validated_data.pop("notificatie", None)

        if not notificatie and settings.LOG_NOTIFICATIONS_IN_DB:
            # creation of the notification
            kanaal = Kanaal.objects.get(naam=validated_data["kanaal"])
            notificatie = Notificatie.objects.create(
                forwarded_msg=validated_data, kanaal=kanaal
            )

        self._validate_source(validated_data)

        with structlog.contextvars.bound_contextvars(
            channel_name=validated_data["kanaal"],
            resource=validated_data["resource"],
            resource_url=validated_data["resourceUrl"],
            main_object_url=validated_data["hoofdObject"],
            # Explicitly use `strftime` because `isoformat` adds a `+00:00` suffix
            creation_date=validated_data["aanmaakdatum"].strftime("%Y-%m-%dT%H:%M:%SZ"),
            action=validated_data["actie"],
            additional_attributes=validated_data.get("kenmerken"),
        ):
            logger.info("notification_received")
        self._schedule_notification(validated_data, notificatie)
        return validated_data

    @classmethod
    def send_notification(cls, obj: Notificatie):
        transformed = underscoreize(obj.forwarded_msg)
        serializer = cls(data={"kanaal": obj.kanaal, **transformed})
        if serializer.is_valid():
            # Save the serializer to send the messages to the subscriptions
            serializer.save(notificatie=obj)


class CloudEventSerializer(serializers.ModelSerializer):
    source = URIRefField(help_text=get_help_text("datamodel.CloudEvent", "source"))
    dataschema = URIField(
        help_text=get_help_text("datamodel.CloudEvent", "dataschema"),
        required=False,
        allow_blank=True,
    )
    data = JSONOrStringField(
        help_text=get_help_text("datamodel.CloudEvent", "data"),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = CloudEvent
        fields = "__all__"

    def _schedule_cloudevent(
        self,
        msg: CloudEventKwargs,
        cloudevent: CloudEvent | None = None,
    ):
        ScheduledNotification.objects.create(
            type=NotificationTypes.cloudevent,
            task_args=msg,
            execute_after=timezone.now(),
            attempt=0,
            cloudevent=cloudevent,
        )

    def _log(self, validated_data: CloudEventKwargs) -> None:
        with structlog.contextvars.bound_contextvars(
            id=validated_data["id"],
            source=validated_data["source"],
            type=validated_data["type"],
            subject=validated_data.get("subject"),
        ):
            logger.info("cloudevent_received")

    def create(self, validated_data: CloudEventKwargs) -> CloudEventKwargs:
        if settings.LOG_NOTIFICATIONS_IN_DB:
            cloudevent = super().create(validated_data)
        else:
            cloudevent = None

        self._log(validated_data)
        self._schedule_cloudevent(validated_data, cloudevent)
        return validated_data

    def update(self, instance, validated_data: CloudEventKwargs) -> CloudEventKwargs:
        self._log(validated_data)
        self._schedule_cloudevent(validated_data, instance)
        return validated_data

    @classmethod
    def send_cloudevent(cls, obj: CloudEvent):
        serializer = cls(instance=obj, data=model_to_dict(obj))
        if serializer.is_valid():
            # Save the serializer to send the messages to the subscriptions
            serializer.save()
