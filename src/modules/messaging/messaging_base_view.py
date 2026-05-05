from __future__ import annotations

import flet as ft

from modules.base_view import last_n_chars, make_copy_handler
from modules.tooltip_helpers import build_tooltip_text


def is_party_visible(perspective: str, party_name: str) -> bool:
    return perspective == "global" or perspective.lower() == party_name.lower()


def build_key_field(
    page: ft.Page,
    visible: bool,
    label: str,
    full_value: str,
    tooltip_message: str = "",
    copy_value: str | None = None,
) -> ft.Control:
    """Build a formatted key field with tooltip, matching double_ratchet style."""
    display = last_n_chars(full_value, 8) if visible else "Hidden"
    cv = copy_value if copy_value is not None else full_value
    return build_tooltip_text(
        label,
        display,
        tooltip_message,
        full_value=full_value if visible else None,
        on_click=make_copy_handler(page, label, cv) if visible else None,
    )


__all__ = ["is_party_visible", "build_key_field"]
FAMILY_ID = "messaging"
