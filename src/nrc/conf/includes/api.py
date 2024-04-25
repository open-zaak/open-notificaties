from vng_api_common.conf.api import *  # noqa - imports white-listed

API_VERSION = "1.0.0"

REST_FRAMEWORK = BASE_REST_FRAMEWORK.copy()
REST_FRAMEWORK["PAGE_SIZE"] = 100
REST_FRAMEWORK.update(
    {
        "DEFAULT_PERMISSION_CLASSES": (
            "vng_api_common.permissions.AuthScopesRequired",
        ),
        "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    }
)

SECURITY_DEFINITION_NAME = "JWT-Claims"

SPECTACULAR_SETTINGS = {
    "TITLE": "Open Notificaties API",
}


# todo REMOVE
SWAGGER_SETTINGS = BASE_SWAGGER_SETTINGS.copy()
SWAGGER_SETTINGS.update(
    {
        "DEFAULT_INFO": "nrc.api.schema.info",
        "SECURITY_DEFINITIONS": {
            SECURITY_DEFINITION_NAME: {
                # OAS 3.0
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                # not official...
                # 'scopes': {},  # TODO: set up registry that's filled in later...
                # Swagger 2.0
                # 'name': 'Authorization',
                # 'in': 'header'
                # 'type': 'apiKey',
            }
        },
    }
)

GEMMA_URL_INFORMATIEMODEL_VERSIE = "1.0"

TEST_CALLBACK_AUTH = True

SPEC_CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours

# URLs for documentation that are shown in API schema
DOCUMENTATION_URL = "https://vng-realisatie.github.io/gemma-zaken/standaard/"
OPENNOTIFS_DOCS_URL = "https://open-notificaties.readthedocs.io/en/latest/"
OPENNOTIFS_GITHUB_URL = "https://github.com/open-zaak/open-notificaties"
ZGW_URL = "https://www.vngrealisatie.nl/producten/api-standaarden-zaakgericht-werken"
