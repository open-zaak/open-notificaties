from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from vng_api_common.models import JWTSecret

from nrc.utils.auth import generate_jwt

admin.site.unregister(JWTSecret)


@admin.register(JWTSecret)
class JWTSecretAdmin(admin.ModelAdmin):

    list_display = ("identifier",)

    readonly_fields = ("get_jwt",)

    @admin.display(description="jwt")
    def get_jwt(self, obj):
        if obj.identifier and obj.secret:
            jwt = generate_jwt(
                obj.identifier, obj.secret, obj.identifier, obj.identifier
            )
            return format_html(
                '<code class="jwt">{val}</code><p>{hint}</p>',
                val=jwt,
                hint=_("Gebruik het JWT-token nooit direct in een applicatie."),
            )
        return ""
