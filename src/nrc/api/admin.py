from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from vng_api_common.authorizations.utils import generate_jwt
from vng_api_common.models import JWTSecret

admin.site.unregister(JWTSecret)


@admin.register(JWTSecret)
class JWTSecretAdmin(admin.ModelAdmin):

    list_display = ("identifier",)

    readonly_fields = ("get_jwt",)

    @admin.display(description="jwt")
    def get_jwt(self, obj: JWTSecret):
        if obj.identifier and obj.secret:
            return format_html(
                '<code class="jwt">{val}</code><p>{hint}</p>',
                val=generate_jwt(obj.identifier, obj.secret, "", ""),
                hint=_("Gebruik het JWT-token nooit direct in een applicatie."),
            )
        return ""
