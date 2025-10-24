from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers


@extend_schema_field(OpenApiTypes.URI)
class URIField(serializers.CharField):
    pass


@extend_schema_field(OpenApiTypes.URI_REF)
class URIRefField(serializers.CharField):
    pass
