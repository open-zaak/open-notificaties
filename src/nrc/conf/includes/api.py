from vng_api_common.conf.api import *  # noqa - imports white-listed

from nrc.utils.apidoc import DESCRIPTION

API_VERSION = "1.0.0"

REST_FRAMEWORK = BASE_REST_FRAMEWORK.copy()
REST_FRAMEWORK["PAGE_SIZE"] = 100
REST_FRAMEWORK.update(
    {
        "DEFAULT_PERMISSION_CLASSES": (
            "vng_api_common.permissions.AuthScopesRequired",
        ),
        "DEFAULT_SCHEMA_CLASS": "nrc.utils.schema.AutoSchema",
    }
)

SECURITY_DEFINITION_NAME = "JWT-Claims"
OPENNOTIFICATIES_API_CONTACT_EMAIL = "support@maykinmedia.nl"
OPENNOTIFICATIES_API_CONTACT_URL = "https://www.maykinmedia.nl"

SPECTACULAR_SETTINGS = {
    "TITLE": "Open Notificaties API",
    "VERSION": API_VERSION,
    "DESCRIPTION": DESCRIPTION,
    "SERVERS": [{"url": "/api/v1"}],
    "LICENSE": {"name": "EUPL 1.2", "url": "https://opensource.org/licenses/EUPL-1.2"},
    "CONTACT": {
        "email": OPENNOTIFICATIES_API_CONTACT_EMAIL,
        "url": OPENNOTIFICATIES_API_CONTACT_URL,
    },
    "SERVE_INCLUDE_SCHEMA": False,
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
        "drf_spectacular.contrib.djangorestframework_camel_case.camelize_serializer_fields",
    ],
    "PREPROCESSING_HOOKS": ["nrc.utils.hooks.preprocess_exclude_endpoints"],
    "SCHEMA_PATH_PREFIX": "/api/v1",
    "SCHEMA_PATH_PREFIX_TRIM": True,
    "COMPONENT_NO_READ_ONLY_REQUIRED": True,
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            SECURITY_DEFINITION_NAME: {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
    },
    "TAGS": [{"name": "abonnement"}, {"name": "kanaal"}, {"name": "notificaties"}],
}

GEMMA_URL_INFORMATIEMODEL_VERSIE = "1.0"

TEST_CALLBACK_AUTH = True

SPEC_CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours
