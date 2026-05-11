from __future__ import annotations

from typing import Any, Callable

import flet as ft

from components.data_classes import (
    PartyState,
    SpqrRatchetState,
    TripleRatchetMessageState,
    TripleRatchetPartyState,
    TripleRatchetSessionState,
)
from modules.base_view import format_key
from modules.messaging.messaging_base_view import (
    SIDE_PANEL_WIDTH,
    build_key_field,
    get_key_tooltip_text,
    is_party_visible,
    build_timeline_column, collect_timeline_items, pqxdh_header_preview, find_bob_pqxdh_header,
    build_timeline_entry, build_received_row_controls, build_pending_row_controls,
    resolve_received_body, resolve_pending_body, append_pqxdh_bootstrap_buttons,
)



def _build_dr_section(
    page: ft.Page,
    dr: PartyState,
    visible: bool,
) -> list[ft.Control]:
    return [
        ft.Text("Double Ratchet", size=13, weight="bold", color=ft.Colors.PRIMARY),
        build_key_field(page, visible, "RK", format_key(dr.RK), "DR root key"),
        build_key_field(page, visible, "CKs", format_key(dr.CKs) if dr.CKs else "None", "DR sending chain key"),
        build_key_field(page, visible, "CKr", format_key(dr.CKr) if dr.CKr else "None", "DR receiving chain key"),
        build_key_field(page, visible, "DHs", dr.DHs.public[-16:] if dr.DHs else "None", "DR ephemeral DH public key"),
        build_key_field(page, visible, "DHr", dr.DHr[-16:] if dr.DHr else "None", "DR remote DH public key"),
        ft.Text(f"Ns={dr.Ns}, Nr={dr.Nr}, PN={dr.PN}", size=12),
    ]


def _build_spqr_section(
    page: ft.Page,
    spqr: SpqrRatchetState | None,
    visible: bool,
) -> list[ft.Control]:
    if spqr is None:
        return [
            ft.Text("SPQR", size=13, weight="bold", color=ft.Colors.SECONDARY),
            ft.Text("Not initialized", color=ft.Colors.OUTLINE),
        ]
    chains = spqr.kdfchains.get(spqr.epoch)
    send_ck = format_key(chains.send.CK) if chains is not None and chains.send is not None else "None"
    recv_ck = format_key(chains.receive.CK) if chains is not None and chains.receive is not None else "None"
    state_name = type(spqr.scka_state.node).__name__ if spqr.scka_state is not None and spqr.scka_state.node is not None else "None"
    return [
        ft.Text("SPQR", size=13, weight="bold", color=ft.Colors.SECONDARY),
        ft.Text(f"Epoch: {spqr.epoch} | Direction: {spqr.direction} | State: {state_name}", size=12),
        build_key_field(page, visible, "RK", format_key(spqr.RK), "SPQR root key"),
        build_key_field(page, visible, "CK_send", send_ck, "SPQR active sending chain key"),
        build_key_field(page, visible, "CK_recv", recv_ck, "SPQR active receiving chain key"),
    ]


def _build_party_panel(
    page: ft.Page,
    party: TripleRatchetPartyState | None,
    party_name: str,
    perspective: str,
    message_input: ft.TextField | None = None,
    on_send: Callable | None = None,
) -> ft.Control:
    if party is None:
        return ft.Container(
            content=ft.Column(
                [ft.Text(party_name, size=18, weight="bold"), ft.Text("Not initialized yet", color=ft.Colors.OUTLINE)],
                spacing=4, tight=True,
            ),
            width=SIDE_PANEL_WIDTH, padding=10,
        )

    visible = is_party_visible(perspective, party_name)

    controls: list[ft.Control] = [
        ft.Text(party_name, size=18, weight="bold"),
        *_build_dr_section(page, party.dr, visible),
        ft.Divider(height=8),
        *_build_spqr_section(page, party.spqr, visible),
    ]

    if message_input is not None and on_send is not None:
        controls.extend([ft.Divider(height=10), message_input, ft.Button("Send", on_click=on_send)])

    return ft.Container(
        content=ft.Column(controls, spacing=4, tight=True),
        width=SIDE_PANEL_WIDTH, padding=10,
    )


def _build_key_history_panel(
    page: ft.Page,
    party: TripleRatchetPartyState | None,
    party_name: str,
    perspective: str,
) -> ft.Control:
    visible = is_party_visible(perspective, party_name)

    panel: list[ft.Control] = [
        ft.Text("Key history", weight="bold", size=14),
    ]

    if party is None:
        panel.append(ft.Text("Not initialized", color=ft.Colors.OUTLINE))
    elif not visible:
        panel.append(ft.Text("Hidden", color=ft.Colors.OUTLINE))
    else:
        # DR key history
        panel.append(ft.Text("DR", weight="bold", size=12, color=ft.Colors.PRIMARY))
        for section_label, events in [("RK", party.dr.key_history.rk_events), ("CKs", party.dr.key_history.cks_events), ("CKr", party.dr.key_history.ckr_events)]:
            panel.append(ft.Text(section_label, weight="bold", size=11))
            for event in reversed(events):
                key_text = event.key_value.hex() if isinstance(event.key_value, bytes) else str(event.key_value)
                label = f"{event.key_type}#{event.key_number} ({event.created_at_step})"
                panel.append(build_key_field(page, visible, label, key_text, get_key_tooltip_text(event)))

        # SPQR key history
        if party.spqr is not None:
            panel.append(ft.Divider(height=6))
            panel.append(ft.Text("SPQR", weight="bold", size=12, color=ft.Colors.SECONDARY))
            for section_label, events in [("RK", party.spqr.key_history.rk_events), ("CKs", party.spqr.key_history.cks_events), ("CKr", party.spqr.key_history.ckr_events)]:
                panel.append(ft.Text(section_label, weight="bold", size=11))
                for event in reversed(events):
                    key_text = event.key_value.hex() if isinstance(event.key_value, bytes) else str(event.key_value)
                    label = f"{event.key_type}#{event.key_number} ({event.created_at_step})"
                    panel.append(build_key_field(page, visible, label, key_text, get_key_tooltip_text(event)))

    return ft.Container(
        content=ft.Column(panel, spacing=2, tight=False, horizontal_alignment=ft.CrossAxisAlignment.START, scroll=ft.ScrollMode.AUTO),
        width=SIDE_PANEL_WIDTH, expand=True, padding=8, border_radius=8,
    )


def _header_text(msg: TripleRatchetMessageState) -> str:
    if msg.header is None:
        return "No header"
    dr = msg.header.dr
    spqr = msg.header.spqr
    return f"DR: dh={dr.dh[-8:]}, pn={dr.pn}, n={dr.n} | SPQR: epoch={spqr.msg.epoch}, type={spqr.msg.msg_type.value}, n={spqr.n}"


def _pending_header_text(header: Any) -> str:
    if header is None:
        return ""
    try:
        dr = header.dr
        spqr = header.spqr
        return f"DR: dh={dr.dh[-8:]}, pn={dr.pn}, n={dr.n} | SPQR: epoch={spqr.msg.epoch}, type={spqr.msg.msg_type.value}, n={spqr.n}"
    except AttributeError:
        return str(header)


def build_timeline(
    session: TripleRatchetSessionState,
    perspective: str,
    page: ft.Page,
    pending_messages: list[dict] | None = None,
    on_receive_pending: Callable | None = None,
    on_show_send_visualization: Callable | None = None,
    on_show_receive_visualization: Callable | None = None,
    on_show_alice_pqxdh_bootstrap: Callable | None = None,
    on_show_bob_pqxdh_bootstrap: Callable | None = None,
) -> ft.Control:
    perspective_key = perspective.lower()
    col = build_timeline_column()
    bob_pqxdh_header = find_bob_pqxdh_header(session.message_log)

    for seq_id, kind, entry in sorted(
        collect_timeline_items(session.message_log, pending_messages),
        key=lambda x: x[0], reverse=True,
    ):
        if kind == "received":
            msg: TripleRatchetMessageState = entry
            body = resolve_received_body(perspective_key, msg.sender, msg.plaintext, msg.decrypted_by_receiver, msg.cipher)
            row_controls = build_received_row_controls(seq_id, msg.sender, msg.receiver, on_show_send_visualization, on_show_receive_visualization)
            col.controls.append(build_timeline_entry(row_controls, _header_text(msg), body, pqxdh_header_preview(getattr(msg, "pqxdh_header", None))))
        else:
            sender = str(entry.get("sender", ""))
            receiver = str(entry.get("receiver", ""))
            body = resolve_pending_body(perspective_key, sender, entry.get("plaintext", b""), entry.get("cipher", b""))
            row_controls = build_pending_row_controls(seq_id, sender, receiver, perspective_key, on_receive_pending, on_show_send_visualization)
            col.controls.append(build_timeline_entry(row_controls, _pending_header_text(entry.get("header")), body, pqxdh_header_preview(entry.get("pqxdh_header")), ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)))

    append_pqxdh_bootstrap_buttons(col, session.alice, session.bob is not None, bob_pqxdh_header, perspective_key, on_show_alice_pqxdh_bootstrap, on_show_bob_pqxdh_bootstrap)
    return col


def build_visual(
    session: TripleRatchetSessionState,
    perspective: str,
    page: ft.Page,
    alice_input: ft.TextField | None = None,
    bob_input: ft.TextField | None = None,
    on_send_alice: Callable | None = None,
    on_send_bob: Callable | None = None,
    pending_messages: list[dict] | None = None,
    on_receive_pending: Callable | None = None,
    on_show_send_visualization: Callable | None = None,
    on_show_receive_visualization: Callable | None = None,
    on_show_alice_pqxdh_bootstrap: Callable | None = None,
    on_show_bob_pqxdh_bootstrap: Callable | None = None,
) -> ft.Control:
    if session.alice is None:
        return ft.Container(
            content=ft.Text("Triple Ratchet session is not initialized from PQXDH yet."), padding=12
        )

    page_height = getattr(page, "height", None)
    if page_height is None and getattr(page, "window", None) is not None:
        page_height = getattr(page.window, "height", None)
    if not isinstance(page_height, (int, float)) or page_height <= 0:
        page_height = 900

    timeline_height = max(280, int(page_height * 0.86))

    alice_panel = _build_party_panel(page, session.alice, "Alice", perspective, alice_input, on_send_alice)
    bob_panel = _build_party_panel(page, session.bob, "Bob", perspective, bob_input, on_send_bob)

    show_key_history = perspective.lower() != "attacker"
    alice_history = _build_key_history_panel(page, session.alice, "Alice", perspective) if show_key_history else None
    bob_history = _build_key_history_panel(page, session.bob, "Bob", perspective) if show_key_history else None

    timeline = build_timeline(
        session, perspective, page,
        pending_messages=pending_messages,
        on_receive_pending=on_receive_pending,
        on_show_send_visualization=on_show_send_visualization,
        on_show_receive_visualization=on_show_receive_visualization,
        on_show_alice_pqxdh_bootstrap=on_show_alice_pqxdh_bootstrap,
        on_show_bob_pqxdh_bootstrap=on_show_bob_pqxdh_bootstrap,
    )

    timeline_container = ft.Container(content=timeline, height=timeline_height, padding=10, clip_behavior=ft.ClipBehavior.HARD_EDGE)

    alice_controls: list[ft.Control] = [alice_panel]
    bob_controls: list[ft.Control] = [bob_panel]
    if show_key_history and alice_history and bob_history:
        alice_controls.extend([ft.Divider(height=10), alice_history])
        bob_controls.extend([ft.Divider(height=10), bob_history])

    return ft.Row(
        controls=[
            ft.Column(alice_controls, expand=True, tight=False),
            ft.Column([timeline_container], expand=True),
            ft.Column(bob_controls, expand=True, tight=False),
        ],
        expand=True,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )
