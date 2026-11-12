from django.apps import AppConfig


class UtilsConfig(AppConfig):
    name = "nrc.utils"

    def ready(self) -> None:
        from . import oas_extensions  # noqa
        from ..api import metrics  # noqa
