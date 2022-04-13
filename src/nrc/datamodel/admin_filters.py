from django.contrib import admin
from django.db.models import Count, Q
from django.utils.translation import gettext_lazy as _


class BaseFilter(admin.SimpleListFilter):
    title = None
    parameter_name = None
    field_name = None

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        choices = qs.values_list(self.field_name, flat=True).distinct()
        return (
            (
                choice,
                choice,
            )
            for choice in choices
        )

    def queryset(self, request, queryset):
        if not self.value():
            return queryset

        return queryset.filter(**{self.field_name: self.value()})


class ActionFilter(BaseFilter):
    title = _("action")
    parameter_name = "actie"
    field_name = "forwarded_msg__actie"


class ResourceFilter(BaseFilter):
    title = _("resource")
    parameter_name = "resource"
    field_name = "forwarded_msg__resource"


class ResultFilter(admin.SimpleListFilter):
    title = _("result")
    parameter_name = "result"

    def lookups(self, request, model_admin):
        return (
            ("success", _("Success")),
            ("failure", _("Failure")),
        )

    def queryset(self, request, queryset):
        if not self.value():
            return queryset

        annotated = queryset.annotate(
            num_responses=Count(
                "notificatieresponse",
                filter=~Q(notificatieresponse__response_status=204),
            )
        )
        if self.value() == "success":
            return annotated.filter(num_responses=0)
        elif self.value() == "failure":
            return annotated.filter(num_responses__gte=1)
