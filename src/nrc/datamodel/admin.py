from django.contrib import admin, messages
from django.db.models import Count, Q
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from djangorestframework_camel_case.util import underscoreize
from rest_framework.fields import DateTimeField

from nrc.api.serializers import MessageSerializer

from .admin_filters import ActionFilter, ResourceFilter, ResultFilter
from .models import (
    Abonnement,
    Filter,
    FilterGroup,
    Kanaal,
    Notificatie,
    NotificatieResponse,
)


@admin.register(Kanaal)
class KanaalAdmin(admin.ModelAdmin):
    list_display = ("naam", "filters")
    readonly_fields = ("uuid",)


class FilterGroupInline(admin.TabularInline):
    fields = ("kanaal", "get_filters_display", "get_object_actions")
    model = FilterGroup
    readonly_fields = ("get_filters_display", "get_object_actions")
    extra = 0

    def get_filters_display(self, obj):
        return ", ".join([f"{f.key}={f.value}" for f in obj.filters.all()])

    get_filters_display.short_description = _("filters")

    def get_object_actions(self, obj):
        return mark_safe(
            '<a href="{}">{}</a>'.format(
                reverse("admin:datamodel_filtergroup_change", args=(obj.pk,)),
                _("Filters instellen"),
            )
        )

    get_object_actions.short_description = _("acties")


@admin.register(Abonnement)
class AbonnementAdmin(admin.ModelAdmin):
    list_display = ("uuid", "client_id", "callback_url", "get_kanalen_display")
    readonly_fields = ("uuid",)
    inlines = (FilterGroupInline,)

    def get_kanalen_display(self, obj):
        return ", ".join([k.naam for k in obj.kanalen])

    get_kanalen_display.short_description = _("kanalen")


class FilterInline(admin.TabularInline):
    model = Filter
    extra = 0


@admin.register(FilterGroup)
class FilterGroup(admin.ModelAdmin):
    list_display = ("abonnement", "kanaal")
    inlines = (FilterInline,)


@admin.register(NotificatieResponse)
class NotificatieResponseAdmin(admin.ModelAdmin):
    list_display = ("notificatie", "abonnement", "get_result_display")

    list_filter = ("abonnement", "response_status")
    search_fields = ("abonnement",)

    def get_result_display(self, obj):
        return obj.response_status or obj.exception

    get_result_display.short_description = _("result")


class NotificatieResponseInline(admin.TabularInline):
    model = NotificatieResponse


@admin.action(description=_("Re-send the selected notifications to all subscriptions"))
def resend_notifications(modeladmin, request, queryset):
    # Save all the selected notifications via the modeladmin, triggering
    # the notification mechanism
    for notification in queryset:
        modeladmin.save_model(request, notification, None, True)

    messages.add_message(
        request, messages.SUCCESS, _("Selected notifications have been resent")
    )


@admin.register(Notificatie)
class NotificatieAdmin(admin.ModelAdmin):
    list_display = (
        "kanaal",
        "action",
        "resource",
        "result",
        "created_date",
        "forwarded_msg",
    )
    inlines = (NotificatieResponseInline,)
    actions = [resend_notifications]

    list_filter = (
        "kanaal",
        ActionFilter,
        ResourceFilter,
        ResultFilter,
    )
    search_fields = (
        "kanaal__naam",
        "forwarded_msg",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            failed_responses_count=Count(
                "notificatieresponse",
                filter=Q(
                    Q(notificatieresponse__response_status__lt=200)
                    | Q(notificatieresponse__response_status__gte=300)
                ),
            )
        )

    def result(self, obj):
        return not obj.failed_responses_count > 0

    result.short_description = _("Result")
    result.boolean = True

    def action(self, obj):
        return obj.forwarded_msg.get("actie")

    action.short_description = _("Action")

    def resource(self, obj):
        return obj.forwarded_msg.get("resource")

    resource.short_description = _("Resource")

    def created_date(self, obj):
        aanmaakdatum = obj.forwarded_msg.get("aanmaakdatum")
        if not aanmaakdatum:
            return None

        return DateTimeField().to_internal_value(aanmaakdatum)

    created_date.short_description = _("Created date")

    def get_inline_instances(self, request, obj=None):
        # Hide the NotificatieResponseInline when creating a Notification
        return obj and super().get_inline_instances(request, obj) or []

    def save_model(self, request, obj, form, change):
        """
        Given a model instance save it to the database.
        """
        super().save_model(request, obj, form, change)

        # Notification is being resent, delete the existing notificatieresponses
        if change:
            obj.notificatieresponse_set.all().delete()

        transformed = underscoreize(obj.forwarded_msg)
        serializer = MessageSerializer(data={"kanaal": obj.kanaal, **transformed})
        if serializer.is_valid():
            # Save the serializer to send the messages to the subscriptions
            serializer.save(notificatie_id=obj.pk)
