import warnings

from django.conf import settings


def get_domain() -> str:
    """
    Obtain the domain of Open Notificaties according to settings or configuration.
    """
    from django.contrib.sites.models import Site

    if settings.SITE_DOMAIN:
        return settings.SITE_DOMAIN

    warnings.warn(
        "Deriving the domain from the `Sites` configuration will soon be deprecated, "
        "please migrate to the SITE_DOMAIN setting.",
        PendingDeprecationWarning,
    )
    return Site.objects.get_current().domain
