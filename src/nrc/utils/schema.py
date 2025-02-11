import logging

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from drf_spectacular.openapi import AutoSchema as _AutoSchema
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes
from rest_framework import exceptions, mixins, serializers
from vng_api_common.constants import VERSION_HEADER
from vng_api_common.permissions import BaseAuthRequired, get_required_scopes
from vng_api_common.schema import DEFAULT_ACTION_ERRORS, HTTP_STATUS_CODE_TITLES
from vng_api_common.serializers import FoutSerializer, ValidatieFoutSerializer
from vng_api_common.views import ERROR_CONTENT_TYPE

logger = logging.getLogger(__name__)


class AutoSchema(_AutoSchema):
    def get_auth(self) -> list[dict[str, list[str]]]:
        """
        Return a list of security requirements for this operation.
        `OpenApiAuthenticationExtension` can't be used here since it's tightly coupled
        with DRF authentication classes
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

    def get_operation_id(self):
        """
        Use view basename as a base for operation_id
        """
        if hasattr(self.view, "basename"):
            basename = self.view.basename
            action = self.view.action
            # make compatible with old OAS
            if action == "destroy":
                action = "delete"
            elif action == "retrieve":
                action = "read"

            return f"{basename}_{action}"
        return super().get_operation_id()

    def get_error_responses(self) -> dict[int, type[serializers.Serializer]]:
        """
        return dictionary of error codes and correspondent error serializers
        - define status codes based on exceptions for each endpoint
        - define error serializers based on status code
        """

        # only supports viewsets
        action = getattr(self.view, "action")
        if not action:
            return {}

        # define status codes for the action based on potential exceptions
        # general errors
        general_klasses = DEFAULT_ACTION_ERRORS.get(action)
        if general_klasses is None:
            logger.debug("Unknown action %s, no default error responses added")
            return {}

        exception_klasses = general_klasses[:]
        # add geo and validation errors
        has_validation_errors = action == "list" or any(
            issubclass(klass, exceptions.ValidationError) for klass in exception_klasses
        )
        if has_validation_errors:
            exception_klasses.append(exceptions.ValidationError)

        status_codes = sorted({e.status_code for e in exception_klasses})

        # choose serializer based on the status code
        responses = {}
        for status_code in status_codes:
            error_serializer = (
                ValidatieFoutSerializer
                if status_code == exceptions.ValidationError.status_code
                else FoutSerializer
            )
            responses[status_code] = error_serializer

        return responses

    def get_response_serializers(
        self,
    ) -> dict[int, type[serializers.Serializer] | None]:
        """append error serializers"""
        response_serializers = super().get_response_serializers()

        if self.method == "DELETE":
            status_code = 204
            serializer = None
        elif self._is_create_operation():
            status_code = 201
            serializer = response_serializers
        else:
            status_code = 200
            serializer = response_serializers

        responses = {
            status_code: serializer,
            **self.get_error_responses(),
        }
        return responses

    def _get_response_for_code(
        self, serializer, status_code, media_types=None, direction="response"
    ):
        """
        choose media types and set descriptions
        """
        if not media_types:
            if int(status_code) >= 400:
                media_types = [ERROR_CONTENT_TYPE]
            else:
                media_types = ["application/json"]

        response = super()._get_response_for_code(
            serializer, status_code, media_types, direction
        )

        # add description based on the status code
        if not response.get("description"):
            response["description"] = HTTP_STATUS_CODE_TITLES.get(int(status_code), "")
        return response

    def get_override_parameters(self):
        """Add request and response headers"""
        version_headers = self.get_version_headers()
        content_type_headers = self.get_content_type_headers()
        location_headers = self.get_location_headers()
        return version_headers + content_type_headers + location_headers

    def get_version_headers(self) -> list[OpenApiParameter]:
        return [
            OpenApiParameter(
                name=VERSION_HEADER,
                type=str,
                location=OpenApiParameter.HEADER,
                description=_(
                    "Geeft een specifieke API-versie aan in de context van "
                    "een specifieke aanroep. Voorbeeld: 1.2.1."
                ),
                response=True,
            )
        ]

    def get_content_type_headers(self) -> list[OpenApiParameter]:
        if self.method not in ["POST", "PUT", "PATCH"]:
            return []

        return [
            OpenApiParameter(
                name="Content-Type",
                type=str,
                location=OpenApiParameter.HEADER,
                description=_("Content type of the request body."),
                enum=["application/json"],
                required=True,
            )
        ]

    def get_location_headers(self) -> list[OpenApiParameter]:
        # only for CreateModelMixin - exclude notificaties endpoint
        if isinstance(self.view, mixins.CreateModelMixin):
            return [
                OpenApiParameter(
                    name="Location",
                    type=OpenApiTypes.URI,
                    location=OpenApiParameter.HEADER,
                    description=_("URL waar de resource leeft."),
                    response=[201],
                ),
            ]

        return []
