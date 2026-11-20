from django.conf import settings as django_settings
from django.http import HttpRequest


def settings(request: HttpRequest) -> dict[str, dict[str, object]]:
    public_settings = (
        "GOOGLE_ANALYTICS_ID",
        "ENVIRONMENT",
        "ENVIRONMENT_SHOWN_IN_ADMIN",
        "PROJECT_NAME",
        "SITE_TITLE",
        "API_VERSION",
    )

    return {"settings": {k: getattr(django_settings, k, None) for k in public_settings}}
