from __future__ import annotations

from typing import Any, Callable

import flet as ft

from components.data_classes import DoubleRatchetState
from modules.messaging.double_ratchet.attacker_dashboard.logic import (
    collect_attacker_secret_options,
    compute_implied_known_ids,
)


def build_attacker_dashboard(
    page: ft.Page,
    session: DoubleRatchetState,
    pending_messages: list[dict[str, Any]],
    compromised_secrets: dict[str, dict[str, Any]],
    set_compromised_secrets: Callable[[dict[str, dict[str, Any]]], None],
    refresh_callback: Callable[[], None],
    session_ad: bytes = b"",
) -> ft.Control:
    options = collect_attacker_secret_options(session)
    option_ids = {item["id"] for item in options}
    active_selected = {key_id for key_id in compromised_secrets if key_id in option_ids}
    options_by_id = {item["id"]: item for item in options}

    party_names = {session.initializer.name, session.responder.name}
    opposite_party_by_name = {
        session.initializer.name: session.responder.name,
        session.responder.name: session.initializer.name,
    }

    def _option_owner(label: str) -> str:
        first_token = label.split(" ", 1)[0] if label else "Other"
        return first_token if first_token in party_names else "Other"

    def _extract_key_number(item: dict[str, Any]) -> int:
        key_id = str(item.get("id", ""))
        try:
            return int(key_id.rsplit(":", 1)[1])
        except (IndexError, ValueError):
            return 0

    def _layout_label(item: dict[str, Any]) -> str:
        kind = item.get("kind")
        number = _extract_key_number(item)
        if kind == "dh_private":
            return f"DH#{number}"
        if kind == "rk":
            return f"RK#{number}"
        if kind == "cks":
            return f"CKs#{number}"
        if kind == "ckr":
            return f"CKr#{number}"
        if kind == "ck":
            direction = item.get("direction")
            if direction == "send":
                return f"CKs#{number}"
            if direction == "recv":
                return f"CKr#{number}"
            return f"CK#{number}"
        return str(item.get("label", ""))

    def _key_sort(item: dict[str, Any]) -> tuple[int, int]:
        kind_rank = {
            "dh_private": 0,
            "rk": 1,
            "cks": 2,
            "ckr": 3,
            "ck": 4,
            "mk": 3,
        }.get(str(item.get("kind", "")), 99)
        return (kind_rank, _extract_key_number(item))

    implied_known_ids = compute_implied_known_ids(
        options=options,
        options_by_id=options_by_id,
        opposite_party_by_name=opposite_party_by_name,
        session=session,
        pending_messages=pending_messages,
        session_ad=session_ad,
        selected_ids=active_selected,
    )

    def _checkbox_cell(item: dict[str, Any]) -> ft.Control:
        is_selected = item["id"] in active_selected
        is_implied = item["id"] in implied_known_ids and not is_selected
        cell_bg = ft.Colors.AMBER_50 if is_implied else None
        cell_border_color = ft.Colors.AMBER_500 if is_implied else ft.Colors.TRANSPARENT
        tooltip_text = str(item.get("context", ""))
        if is_implied:
            implied_note = "Implied by selected secrets"
            tooltip_text = f"{implied_note}\n\n{tooltip_text}" if tooltip_text else implied_note

        return ft.Container(
            content=ft.Checkbox(
                label=_layout_label(item),
                value=is_selected,
                on_change=lambda e, kid=item["id"]: update_selection(kid, bool(e.control.value)),
            ),
            tooltip=tooltip_text,
            width=140,
            padding=ft.Padding.only(right=6),
            bgcolor=cell_bg,
            border=ft.Border.all(color=cell_border_color),
            border_radius=6,
        )

    def update_selection(key_id: str, checked: bool) -> None:
        updated = dict(compromised_secrets)
        if checked:
            option = options_by_id.get(key_id)
            if option is None:
                return
            updated[key_id] = dict(option)
        else:
            updated.pop(key_id, None)
        set_compromised_secrets(updated)
        refresh_callback()
        page.update()

    def select_all(e) -> None:
        set_compromised_secrets({item["id"]: dict(item) for item in options})
        refresh_callback()
        page.update()

    def clear_all(e) -> None:
        set_compromised_secrets({})
        refresh_callback()
        page.update()

    def _owner_items(owner: str) -> list[dict[str, Any]]:
        return [
            item
            for item in options
            if _option_owner(str(item.get("label", ""))) == owner
        ]

    def select_owner(owner: str) -> None:
        updated = dict(compromised_secrets)
        for item in _owner_items(owner):
            item_id = str(item.get("id", ""))
            if item_id:
                updated[item_id] = dict(item)
        set_compromised_secrets(updated)
        refresh_callback()
        page.update()

    key_selector_controls: list[ft.Control] = [
        ft.Row(
            controls=[
                ft.Text("Compromised secrets", weight="bold"),
                ft.Row(
                    controls=[
                        ft.Text("Amber highlight = implied known key", size=11, color=ft.Colors.AMBER_800),
                        ft.TextButton("Select all", on_click=select_all),
                        ft.TextButton("Clear", on_click=clear_all),
                    ],
                    spacing=6,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
    ]

    if not options:
        key_selector_controls.append(ft.Text("No selectable secrets are available yet."))
    else:
        grouped: dict[str, list[dict[str, Any]]] = {session.initializer.name: [], session.responder.name: [], "Other": []}
        for item in options:
            grouped.setdefault(_option_owner(item["label"]), []).append(item)

        for owner in (session.initializer.name, session.responder.name, "Other"):
            owner_items = grouped.get(owner, [])
            if not owner_items:
                continue

            key_selector_controls.append(ft.Divider(height=8))
            key_selector_controls.append(
                ft.Row(
                    controls=[
                        ft.Text(owner, weight="bold", size=12),
                        ft.TextButton("Select all", on_click=lambda e, section=owner: select_owner(section)),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )
            )

            if owner in {session.initializer.name, session.responder.name}:
                dh_and_rk = sorted(
                    [item for item in owner_items if item.get("kind") in {"dh_private", "rk"}],
                    key=_key_sort,
                )
                ck_s = sorted(
                    [
                        item
                        for item in owner_items
                        if item.get("kind") == "cks" or (item.get("kind") == "ck" and item.get("direction") == "send")
                    ],
                    key=_key_sort,
                )
                ck_r = sorted(
                    [
                        item
                        for item in owner_items
                        if item.get("kind") == "ckr" or (item.get("kind") == "ck" and item.get("direction") == "recv")
                    ],
                    key=_key_sort,
                )

                for row_items in (dh_and_rk, ck_s, ck_r):
                    if not row_items:
                        continue
                    key_selector_controls.append(
                        ft.Row(
                            controls=[_checkbox_cell(item) for item in row_items],
                            wrap=True,
                            vertical_alignment=ft.CrossAxisAlignment.START,
                        )
                    )
            else:
                other_items = sorted(owner_items, key=_key_sort)
                key_selector_controls.append(
                    ft.Row(
                        controls=[_checkbox_cell(item) for item in other_items],
                        wrap=True,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    )
                )

    return ft.Container(
        content=ft.Column(
            controls=key_selector_controls,
            scroll=ft.ScrollMode.AUTO,
            spacing=4,
        ),
        expand=True,
        padding=10,
        border=ft.Border.all(color=ft.Colors.OUTLINE),
        border_radius=8,
    )
