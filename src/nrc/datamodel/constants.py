from django.db import models
from django.utils.translation import gettext_lazy as _


class AuthTypes(models.TextChoices):
    no_auth = "no_auth", _("No authorization")
    api_key = "api_key", _("API key")
    zgw = "zgw", _("ZGW client_id + secret")
    oauth2_client_credentials = (
        "oauth2_client_credentials",
        _("OAuth2 client credentials flow"),
    )
