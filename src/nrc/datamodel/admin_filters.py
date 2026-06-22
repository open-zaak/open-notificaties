from django.contrib import admin
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

        if self.value() == "success":
            return queryset.filter(has_failure=False)
        elif self.value() == "failure":
            return queryset.filter(has_failure=True)
