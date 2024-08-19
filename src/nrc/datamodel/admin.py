from django.contrib import admin, messages
from django.db.models import Count, OuterRef, Q, Subquery
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from rest_framework.fields import DateTimeField

from nrc.api.utils import send_notification

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

    @admin.display(description=_("filters"))
    def get_filters_display(self, obj):
        return ", ".join([f"{f.key}={f.value}" for f in obj.filters.all()])

    @admin.display(description=_("acties"))
    def get_object_actions(self, obj):
        return mark_safe(
            '<a href="{}">{}</a>'.format(
                reverse("admin:datamodel_filtergroup_change", args=(obj.pk,)),
                _("Filters instellen"),
            )
        )


@admin.register(Abonnement)
class AbonnementAdmin(admin.ModelAdmin):
    list_display = ("uuid", "client_id", "callback_url", "get_kanalen_display")
    readonly_fields = ("uuid",)
    inlines = (FilterGroupInline,)

    @admin.display(description=_("kanalen"))
    def get_kanalen_display(self, obj):
        return ", ".join([k.naam for k in obj.kanalen])

    def get_deleted_objects(self, objs, request):
        deleted_objects, model_count, perms_needed, protected = (
            super().get_deleted_objects(objs, request)
        )

        # Filter out the NotificationResponses, to avoid an enormous list when deleting
        # an Abonnement
        filtered_deleted_objects = []
        for obj in deleted_objects:
            if isinstance(obj, list):
                filtered_obj = [
                    item
                    for item in obj
                    if "Notificatie response"
                    not in item  # Replace with your related model's name
                ]
                filtered_deleted_objects.append(filtered_obj)
            else:
                filtered_deleted_objects.append(obj)

        return filtered_deleted_objects, model_count, perms_needed, protected


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

    @admin.display(description=_("result"))
    def get_result_display(self, obj):
        return obj.response_status or obj.exception


class NotificatieResponseInline(admin.TabularInline):
    model = NotificatieResponse


@admin.action(description=_("Re-send the selected notifications to all subscriptions"))
def resend_notifications(modeladmin, request, queryset):
    # Save all the selected notifications via the modeladmin, triggering
    # the notification mechanism
    for notification in queryset:
        send_notification(notification)

    messages.add_message(
        request, messages.SUCCESS, _("Selected notifications have been scheduled.")
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
        latest_attempts = (
            NotificatieResponse.objects.filter(notificatie=OuterRef(OuterRef("pk")))
            .order_by("abonnement", "-attempt")
            .distinct("abonnement")
            .values("pk")
        )

        failed_attempts = (
            NotificatieResponse.objects.filter(pk__in=Subquery(latest_attempts))
            .filter(Q(response_status__lt=200) | Q(response_status__gte=300))
            .values("pk")
        )

        qs = qs.annotate(
            failed_responses_count=Count(
                "notificatieresponse",
                filter=Q(notificatieresponse__pk__in=Subquery(failed_attempts)),
            ),
        )
        return qs

    @admin.display(
        description=_("Result"),
        boolean=True,
    )
    def result(self, obj):
        return obj.failed_responses_count == 0

    @admin.display(description=_("Action"))
    def action(self, obj):
        return obj.forwarded_msg.get("actie")

    @admin.display(description=_("Resource"))
    def resource(self, obj):
        return obj.forwarded_msg.get("resource")

    @admin.display(description=_("Created date"))
    def created_date(self, obj):
        aanmaakdatum = obj.forwarded_msg.get("aanmaakdatum")
        if not aanmaakdatum:
            return None

        return DateTimeField().to_internal_value(aanmaakdatum)

    def get_inline_instances(self, request, obj=None):
        # Hide the NotificatieResponseInline when creating a Notification
        if obj is None:
            return []
        return super().get_inline_instances(request, obj)

    def save_model(self, request, obj, form, change):
        """
        Given a model instance save it to the database.
        """
        super().save_model(request, obj, form, change)

        send_notification(obj)
