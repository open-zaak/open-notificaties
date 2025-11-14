import uuid

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import CharField, F, Value
from django.forms.models import model_to_dict
from django.utils.translation import gettext_lazy as _

import structlog
from djangorestframework_camel_case.util import camelize, underscoreize
from notifications_api_common.api.serializers import NotificatieSerializer
from rest_framework import fields, serializers
from rest_framework.validators import UniqueValidator
from vng_api_common.utils import get_help_text
from vng_api_common.validators import IsImmutableValidator, URLValidator

from nrc.api.tasks import deliver_cloudevent, deliver_message
from nrc.datamodel.models import (
    Abonnement,
    CloudEvent,
    Filter,
    FilterGroup,
    Kanaal,
    Notificatie,
)

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
        return [Filter(key=k, value=v) for k, v in data.items()]


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


class AbonnementSerializer(serializers.HyperlinkedModelSerializer):
    kanalen = FilterGroupSerializer(
        label=_("kanalen"),
        source="filter_groups",
        many=True,
        help_text=_(
            "Een lijst van kanalen en filters waarop het ABONNEMENT wordt afgenomen."
        ),
    )

    class Meta:
        model = Abonnement
        fields = ("url", "callback_url", "auth", "kanalen")
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "callback_url": {"validators": [CallbackURLAuthValidator()]},
            "auth": {"write_only": True},
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

            # check abonnement filters are consistent with kanaal filters
            abon_filter_names = [f.key for f in group_data["filters"]]
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
            filters = group_data.pop("filters")

            kanaal = Kanaal.objects.get(naam=kanaal_data["naam"])
            filter_group = FilterGroup.objects.create(
                kanaal=kanaal, abonnement=abonnement
            )
            for filter in filters:
                filter.filter_group = filter_group
                filter.save()

    @transaction.atomic
    def create(self, validated_data):
        groups = validated_data.pop("filter_groups")
        abonnement = super().create(validated_data)
        self._create_kanalen_filters(abonnement, groups)
        return abonnement

    @transaction.atomic
    def update(self, instance, validated_data):
        groups = validated_data.pop("filter_groups", [])
        abonnement = super().update(instance, validated_data)

        # in case of update - delete all related kanalen and filters
        # and create them from request data
        abonnement.filter_groups.all().delete()

        self._create_kanalen_filters(abonnement, groups)
        return abonnement


class MessageSerializer(NotificatieSerializer):
    # TODO move to package
    source = serializers.CharField(
        label=_("source"),
        max_length=100,
        help_text=_(
            "De identifier van de oorsprong van de notificatie, een systeem of organisatie."
        ),
    )

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

    def _get_subs(self, msg) -> set[Abonnement]:
        # define subs
        msg_filters = msg["kenmerken"]
        subs = set()
        filter_groups = FilterGroup.objects.filter(
            kanaal__naam=msg["kanaal"],
        )
        for group in filter_groups:
            if group.match_pattern(msg_filters):
                subs.add(group.abonnement)

        return subs

    def _send_to_subs(
        self,
        subs: set[Abonnement],
        msg: NotificationMessage,
        notificatie: Notificatie | None = None,
    ):
        task_kwargs = {}

        if notificatie:
            task_kwargs.update(
                {
                    "notificatie_id": notificatie.id,
                    "attempt": notificatie.last_attempt + 1,
                }
            )

        with structlog.contextvars.bound_contextvars(
            channel_name=msg["kanaal"],
            resource=msg["resource"],
            resource_url=msg["resourceUrl"],
            main_object_url=msg["hoofdObject"],
            # Explicitly use `strftime` because `isoformat` adds a `+00:00` suffix
            creation_date=msg["aanmaakdatum"].strftime("%Y-%m-%dT%H:%M:%SZ"),
            action=msg["actie"],
            additional_attributes=msg.get("kenmerken"),
        ):
            logger.info("notification_received")

            # send to subs
            for sub in list(subs):
                deliver_message.delay(sub.id, msg, **task_kwargs)

    def _transform_to_cloudevent(self, notif: NotificationMessage) -> CloudEventKwargs:
        return {
            "id": str(uuid.uuid4()),
            "source": notif["source"],
            "specversion": "1.0",  # TODO setting?
            "type": f"{notif['kanaal']}:{notif['resource']}:{notif['actie']}",
            "datacontenttype": "application/json",
            "subject": notif["resourceUrl"],
            "time": notif["aanmaakdatum"].strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": {
                **notif["kenmerken"],
                "hoofdObject": notif["hoofdObject"],
            },
        }

    def create(self, validated_data: NotificationMessage) -> NotificationMessage:
        if settings.LOG_NOTIFICATIONS_IN_DB:
            # creation of the notification
            kanaal = Kanaal.objects.get(naam=validated_data["kanaal"])
            notificatie = Notificatie.objects.create(
                forwarded_msg=validated_data, kanaal=kanaal
            )
        else:
            notificatie = None

        subs = self._get_subs(validated_data)
        self._send_to_subs(
            {sub for sub in subs if not sub.send_cloudevents},
            validated_data,
            notificatie,
        )

        # Send notificatie as cloudevent.
        CloudEventSerializer.send_to_subs(
            {sub for sub in subs if sub.send_cloudevents},
            self._transform_to_cloudevent(validated_data),
            notificatie=notificatie,
        )
        return validated_data

    def update(
        self, instance, validated_data: NotificationMessage
    ) -> NotificationMessage:
        subs = self._get_subs(validated_data)
        self._send_to_subs(
            {sub for sub in subs if not sub.send_cloudevents},
            validated_data,
            instance,
        )

        # Send notificatie as cloudevent.
        CloudEventSerializer.send_to_subs(
            {sub for sub in subs if sub.send_cloudevents},
            self._transform_to_cloudevent(validated_data),
            notificatie=instance,
        )
        return validated_data

    @classmethod
    def send_notification(cls, obj: Notificatie):
        transformed = underscoreize(obj.forwarded_msg)
        serializer = cls(instance=obj, data={"kanaal": obj.kanaal, **transformed})
        if serializer.is_valid():
            # Save the serializer to send the messages to the subscriptions
            serializer.save()


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

    def _get_subs(self, msg: CloudEventKwargs) -> set[Abonnement]:
        return set(
            Abonnement.objects.prefetch_related("cloudevent_filtergroups")
            .annotate(type=Value(msg["type"], CharField()))
            .filter(
                type__contains=F("cloudevent_filtergroups__type_substring"),
                send_cloudevents=True,
            )
            .distinct()
        )

    @classmethod
    def send_to_subs(
        cls,
        subs: set[Abonnement],
        msg: CloudEventKwargs,
        cloudevent: CloudEvent | None = None,
        notificatie: Notificatie | None = None,
    ):
        task_kwargs = {}
        if cloudevent:
            task_kwargs.update(
                {
                    "cloudevent_id": cloudevent.id,
                    "attempt": cloudevent.last_attempt + 1,
                }
            )
        elif notificatie:  # TODO
            task_kwargs.update(
                {
                    "notificatie_id": notificatie.id,
                    "attempt": notificatie.last_attempt + 1,
                }
            )

        with structlog.contextvars.bound_contextvars(
            id=msg["id"],
            source=msg["source"],
            type=msg["type"],
            subject=msg["subject"],
        ):
            logger.info("cloudevent_received")

            for sub in subs:
                deliver_cloudevent.delay(sub.id, msg, **task_kwargs)

    def create(self, validated_data: CloudEventKwargs) -> CloudEventKwargs:
        if settings.LOG_NOTIFICATIONS_IN_DB:
            if validated_data.get("data", False) is None:
                cloudevent = super().create(validated_data | {"data": "null"})
            else:
                cloudevent = super().create(validated_data)
        else:
            cloudevent = None

        subs = self._get_subs(validated_data)
        self.send_to_subs(subs, validated_data, cloudevent=cloudevent)
        return validated_data

    def update(self, instance, validated_data: CloudEventKwargs) -> CloudEventKwargs:
        subs = self._get_subs(validated_data)
        self.send_to_subs(subs, validated_data, cloudevent=instance)
        return validated_data

    @classmethod
    def send_cloudevent(cls, obj: CloudEvent):
        serializer = cls(instance=obj, data=model_to_dict(obj))
        if serializer.is_valid():
            # Save the serializer to send the messages to the subscriptions
            serializer.save()
