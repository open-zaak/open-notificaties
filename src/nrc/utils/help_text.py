from typing import TYPE_CHECKING

from django.utils.functional import Promise
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from django.utils.functional import _StrPromise


def mark_experimental(text: str | Promise) -> "_StrPromise":
    return format_lazy(_("**EXPERIMENTEEL** {}"), text)
