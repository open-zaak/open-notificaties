from django.utils.translation import gettext_lazy as _

import jwt
from rest_framework.exceptions import PermissionDenied
from vng_api_common.middleware import (
    AuthMiddleware as _AuthMiddleware,
    JWTAuth as _JWTAuth,
)


class JWTAuth(_JWTAuth):
    @property
    def payload(self):
        try:
            return super().payload
        except jwt.PyJWTError as exc:
            raise PermissionDenied(
                _("JWT did not validate, try checking the `nbf` and `iat`"),
                code="jwt-{err}".format(err=type(exc).__name__.lower()),
            )


class AuthMiddleware(_AuthMiddleware):
    def extract_jwt_payload(self, request):
        authorization = request.headers.get(self.header, "")
        prefix = f"{self.auth_type} "
        if authorization.startswith(prefix):
            # grab the actual token
            encoded = authorization[len(prefix) :]
        else:
            encoded = None

        request.jwt_auth = JWTAuth(encoded)
