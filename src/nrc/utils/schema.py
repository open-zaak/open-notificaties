from django.conf import settings

from drf_spectacular.openapi import AutoSchema as _AutoSchema
from vng_api_common.inspectors.view import AutoSchema as oldAutoSchema
from vng_api_common.permissions import BaseAuthRequired, get_required_scopes


class AutoSchema(_AutoSchema):
    def get_auth(self) -> list[dict[str, list[str]]]:
        """
        Return a list of security requirements for this operation.
        `OpenApiAuthenticationExtension` can't be used here since it's tightly coupled
        with DRF authentication classes, and we have none in Open Zaak
        """
        permissions = self.view.get_permissions()
        scope_permissions = [
            perm for perm in permissions if isinstance(perm, BaseAuthRequired)
        ]

        if not scope_permissions:
            return super().get_auth()

        scopes = get_required_scopes(self.view.request, self.view)
        if not scopes:
            return []

        return [{settings.SECURITY_DEFINITION_NAME: [str(scopes)]}]
