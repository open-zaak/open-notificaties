from datetime import datetime

from django.contrib import admin
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

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

    def result(self, obj):
        all_succeeded = not obj.notificatieresponse_set.filter(~Q(response_status=204))
        return all_succeeded

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

        naive = datetime.fromisoformat(aanmaakdatum.rstrip("Z"))
        return timezone.make_aware(naive, timezone=timezone.utc)

    created_date.short_description = _("Created date")
