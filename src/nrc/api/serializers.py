from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils.translation import gettext_lazy as _

import structlog
from djangorestframework_camel_case.util import camelize, underscoreize
from notifications_api_common.api.serializers import NotificatieSerializer
from rest_framework import fields, serializers
from rest_framework.validators import UniqueValidator
from vng_api_common.validators import IsImmutableValidator, URLValidator

from nrc.api.tasks import deliver_message
from nrc.datamodel.models import Abonnement, Filter, FilterGroup, Kanaal, Notificatie

from .types import NotificationMessage
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

    def _send_to_subs(
        self, msg: NotificationMessage, notificatie: Notificatie | None = None
    ):
        # define subs
        msg_filters = msg["kenmerken"]
        subs = set()
        filter_groups = FilterGroup.objects.filter(kanaal__naam=msg["kanaal"])
        for group in filter_groups:
            if group.match_pattern(msg_filters):
                subs.add(group.abonnement)

        task_kwargs = {}

        # Do not save a new notification, if an existing notification is being scheduled
        if not notificatie and settings.LOG_NOTIFICATIONS_IN_DB:
            # creation of the notification
            kanaal = Kanaal.objects.get(naam=msg["kanaal"])
            notificatie = Notificatie.objects.create(forwarded_msg=msg, kanaal=kanaal)

        if notificatie:
            task_kwargs.update(
                {
                    "notificatie_id": notificatie.id,
                    "attempt": notificatie.last_attempt + 1,
                }
            )

        # send to subs
        for sub in list(subs):
            deliver_message.delay(sub.id, msg, **task_kwargs)

    def create(self, validated_data: NotificationMessage) -> NotificationMessage:
        notificatie: Notificatie | None = validated_data.pop("notificatie", None)

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
            # send to subs
            self._send_to_subs(validated_data, notificatie=notificatie)
        return validated_data

    @classmethod
    def send_notification(cls, obj: Notificatie):
        transformed = underscoreize(obj.forwarded_msg)
        serializer = cls(data={"kanaal": obj.kanaal, **transformed})
        if serializer.is_valid():
            # Save the serializer to send the messages to the subscriptions
            serializer.save(notificatie=obj)
