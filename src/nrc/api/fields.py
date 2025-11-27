import json

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers


@extend_schema_field(OpenApiTypes.URI)
class URIField(serializers.CharField):
    pass


@extend_schema_field(
    {
        "type": "string",
        "format": "uri-reference",
        "example": "https://openzaak.maykin.nl",
    }
)
class URIRefField(serializers.CharField):
    pass


@extend_schema_field(OpenApiTypes.ANY)
class JSONOrStringField(serializers.Field):
    def to_internal_value(self, data):
        return data

    def to_representation(self, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except ValueError:
                pass
        return value
