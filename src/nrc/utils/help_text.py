from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _


def mark_experimental(text):
    return format_lazy(_("**EXPERIMENTEEL** {}"), text)
