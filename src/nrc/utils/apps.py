from django.apps import AppConfig


class UtilsConfig(AppConfig):
    name = "nrc.utils"

    def ready(self):
        from . import checks, oas_extensions  # noqa
