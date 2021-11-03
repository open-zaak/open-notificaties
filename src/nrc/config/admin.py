from django.contrib import admin
from solo.admin import SingletonModelAdmin
from .models import CloudEventConfig


@admin.register(CloudEventConfig)
class CloudEventConfigAdmin(SingletonModelAdmin):
    list_display = ("oin",)
