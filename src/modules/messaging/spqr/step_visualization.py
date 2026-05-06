from __future__ import annotations

from typing import Any, Callable

import flet as ft

from components.data_classes import SpqrHeader, SpqrRatchetState
from modules.base_step_visualization import (
    page_size as _shared_page_size,
    to_text as _shared_to_text,
    with_tooltip as _shared_with_tooltip,
)
from modules.tooltip_helpers import get_tooltip_messages


def _to_text(value: Any) -> str:
    return _shared_to_text(value)


def _page_size(page: ft.Page) -> tuple[int, int]:
    return _shared_page_size(page)


def _with_tooltip(control: ft.Control, message: str | None, full_value: Any = None) -> ft.Control:
    return _shared_with_tooltip(control, message, full_value)


def _preview_text(value: Any, limit: int = 48) -> str:
    text = _to_text(value)
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."


def _last_n_chars(value: Any, count: int = 8) -> str:
    text = _to_text(value)
    if len(text) <= count:
        return text
    return text[-count:]


def _format_plaintext(value: Any) -> str | Any:
    """Convert plaintext bytes to a readable string for visualization."""
    if value is None:
        return None
    if isinstance(value, list) and all(isinstance(item, int) and 0 <= item <= 255 for item in value):
        value = bytes(value)
    if isinstance(value, (bytes, bytearray)):
        try:
            return value.decode('utf-8', errors='replace')
        except Exception:
            return value
    return value


def _var_node(label: str, value: Any, tip_key: str) -> ft.Control:
    label_key = label.lower()
    display_value = _to_text(value) if "plaintext" in label_key else _last_n_chars(value, 8)
    return _flow_node(
        label,
        display_value,
        width=220,
        tooltip=_tt(tip_key),
        full_value=value,
    )


def _tt(key: str) -> str:
    tooltips = get_tooltip_messages("spqr")
    message = tooltips.get(key, "")
    return message if message else "Tooltip missing in src/assets/tooltips.json"


def _function_node(label: str, tip_key: str, full_value: Any = None, value: Any = None) -> ft.Control:
    return _flow_node(
        label,
        circle=True,
        width=220,
        height=70,
        tooltip=_tt(tip_key),
        full_value=full_value,
    )


def _flow_node(
    label: str,
    value: str | None = None,
    circle: bool = False,
    width: int = 260,
    height: int = 90,
    tooltip: str | None = None,
    full_value: Any = None,
    bgcolor: str | None = None,
    text_color: str | None = None,
    border_color: str | None = None,
) -> ft.Control:
    controls = [ft.Text(label, weight="bold", text_align=ft.TextAlign.CENTER, color=text_color)]
    if value:
        controls.append(ft.Text(value, text_align=ft.TextAlign.CENTER, color=text_color))

    node = ft.Container(
        content=ft.Column(
            controls=controls,
            spacing=4,
            tight=True,
            expand=True,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        width=width,
        height=height,
        padding=10,
        bgcolor=bgcolor,
        border=ft.Border.all(color=border_color) if border_color is not None else ft.Border.all(),
        border_radius=45 if circle else 8,
    )
    return _with_tooltip(node, tooltip, full_value)


def _flow_row(items: list[tuple[str, str | None]], tooltip: str | None = None) -> ft.Control:
    return ft.Row(
        controls=[
            _flow_node(label, value, width=220, tooltip=tooltip)
            for label, value in items
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=16,
        wrap=True,
    )


def _state_row(
    label: str,
    value: str,
    tooltip: str | None = None,
    full_value: Any = None,
    highlight: bool = False,
) -> ft.Control:
    row = ft.Row(
        controls=[
            ft.Text(
                f"{label}:",
                weight="bold",
                color=ft.Colors.ON_PRIMARY_CONTAINER if highlight else None,
            ),
            ft.Text(
                value,
                weight=ft.FontWeight.W_600 if highlight else None,
                color=ft.Colors.ON_PRIMARY_CONTAINER if highlight else None,
            ),
        ],
        spacing=8,
        wrap=True,
    )
    row_control: ft.Control = row
    if highlight:
        row_control = ft.Container(
            content=row,
            padding=ft.Padding.symmetric(horizontal=6, vertical=2),
            border_radius=6,
            bgcolor=ft.Colors.PRIMARY_CONTAINER,
        )
    return _with_tooltip(
        ft.Container(
            content=row_control,
            padding=ft.Padding.symmetric(horizontal=4, vertical=2),
            border_radius=6,
            height=32,
        ),
        tooltip,
        full_value,
    )


def _party_state_panel(
    title: str,
    rows: list[tuple[str, str, str | None, Any]],
    tooltip: str | None = None,
    highlight_labels: set[str] | None = None,
) -> ft.Control:
    highlighted = highlight_labels or set()
    panel = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(title, size=16, weight="bold"),
                *[
                    _state_row(
                        label,
                        value,
                        row_tooltip,
                        full_value,
                        highlight=label in highlighted,
                    )
                    for label, value, row_tooltip, full_value in rows
                ],
            ],
            spacing=4,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        ),
        width=420,
        padding=10,
        border=ft.Border.all(),
        border_radius=8,
    )
    return _with_tooltip(panel, tooltip)


def _show_step_dialog(
    page: ft.Page,
    dialog_title: str,
    steps: list[dict[str, Any]],
    on_close: Callable[[], None] | None = None,
) -> None:
    resize_event_name = "on_resized" if hasattr(page, "on_resized") else "on_resize"
    previous_resize_handler = getattr(page, resize_event_name, None)

    current_step = {"index": 0}
    progress_text = ft.Text()
    step_container = ft.Container(width=620)

    def apply_responsive_dialog_size() -> None:
        page_width, page_height = _page_size(page)
        content_width = max(620, min(980, int(page_width * 0.82)))
        content_height = max(360, min(760, int(page_height * 0.72)))

        dialog_content.width = content_width
        dialog_content.height = content_height
        step_container.width = max(520, content_width - 80)

    def on_page_resized(e) -> None:
        apply_responsive_dialog_size()
        if callable(previous_resize_handler):
            previous_resize_handler(e)
        if dialog.open:
            page.update()

    def close_dialog(e) -> None:
        dialog.open = False
        if getattr(page, resize_event_name, None) == on_page_resized:
            setattr(page, resize_event_name, previous_resize_handler)
        page.update()
        if on_close is not None:
            on_close()

    def render_current_step() -> None:
        index = current_step["index"]
        step = steps[index]
        progress_text.value = f"Step {index + 1}/{len(steps)}"
        step_container.content = step["control"]
        previous_button.disabled = index == 0
        next_button.text = "Finish" if index == len(steps) - 1 else "Next"

    def on_previous(e) -> None:
        if current_step["index"] <= 0:
            return
        current_step["index"] -= 1
        render_current_step()
        page.update()

    def on_next(e) -> None:
        if current_step["index"] >= len(steps) - 1:
            close_dialog(e)
            return
        current_step["index"] += 1
        render_current_step()
        page.update()

    previous_button = ft.TextButton("Previous", on_click=on_previous)
    next_button = ft.TextButton("Next", on_click=on_next)

    dialog_content = ft.Container(
        content=ft.Column(
            controls=[
                progress_text,
                ft.Text("Click Next to continue to the following step."),
                ft.Row(controls=[step_container], alignment=ft.MainAxisAlignment.CENTER),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
            spacing=8,
            scroll=ft.ScrollMode.ALWAYS,
        ),
        width=700,
        height=460,
    )

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text(dialog_title),
        content=dialog_content,
        actions=[previous_button, next_button, ft.TextButton("Close", on_click=close_dialog)],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    apply_responsive_dialog_size()
    setattr(page, resize_event_name, on_page_resized)
    render_current_step()
    page.overlay.append(dialog)
    dialog.open = True
    page.update()


def _header_preview(header: SpqrHeader | None) -> str:
    if header is None:
        return "No header"
    return f"epoch={header.msg.epoch}, type={header.msg.msg_type.value}, n={header.n}"


def _before_after_rows(snapshot: dict[str, Any], tooltips: dict[str, str]) -> list[tuple[str, str, str | None, Any]]:
    return [
        (
            "State",
            str(snapshot.get("state", snapshot.get("node", "Unknown"))),
            tooltips.get("spqr_step_state", tooltips.get("spqr_step_node", "")),
            snapshot.get("state", snapshot.get("node", "Unknown")),
        ),
        ("Epoch", str(snapshot.get("epoch", "-")), tooltips.get("spqr_step_epoch", ""), snapshot.get("epoch", "-")),
        ("Direction", str(snapshot.get("direction", "-")), tooltips.get("spqr_step_direction", ""), snapshot.get("direction", "-")),
        ("RK", str(snapshot.get("rk_tail", "None")), tooltips.get("spqr_step_rk", ""), snapshot.get("rk_tail", "None")),
        (
            "CKs",
            str(snapshot.get("send_ck_tail", "None")),
            tooltips.get("spqr_step_send_ck", ""),
            snapshot.get("send_ck_tail", "None"),
        ),
        (
            "CKr",
            str(snapshot.get("recv_ck_tail", "None")),
            tooltips.get("spqr_step_recv_ck", ""),
            snapshot.get("recv_ck_tail", "None"),
        ),
    ]


def _send_keys_unsampled(step_data: dict[str, Any], tooltips: dict[str, str]) -> list[dict[str, Any]]:

    header: SpqrHeader | None = step_data.get("header")
    after = step_data.get("after") if isinstance(step_data.get("after"), dict) else {}
    after_node = after.get("scka_node") if isinstance(after.get("scka_node"), dict) else {}

    dk = after_node.get("dk")
    ek_header = after_node.get("ek_header")
    ek_vector = after_node.get("ek_vector")
    header_encoder = after_node.get("header_encoder") if isinstance(after_node.get("header_encoder"), dict) else {}

    ek_header_bytes = bytes(ek_header) if isinstance(ek_header, (bytes, bytearray)) else None
    header_encoder_message = header_encoder.get("message") if isinstance(header_encoder.get("message"), (bytes, bytearray)) else None
    header_bytes = bytes(header_encoder_message[:64]) if isinstance(header_encoder_message, (bytes, bytearray)) and len(header_encoder_message) >= 64 else None
    if header_bytes is None:
        header_bytes = ek_header_bytes
    mac = bytes(header_encoder_message[64:]) if isinstance(header_encoder_message, (bytes, bytearray)) and len(header_encoder_message) > 64 else None
    header_with_mac = bytes(header_encoder_message) if isinstance(header_encoder_message, (bytes, bytearray)) else None
    if header_with_mac is None and isinstance(header_bytes, bytes) and isinstance(mac, bytes):
        header_with_mac = header_bytes + mac

    chunk = header.msg.data if header is not None else None
    msg_epoch = header.msg.epoch if header is not None else after.get("epoch")
    sending_epoch = msg_epoch - 1 if isinstance(msg_epoch, int) else "self.epoch - 1"

    return [
        {
            "title": "Generate key material",
            "control": ft.Column(
                controls=[
                    ft.Text("Generate key material", weight="bold"),
                    _function_node(
                        "IncrementalKEM.KeyGen",
                        "spqr_step_keygen_fn",
                        full_value="Outputs: dk, ek_header, ek_vector",
                    ),
                    ft.Text("↓", size=24),
                    ft.Row(
                        controls=[
                            _var_node("dk", dk, "spqr_step_dk"),
                            _var_node("ek_header", ek_header, "spqr_step_ek_header"),
                            _var_node("ek_vector", ek_vector, "spqr_step_ek_vector"),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=16,
                        wrap=True,
                    ),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        },
        {
            "title": "Authenticate header",
            "control": ft.Column(
                controls=[
                    ft.Text("Authenticate header", weight="bold"),
                    ft.Row(
                        controls=[
                            _var_node("auth", after_node.get("auth"), "spqr_step_auth"),
                            _var_node("epoch", msg_epoch, "spqr_step_epoch"),
                            _var_node("header", header_bytes, "spqr_step_header_in_mac"),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=16,
                        wrap=True,
                    ),
                    ft.Text("↓", size=24),
                    _function_node(
                        "Authenticator.MacHdr",
                        "spqr_step_machdr_fn",
                        full_value="mac = MacHdr(auth, epoch, header)",
                    ),
                    ft.Text("↓", size=24),
                    _var_node("mac", mac, "spqr_step_mac"),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        },
        {
            "title": "Start header stream",
            "control": ft.Column(
                controls=[
                    ft.Text("Start header stream", weight="bold"),
                    _var_node("header||mac", header_with_mac, "spqr_step_header_with_mac"),
                    ft.Text("↓", size=24),
                    _function_node(
                        "new Encoder",
                        "spqr_step_encode_fn",
                        full_value="header_encoder = Encode(header || mac)",
                    ),
                    ft.Text("↓", size=24),
                    _flow_node(
                        "header_encoder",
                        width=220,
                        height=70,
                        tooltip=_tt("spqr_step_header_encoder"),
                        full_value=header_encoder,
                    ),
                    ft.Divider(height=1),
                    _function_node(
                        "Encoder.next_chunk",
                        "spqr_step_next_chunk",
                        full_value="chunk = header_encoder.next_chunk()",
                    ),
                    ft.Text("↓", size=24),
                    _var_node("Header chunk", chunk, "spqr_step_chunk"),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        },
        {
            "title": "Build message with header chunk",
            "control": ft.Column(
                controls=[
                    ft.Text("Build message with header chunk", weight="bold"),
                    ft.Row(
                        controls=[
                            _var_node("Header chunk", chunk, "spqr_step_chunk_in_msg"),
                            _var_node("epoch", msg_epoch, "spqr_step_epoch_in_msg"),
                            _flow_node(
                                "msg.type",
                                "Hdr",
                                width=220,
                                tooltip=_tt("spqr_step_msg_type_in_msg"),
                                full_value="SpqrMessageType.HDR",
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=16,
                        wrap=True,
                    ),
                    ft.Text("↓", size=24),
                    _flow_node(
                        "Build SpqrMessage",
                        circle=True,
                        width=220,
                        height=70,
                        tooltip=_tt("spqr_step_build_message"),
                        full_value={
                            "epoch": msg_epoch,
                            "msg_type": "Hdr",
                            "data": chunk,
                        },
                    ),
                    ft.Text("↓", size=24),
                    ft.Row(
                        controls=[
                            _var_node("epoch", msg_epoch, "spqr_step_msg_epoch"),
                            _flow_node(
                                "msg.type",
                                "Hdr",
                                width=220,
                                tooltip=_tt("spqr_step_msg_type"),
                                full_value="SpqrMessageType.HDR",
                            ),
                            _var_node("msg.data", chunk, "spqr_step_msg_data"),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=16,
                        wrap=True,
                    ),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        },
        {
            "title": "Send result",
            "control": ft.Column(
                controls=[
                    ft.Text("Send result", weight="bold"),
                    ft.Row(
                        controls=[
                            _var_node(
                                "sending_epoch",
                                sending_epoch,
                                "spqr_step_sending_epoch",
                            ),
                            _flow_node(
                                "output_key",
                                "None",
                                width=220,
                                tooltip=_tt("spqr_step_output_key"),
                                full_value=None,
                            ),
                            _flow_node(
                                "next_state",
                                "KeysSampled",
                                width=220,
                                tooltip=_tt("spqr_step_next_state"),
                                full_value="KeysSampled",
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=16,
                        wrap=True,
                    ),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        },
    ]


def _send_keys_sampled(step_data: dict[str, Any], tooltips: dict[str, str]) -> list[dict[str, Any]]:

    ctx = _send_context(step_data)
    return _build_chunk_send_steps(
        chunk=ctx["chunk"],
        msg_epoch=ctx["msg_epoch"],
        sending_epoch=ctx["sending_epoch"],
        generate_title="Generate next header chunk",
        build_title="Build message with header chunk",
        chunk_expr="chunk = header_encoder.next_chunk()",
        msg_type_label="Hdr",
        msg_type_full="SpqrMessageType.HDR",
        next_state="KeysSampled",
    )


def _send_header_sent(step_data: dict[str, Any], tooltips: dict[str, str]) -> list[dict[str, Any]]:
    ctx = _send_context(step_data)
    return _build_chunk_send_steps(
        chunk=ctx["chunk"],
        msg_epoch=ctx["msg_epoch"],
        sending_epoch=ctx["sending_epoch"],
        generate_title="Generate next ek_vector chunk",
        build_title="Build message with ek_vector chunk",
        chunk_expr="chunk = ek_encoder.next_chunk()",
        msg_type_label="Ek",
        msg_type_full="SpqrMessageType.EK",
        next_state="HeaderSent",
    )


def _send_ct1_received(step_data: dict[str, Any], tooltips: dict[str, str]) -> list[dict[str, Any]]:
    ctx = _send_context(step_data)
    return _build_chunk_send_steps(
        chunk=ctx["chunk"],
        msg_epoch=ctx["msg_epoch"],
        sending_epoch=ctx["sending_epoch"],
        generate_title="Generate next ek_vector chunk",
        build_title="Build message with ek_vector chunk and acknowledgment",
        chunk_expr="chunk = ek_encoder.next_chunk()",
        msg_type_label="EkCt1Ack",
        msg_type_full="SpqrMessageType.EK_CT1_ACK",
        next_state="Ct1Received",
    )


def _send_ek_sent_ct1_received(step_data: dict[str, Any], tooltips: dict[str, str]) -> list[dict[str, Any]]:
    ctx = _send_context(step_data)
    return _build_none_send_steps(
        msg_epoch=ctx["msg_epoch"],
        sending_epoch=ctx["sending_epoch"],
        msg_type_label="None",
        msg_type_full="SpqrMessageType.NONE",
        next_state="EkSentCt1Received",
    )


def _send_no_header_received(step_data: dict[str, Any], tooltips: dict[str, str]) -> list[dict[str, Any]]:
    ctx = _send_context(step_data)
    return _build_none_send_steps(
        msg_epoch=ctx["msg_epoch"],
        sending_epoch=ctx["sending_epoch"],
        msg_type_label="None",
        msg_type_full="SpqrMessageType.NONE",
        next_state="NoHeaderReceived",
    )


def _send_header_received(step_data: dict[str, Any], tooltips: dict[str, str]) -> list[dict[str, Any]]:
    ctx = _send_context(step_data)
    after = step_data.get("after") if isinstance(step_data.get("after"), dict) else {}
    after_node = after.get("scka_node") if isinstance(after.get("scka_node"), dict) else {}
    encrypt_trace = step_data.get("encrypt_trace") if isinstance(step_data.get("encrypt_trace"), dict) else {}
    auth = after_node.get("auth")
    ek_header = after_node.get("ek_header")
    encaps_secret = after_node.get("encaps_secret")
    ct1 = after_node.get("ct1")
    ct1_encoder = after_node.get("ct1_encoder") if isinstance(after_node.get("ct1_encoder"), dict) else {}
    output_key = encrypt_trace.get("scka_output_key")

    return [
        {
            "title": "Generate shared secret and ct1 using incremental KEM interface",
            "control": ft.Column(
                controls=[
                    ft.Text("Generate shared secret and ct1 using incremental KEM interface", weight="bold"),
                    _var_node("ek_header", ek_header, "spqr_step_ek_header"),
                    ft.Text("↓", size=24),
                    _function_node(
                        "IncrementalKEM.Encaps1",
                        "spqr_step_keygen_fn",
                        full_value="encaps_secret, ct1, ss = Encaps1(ek_header)",
                    ),
                    ft.Text("↓", size=24),
                    ft.Row(
                        controls=[
                            _var_node("encaps_secret", encaps_secret, "spqr_step_ek_vector"),
                            _var_node("ct1", ct1, "spqr_step_chunk"),
                            _flow_node(
                                "ss",
                                _last_n_chars(encrypt_trace.get("raw_ss"), 8),
                                width=220,
                                tooltip=_tt("spqr_step_key_evolution"),
                                full_value=encrypt_trace.get("raw_ss"),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=16,
                        wrap=True,
                    ),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        },
        {

            "title": "Derive output",
            "control": ft.Column(
                controls=[
                    ft.Text("Derive output key", weight="bold"),
                    ft.Row(
                        controls=[
                            _var_node("ss", "ss_from_encaps1_value", "spqr_step_ss"),
                            _var_node("epoch", ctx["msg_epoch"], "spqr_step_epoch"),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=16,
                        wrap=True,
                    ),
                    ft.Text("↓", size=24),
                    _function_node(
                        "KDF_OK",
                        "spqr_step_kdf_ok",
                        full_value="KDF_OK(ss, epoch)",
                    ),
                    ft.Text("↓", size=24),
                    _var_node(
                        "SS (output_key)",
                        _to_text(output_key),
                        "spqr_step_output_key",
                    ),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        },
        {
            "title": "Update authenticator",
            "control": ft.Column(
                controls=[
                    ft.Text("Update authenticator", weight="bold"),
                    ft.Row(
                        controls=[
                            _var_node("auth", auth, "spqr_step_auth"),
                            _var_node("epoch", ctx["msg_epoch"], "spqr_step_epoch"),
                            _var_node("ss", "ss_from_kdf_ok_value", "spqr_step_ss_after_kdf"),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=16,
                        wrap=True,
                    ),
                    ft.Text("↓", size=24),
                    _function_node(
                        "Authenticator.Update",
                        "spqr_step_machdr_fn",
                        full_value="Authenticator.Update(auth, epoch, ss)",
                    ),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        },
        {
            "title": "Start ct1 stream",
            "control": ft.Column(
                controls=[
                    ft.Text("Start ct1 stream", weight="bold"),
                    _var_node("ct1", ct1, "spqr_step_chunk"),
                    ft.Text("↓", size=24),
                    _function_node(
                        "Encode",
                        "spqr_step_encode_fn",
                        full_value="ct1_encoder = Encode(ct1)",
                    ),
                    ft.Text("↓", size=24),
                    _flow_node(
                        "ct1_encoder",
                        _last_n_chars(ct1_encoder.get("chunk_size"), 8),
                        width=220,
                        height=70,
                        tooltip=_tt("spqr_step_header_encoder"),
                        full_value=ct1_encoder,
                    ),
                    ft.Divider(height=1),
                    _function_node(
                        "Encoder.next_chunk",
                        "spqr_step_next_chunk",
                        full_value="chunk = ct1_encoder.next_chunk()",
                    ),
                    ft.Text("↓", size=24),
                    _var_node("chunk", ctx["chunk"], "spqr_step_chunk"),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        },
        *_build_message_step(
            build_title="Build message with ct1 chunk",
            chunk=ctx["chunk"],
            msg_epoch=ctx["msg_epoch"],
            msg_type_label="Ct1",
            msg_type_full="SpqrMessageType.CT1",
        ),
        _build_send_result_step(
            sending_epoch=ctx["sending_epoch"],
            output_key_label="OutputKey",
            output_key=output_key,
            next_state="Ct1Sampled",
        ),
    ]


def _send_ct1_sampled(step_data: dict[str, Any], tooltips: dict[str, str]) -> list[dict[str, Any]]:
    ctx = _send_context(step_data)
    return _build_chunk_send_steps(
        chunk=ctx["chunk"],
        msg_epoch=ctx["msg_epoch"],
        sending_epoch=ctx["sending_epoch"],
        generate_title="Generate next ct1 chunk",
        build_title="Build message with ct1 chunk",
        chunk_expr="chunk = ct1_encoder.next_chunk()",
        msg_type_label="Ct1",
        msg_type_full="SpqrMessageType.CT1",
        next_state="Ct1Sampled",
    )


def _send_ek_received_ct1_sampled(step_data: dict[str, Any], tooltips: dict[str, str]) -> list[dict[str, Any]]:
    ctx = _send_context(step_data)
    return _build_chunk_send_steps(
        chunk=ctx["chunk"],
        msg_epoch=ctx["msg_epoch"],
        sending_epoch=ctx["sending_epoch"],
        generate_title="Generate next ct1 chunk",
        build_title="Build message with ct1 chunk",
        chunk_expr="chunk = ct1_encoder.next_chunk()",
        msg_type_label="Ct1",
        msg_type_full="SpqrMessageType.CT1",
        next_state="EkReceivedCt1Sampled",
    )


def _send_ct1_acknowledged(step_data: dict[str, Any], tooltips: dict[str, str]) -> list[dict[str, Any]]:
    ctx = _send_context(step_data)
    return _build_none_send_steps(
        msg_epoch=ctx["msg_epoch"],
        sending_epoch=ctx["sending_epoch"],
        msg_type_label="None",
        msg_type_full="SpqrMessageType.NONE",
        next_state="Ct1Acknowledged",
    )


def _send_ct2_sampled(step_data: dict[str, Any], tooltips: dict[str, str]) -> list[dict[str, Any]]:
    ctx = _send_context(step_data)
    return _build_chunk_send_steps(
        chunk=ctx["chunk"],
        msg_epoch=ctx["msg_epoch"],
        sending_epoch=ctx["sending_epoch"],
        generate_title="Generate next ct2 chunk",
        build_title="Build message with ct2 chunk",
        chunk_expr="chunk = ct2_encoder.next_chunk()",
        msg_type_label="Ct2",
        msg_type_full="SpqrMessageType.CT2",
        next_state="Ct2Sampled",
    )


def _build_message_step(
    build_title: str,
    chunk: Any,
    msg_epoch: Any,
    msg_type_label: str,
    msg_type_full: str,
) -> list[dict[str, Any]]:
    return [
        {
            "title": build_title,
            "control": ft.Column(
                controls=[
                    ft.Text(build_title, weight="bold"),
                    ft.Row(
                        controls=[
                            _var_node("chunk", chunk, "spqr_step_chunk_in_msg"),
                            _var_node("epoch", msg_epoch, "spqr_step_epoch_in_msg"),
                            _flow_node(
                                "msg.type",
                                msg_type_label,
                                width=220,
                                tooltip=_tt("spqr_step_msg_type_in_msg"),
                                full_value=msg_type_full,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=16,
                        wrap=True,
                    ),
                    ft.Text("↓", size=24),
                    _flow_node(
                        "Build SpqrMessage",
                        circle=True,
                        width=220,
                        height=70,
                        tooltip=_tt("spqr_step_build_message"),
                        full_value={
                            "epoch": msg_epoch,
                            "msg_type": msg_type_label,
                            "data": chunk,
                        },
                    ),
                    ft.Text("↓", size=24),
                    ft.Row(
                        controls=[
                            _var_node("epoch", msg_epoch, "spqr_step_msg_epoch"),
                            _flow_node(
                                "msg.type",
                                msg_type_label,
                                width=220,
                                tooltip=_tt("spqr_step_msg_type"),
                                full_value=msg_type_full,
                            ),
                            _var_node("msg.data", chunk, "spqr_step_msg_data"),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=16,
                        wrap=True,
                    ),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        }
    ]


def _build_send_result_step(
    sending_epoch: Any,
    output_key_label: str,
    output_key: Any,
    next_state: str,
) -> dict[str, Any]:
    return {
        "title": "Send result",
        "control": ft.Column(
            controls=[
                ft.Text("Send result", weight="bold"),
                ft.Row(
                    controls=[
                        _var_node(
                            "sending_epoch",
                            sending_epoch,
                            "spqr_step_sending_epoch",
                        ),
                        _flow_node(
                            "output_key",
                            output_key_label,
                            width=220,
                            tooltip=_tt("spqr_step_output_key"),
                            full_value=output_key,
                        ),
                        _flow_node(
                            "next_state",
                            next_state,
                            width=220,
                            tooltip=_tt("spqr_step_next_state"),
                            full_value=next_state,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=16,
                    wrap=True,
                ),
            ],
            spacing=6,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    }


def _build_chunk_send_steps(
    chunk: Any,
    msg_epoch: Any,
    sending_epoch: Any,
    generate_title: str,
    build_title: str,
    chunk_expr: str,
    msg_type_label: str,
    msg_type_full: str,
    next_state: str,
) -> list[dict[str, Any]]:
    return [
        {
            "title": generate_title,
            "control": ft.Column(
                controls=[
                    ft.Text(generate_title, weight="bold"),
                    _function_node(
                        "Encoder.next_chunk",
                        "spqr_step_next_chunk",
                        full_value=chunk_expr,
                    ),
                    ft.Text("↓", size=24),
                    _var_node("chunk", chunk, "spqr_step_chunk"),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        },
        *_build_message_step(
            build_title=build_title,
            chunk=chunk,
            msg_epoch=msg_epoch,
            msg_type_label=msg_type_label,
            msg_type_full=msg_type_full,
        ),
        _build_send_result_step(
            sending_epoch=sending_epoch,
            output_key_label="None",
            output_key=None,
            next_state=next_state,
        ),
    ]


def _build_none_send_steps(
    msg_epoch: Any,
    sending_epoch: Any,
    msg_type_label: str,
    msg_type_full: str,
    next_state: str,
) -> list[dict[str, Any]]:
    return [
        {
            "title": "Build message with no data to send",
            "control": ft.Column(
                controls=[
                    ft.Text("Build message with no data to send", weight="bold"),
                    ft.Row(
                        controls=[
                            _flow_node("data", "None", width=220, tooltip=_tt("spqr_step_chunk_in_msg"), full_value=None),
                            _var_node("epoch", msg_epoch, "spqr_step_epoch_in_msg"),
                            _flow_node(
                                "msg.type",
                                msg_type_label,
                                width=220,
                                tooltip=_tt("spqr_step_msg_type_in_msg"),
                                full_value=msg_type_full,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=16,
                        wrap=True,
                    ),
                    ft.Text("↓", size=24),
                    _flow_node(
                        "Build SpqrMessage",
                        circle=True,
                        width=220,
                        height=70,
                        tooltip=_tt("spqr_step_build_message"),
                        full_value={
                            "epoch": msg_epoch,
                            "msg_type": msg_type_label,
                            "data": None,
                        },
                    ),
                    ft.Text("↓", size=24),
                    ft.Row(
                        controls=[
                            _var_node("epoch", msg_epoch, "spqr_step_msg_epoch"),
                            _flow_node(
                                "msg.type",
                                msg_type_label,
                                width=220,
                                tooltip=_tt("spqr_step_msg_type"),
                                full_value=msg_type_full,
                            ),
                            _flow_node("msg.data", "None", width=220, tooltip=_tt("spqr_step_msg_data"), full_value=None),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=16,
                        wrap=True,
                    ),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        },
        _build_send_result_step(
            sending_epoch=sending_epoch,
            output_key_label="None",
            output_key=None,
            next_state=next_state,
        ),
    ]


def _send_context(step_data: dict[str, Any]) -> dict[str, Any]:
    header: SpqrHeader | None = step_data.get("header") if isinstance(step_data.get("header"), SpqrHeader) else None
    before = step_data.get("before") if isinstance(step_data.get("before"), dict) else {}
    after = step_data.get("after") if isinstance(step_data.get("after"), dict) else {}
    before_node = before.get("scka_node") if isinstance(before.get("scka_node"), dict) else {}
    after_node = after.get("scka_node") if isinstance(after.get("scka_node"), dict) else {}
    active_node = after_node if after_node else before_node

    msg_epoch = (
        header.msg.epoch
        if header is not None
        else active_node.get("epoch", after.get("epoch", before.get("epoch")))
    )
    sending_epoch = msg_epoch - 1 if isinstance(msg_epoch, int) else "self.epoch - 1"
    chunk = header.msg.data if header is not None else None

    return {
        "header": header,
        "before": before,
        "after": after,
        "before_node": before_node,
        "after_node": after_node,
        "msg_epoch": msg_epoch,
        "sending_epoch": sending_epoch,
        "chunk": chunk,
    }


def _output_key_expected(action: str, state_name: str) -> bool:
    if action == "send" and state_name == "HeaderReceived":
        return True
    if action == "receive" and state_name == "EkSentCt1Received":
        return True
    return False


def _build_intro_step(before: dict[str, Any], tooltips: dict[str, str]) -> dict[str, Any]:
    intro_control = ft.Column(
        controls=[
            _party_state_panel(
                "Before snapshot",
                _before_after_rows(before, tooltips),
                tooltip=tooltips.get("spqr_step_before_panel", ""),
            ),
        ],
        spacing=6,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )
    return {
        "title": "State before",
        "control": intro_control,
    }


def _build_output_key_step(
    action: str,
    state_name: str,
    before: dict[str, Any],
    after: dict[str, Any],
    header: SpqrHeader | None,
    tooltips: dict[str, str],
) -> dict[str, Any]:
    rk_changed = before.get("rk_tail") != after.get("rk_tail")
    output_key_produced = _output_key_expected(action, state_name)
    output_label = "output_key produced" if output_key_produced else "output_key = None"
    rk_label = "RK derivation needed" if rk_changed else "No new RK derived"

    output_control = ft.Column(
        controls=[
            ft.Text("Output key and root-key decision", weight="bold"),
            _flow_node(
                "SCKA output",
                output_label,
                width=320,
                tooltip=tooltips.get("spqr_step_key_evolution", ""),
            ),
            ft.Text("↓", size=24),
            _flow_node(
                "Root key derivation",
                rk_label,
                width=320,
                tooltip=tooltips.get("spqr_step_rk_change", ""),
            ),
        ],
        spacing=6,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )
    return {
        "title": "Output key decision",
        "control": output_control,
    }


def _build_rk_derivation_step(
    action: str,
    state_name: str,
    before: dict[str, Any],
    after: dict[str, Any],
    step_data: dict[str, Any],
) -> dict[str, Any] | None:
    if before.get("rk_tail") == after.get("rk_tail"):
        return None

    derivation_trace = step_data.get("encrypt_trace") if isinstance(step_data.get("encrypt_trace"), dict) else {}
    scka_output_key = derivation_trace.get("scka_output_key")
    if scka_output_key is None:
        scka_output_key = "from SCKA output"

    rk_before = derivation_trace.get("rk_before", before.get("rk_tail"))
    rk_after = derivation_trace.get("rk_after", after.get("rk_tail"))
    new_cks = derivation_trace.get("new_cks", after.get("send_ck_tail"))
    new_ckr = derivation_trace.get("new_ckr", after.get("recv_ck_tail"))

    return {
        "title": "RK derivation",
        "control": ft.Column(
            controls=[
                ft.Text("RK derivation", weight="bold"),
                ft.Row(
                    controls=[
                        _var_node("RK", rk_before, "spqr_step_rk"),
                        _var_node("SCKA_output_key", scka_output_key, "spqr_step_output_key"),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=16,
                    wrap=True,
                ),
                ft.Text("↓", size=24),
                _function_node(
                    "KDF_SCKA_RK",
                    "spqr_step_key_evolution",
                    full_value="new_RK, new_CKs, new_CKr = KDF_SCKA_RK(RK, SCKA_output_key)",
                ),
                ft.Text("↓", size=24),
                ft.Row(
                    controls=[
                        _var_node("new RK", rk_after, "spqr_step_rk"),
                        _var_node("new CKs", new_cks, "spqr_step_send_ck"),
                        _var_node("new CKr", new_ckr, "spqr_step_recv_ck"),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=16,
                    wrap=True,
                ),
            ],
            spacing=6,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    }


def _build_send_steps(state_name: str, step_data: dict[str, Any], tooltips: dict[str, str]) -> list[dict[str, Any]]:
    builders: dict[str, Callable[[dict[str, Any], dict[str, str]], list[dict[str, Any]]]] = {
        "KeysUnsampled": _send_keys_unsampled,
        "KeysSampled": _send_keys_sampled,
        "HeaderSent": _send_header_sent,
        "Ct1Received": _send_ct1_received,
        "EkSentCt1Received": _send_ek_sent_ct1_received,
        "NoHeaderReceived": _send_no_header_received,
        "HeaderReceived": _send_header_received,
        "Ct1Sampled": _send_ct1_sampled,
        "EkReceivedCt1Sampled": _send_ek_received_ct1_sampled,
        "Ct1Acknowledged": _send_ct1_acknowledged,
        "Ct2Sampled": _send_ct2_sampled,
    }
    builder = builders.get(state_name)
    if builder is None:
        return []
    return builder(step_data, tooltips)


def _receive_keys_sampled(step_data: dict[str, Any], tooltips: dict[str, str]) -> list[dict[str, Any]]:
    header: SpqrHeader | None = step_data.get("header") if isinstance(step_data.get("header"), SpqrHeader) else None
    before = step_data.get("before") if isinstance(step_data.get("before"), dict) else {}
    after = step_data.get("after") if isinstance(step_data.get("after"), dict) else {}
    before_node = before.get("scka_node") if isinstance(before.get("scka_node"), dict) else {}
    after_node = after.get("scka_node") if isinstance(after.get("scka_node"), dict) else {}

    chunk = header.msg.data if header is not None else None
    msg_epoch = header.msg.epoch if header is not None else before_node.get("epoch")
    msg_type = header.msg.msg_type.value if header is not None else None
    self_epoch = before_node.get("epoch")
    condition_met = msg_epoch == self_epoch and msg_type == "Ct1"

    ct1_decoder = after_node.get("ct1_decoder") if isinstance(after_node.get("ct1_decoder"), dict) else None
    ek_vector = before_node.get("ek_vector", after_node.get("ek_vector"))
    ek_encoder = after_node.get("ek_encoder") if isinstance(after_node.get("ek_encoder"), dict) else None

    return [
        {
            "title": "Initialize Decoder",
            "control": ft.Column(
                controls=[
                    ft.Text("Initialize Decoder", weight="bold"),
                    ft.Row(
                        controls=[
                            _var_node("msg.epoch", msg_epoch, "spqr_step_epoch"),
                            _flow_node("msg.type", str(msg_type), width=220, tooltip=_tt("spqr_step_msg_type"), full_value=msg_type),
                            _var_node("self.epoch", self_epoch, "spqr_step_epoch"),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=16,
                        wrap=True,
                    ),
                    ft.Text("↓", size=24),
                    _flow_node(
                        "Condition",
                        "msg.epoch == self.epoch and msg.type == Ct1",
                        width=420,
                        tooltip=_tt("spqr_step_state_op"),
                        full_value=condition_met,
                    ),
                    ft.Text("↓", size=24),
                    _function_node(
                        "new Decoder()",
                        "spqr_step_state_op",
                    ),
                    ft.Text("↓", size=24),
                    _flow_node(
                        "ct1_decoder",
                        width=260,
                        tooltip=_tt("spqr_step_state_op"),
                        full_value=ct1_decoder,
                    ),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        },
        {
            "title": "chunk -> Decoder add chunk",
            "control": ft.Column(
                controls=[
                    ft.Text("chunk -> Decoder add chunk", weight="bold"),
                    _var_node("msg.data - Chunk", chunk, "spqr_step_chunk"),
                    ft.Text("↓", size=24),
                    _function_node(
                        "Decoder.add_chunk",
                        "spqr_step_state_op",
                        full_value="ct1_decoder.add_chunk(chunk)",
                    ),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        },
        {
            "title": "ek_vector -> Initialize EkEncoder -> EkEncoder",
            "control": ft.Column(
                controls=[
                    ft.Text("ek_vector -> Initialize EkEncoder -> EkEncoder", weight="bold"),
                    _var_node("ek_vector", ek_vector, "spqr_step_ek_vector"),
                    ft.Text("↓", size=24),
                    _function_node(
                        "new Encoder()",
                        "spqr_step_encode_fn",
                    ),
                    ft.Text("↓", size=24),
                    _flow_node(
                        "EkEncoder",
                        "initialized with ek_vector" if ek_encoder is not None else "not initialized",
                        width=260,
                        tooltip=_tt("spqr_step_state_op"),
                        full_value=ek_encoder,
                    ),
                    ft.Divider(height=10),
                    _flow_node(
                        "Next state",
                        "HeaderSent",
                        width=260,
                        tooltip=_tt("spqr_step_next_state"),
                        full_value=after.get("state", before.get("state")),
                    ),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        },
    ]


def _receive_header_sent(step_data: dict[str, Any], tooltips: dict[str, str]) -> list[dict[str, Any]]:
    header: SpqrHeader | None = step_data.get("header") if isinstance(step_data.get("header"), SpqrHeader) else None
    before = step_data.get("before") if isinstance(step_data.get("before"), dict) else {}
    after = step_data.get("after") if isinstance(step_data.get("after"), dict) else {}
    before_node = before.get("scka_node") if isinstance(before.get("scka_node"), dict) else {}

    chunk = header.msg.data if header is not None else None
    ct1_decoder = before_node.get("ct1_decoder") if isinstance(before_node.get("ct1_decoder"), dict) else None
    has_message = str(after.get("state", before.get("state", ""))) == "Ct1Received"

    return [
        {
            "title": "chunk -> Decoder add chunk",
            "control": ft.Column(
                controls=[
                    ft.Text("chunk -> Decoder add chunk", weight="bold"),
                    ft.Row(
                        controls=[
                            _var_node("chunk", chunk, "spqr_step_chunk"),
                            _flow_node(
                                "Decoder",
                                "ct1_decoder",
                                width=220,
                                tooltip=_tt("spqr_step_state_op"),
                                full_value=ct1_decoder,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=16,
                        wrap=True,
                    ),
                    ft.Text("↓", size=24),
                    _function_node(
                        "Decoder.add_chunk",
                        "spqr_step_state_op",
                        full_value="ct1_decoder.add_chunk(chunk)",
                    ),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        },
        {
            "title": "Decoder has message()",
            "control": ft.Column(
                controls=[
                    ft.Text("Decoder has message()", weight="bold"),
                    _function_node(
                        "Decoder.has_message",
                        "spqr_step_state_op",
                        full_value="ct1_decoder.has_message()",
                    ),
                    ft.Text("↓", size=24),
                    _flow_node(
                        "has_message",
                        "yes" if has_message else "no",
                        width=220,
                        tooltip=_tt("spqr_step_state_op"),
                        full_value=has_message,
                    ),
                    ft.Text("↓", size=24),
                    _flow_node(
                        "state transition" if has_message else "remain in current state",
                        "Ct1Received" if has_message else "HeaderSent",
                        width=260,
                        circle=True,
                        tooltip=_tt("spqr_step_next_state"),
                        full_value=after.get("state", before.get("state")),
                    ),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        },
    ]


def _receive_no_header_received(step_data: dict[str, Any], tooltips: dict[str, str]) -> list[dict[str, Any]]:
    header: SpqrHeader | None = step_data.get("header") if isinstance(step_data.get("header"), SpqrHeader) else None
    before = step_data.get("before") if isinstance(step_data.get("before"), dict) else {}
    after = step_data.get("after") if isinstance(step_data.get("after"), dict) else {}
    before_node = before.get("scka_node") if isinstance(before.get("scka_node"), dict) else {}
    after_node = after.get("scka_node") if isinstance(after.get("scka_node"), dict) else {}

    chunk = header.msg.data if header is not None else None
    msg_epoch = header.msg.epoch if header is not None else before_node.get("epoch")
    msg_type = header.msg.msg_type.value if header is not None else None
    self_epoch = before_node.get("epoch")
    condition_met = msg_epoch == self_epoch and msg_type == "Hdr"
    next_state = after.get("state", before.get("state"))
    completed = next_state == "HeaderReceived"
    header_with_mac = after_node.get("ek_header") if isinstance(after_node.get("ek_header"), (bytes, bytearray)) else None

    return [
        {
            "title": "Initialize header decoder",
            "control": ft.Column(
                controls=[
                    ft.Text("Initialize header decoder", weight="bold"),
                    ft.Row(
                        controls=[
                            _var_node("msg.epoch", msg_epoch, "spqr_step_epoch"),
                            _flow_node("msg.type", str(msg_type), width=220, tooltip=_tt("spqr_step_msg_type"), full_value=msg_type),
                            _var_node("self.epoch", self_epoch, "spqr_step_epoch"),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=16,
                        wrap=True,
                    ),
                    ft.Text("↓", size=24),
                    _flow_node(
                        "Condition",
                        "msg.epoch == self.epoch and msg.type == Hdr",
                        width=420,
                        tooltip=_tt("spqr_step_state_op"),
                        full_value=condition_met,
                    ),
                    ft.Text("↓", size=24),
                    _var_node("chunk", chunk, "spqr_step_chunk"),
                    ft.Text("↓", size=24),
                    _function_node(
                        "Decoder.add_chunk",
                        "spqr_step_state_op",
                        full_value="header_decoder.add_chunk(chunk)",
                    ),
                    ft.Text("↓", size=24),
                    _var_node(
                        "header with MAC",
                        header_with_mac,
                        "spqr_step_header_with_mac",
                    ),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        },
        {
            "title": "Decoder.has_message()",
            "control": ft.Column(
                controls=[
                    ft.Text("Decoder.has_message()", weight="bold"),
                    _flow_node(
                        "has_message",
                        "yes" if completed else "no",
                        width=220,
                        tooltip=_tt("spqr_step_state_op"),
                        full_value=completed,
                    ),
                    ft.Text("↓", size=24),
                    _flow_node(
                        "state transition" if completed else "remain in current state",
                        "HeaderReceived" if completed else "NoHeaderReceived",
                        width=260,
                        circle=True,
                        tooltip=_tt("spqr_step_next_state"),
                        full_value=next_state,
                    ),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        },
    ]


def _receive_header_received(step_data: dict[str, Any], tooltips: dict[str, str]) -> list[dict[str, Any]]:
    before = step_data.get("before") if isinstance(step_data.get("before"), dict) else {}
    after = step_data.get("after") if isinstance(step_data.get("after"), dict) else {}

    return [
        {
            "title": "No action taken",
            "control": ft.Column(
                controls=[
                    ft.Text("No action taken", weight="bold"),
                    _flow_node(
                        "HeaderReceived.receive",
                        "noop",
                        width=260,
                        tooltip=_tt("spqr_step_state_op"),
                        full_value="No action taken",
                    ),
                    ft.Text("↓", size=24),
                    _flow_node(
                        "state",
                        str(after.get("state", before.get("state"))),
                        width=260,
                        circle=True,
                        tooltip=_tt("spqr_step_next_state"),
                        full_value=after.get("state", before.get("state")),
                    ),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        },
    ]


def _receive_ct1_sampled(step_data: dict[str, Any], tooltips: dict[str, str]) -> list[dict[str, Any]]:
    header: SpqrHeader | None = step_data.get("header") if isinstance(step_data.get("header"), SpqrHeader) else None
    before = step_data.get("before") if isinstance(step_data.get("before"), dict) else {}
    after = step_data.get("after") if isinstance(step_data.get("after"), dict) else {}
    before_node = before.get("scka_node") if isinstance(before.get("scka_node"), dict) else {}
    after_state = str(after.get("state", before.get("state", "")))

    chunk = header.msg.data if header is not None else None
    msg_epoch = header.msg.epoch if header is not None else before_node.get("epoch")
    msg_type = header.msg.msg_type.value if header is not None else None
    self_epoch = before_node.get("epoch")
    msg_type_label = str(msg_type)
    is_ek_branch = msg_epoch == self_epoch and msg_type_label == "Ek"
    is_ek_ack_branch = msg_epoch == self_epoch and msg_type_label == "EkCt1Ack"

    if is_ek_branch:
        completed = after_state == "EkReceivedCt1Sampled"
        return [
            {
                "title": "EK branch guard",
                "control": ft.Column(
                    controls=[
                        ft.Text("EK branch guard", weight="bold"),
                        ft.Row(
                            controls=[
                                _var_node("msg.epoch", msg_epoch, "spqr_step_epoch"),
                                _flow_node("msg.type", msg_type_label, width=220, tooltip=_tt("spqr_step_msg_type"), full_value=msg_type_label),
                                _var_node("self.epoch", self_epoch, "spqr_step_epoch"),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=16,
                            wrap=True,
                        ),
                        ft.Text("↓", size=24),
                        _flow_node(
                            "Condition",
                            "msg.epoch == self.epoch and msg.type == Ek",
                            width=420,
                            tooltip=_tt("spqr_step_state_op"),
                            full_value=is_ek_branch,
                        ),
                    ],
                    spacing=6,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            },
            {
                "title": "Add EK chunk",
                "control": ft.Column(
                    controls=[
                        ft.Text("Add EK chunk", weight="bold"),
                        _var_node("chunk", chunk, "spqr_step_chunk"),
                        ft.Text("↓", size=24),
                        _function_node(
                            "ek_decoder.add_chunk",
                            "spqr_step_state_op",
                            full_value="ek_decoder.add_chunk(chunk)",
                        ),
                    ],
                    spacing=6,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            },
            {
                "title": "Check EK completeness",
                "control": ft.Column(
                    controls=[
                        ft.Text("Check EK completeness", weight="bold"),
                        _flow_node(
                            "ek_decoder.has_message",
                            "yes" if completed else "no",
                            width=260,
                            tooltip=_tt("spqr_step_state_op"),
                            full_value=completed,
                        ),
                        ft.Text("↓", size=24),
                        _flow_node(
                            "state transition",
                            "EkReceivedCt1Sampled" if completed else "Ct1Sampled",
                            width=260,
                            circle=True,
                            tooltip=_tt("spqr_step_next_state"),
                            full_value=after_state,
                        ),
                    ],
                    spacing=6,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            },
        ]

    if is_ek_ack_branch:
        completed = after_state == "Ct2Sampled"
        return [
            {
                "title": "EK_CT1_ACK branch guard",
                "control": ft.Column(
                    controls=[
                        ft.Text("EK_CT1_ACK branch guard", weight="bold"),
                        ft.Row(
                            controls=[
                                _var_node("msg.epoch", msg_epoch, "spqr_step_epoch"),
                                _flow_node("msg.type", msg_type_label, width=220, tooltip=_tt("spqr_step_msg_type"), full_value=msg_type_label),
                                _var_node("self.epoch", self_epoch, "spqr_step_epoch"),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=16,
                            wrap=True,
                        ),
                        ft.Text("↓", size=24),
                        _flow_node(
                            "Condition",
                            "msg.epoch == self.epoch and msg.type == EkCt1Ack",
                            width=420,
                            tooltip=_tt("spqr_step_state_op"),
                            full_value=is_ek_ack_branch,
                        ),
                    ],
                    spacing=6,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            },
            {
                "title": "Add EK_CT1_ACK chunk",
                "control": ft.Column(
                    controls=[
                        ft.Text("Add EK_CT1_ACK chunk", weight="bold"),
                        _var_node("chunk", chunk, "spqr_step_chunk"),
                        ft.Text("↓", size=24),
                        _function_node(
                            "ek_decoder.add_chunk",
                            "spqr_step_state_op",
                            full_value="ek_decoder.add_chunk(chunk)",
                        ),
                    ],
                    spacing=6,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            },
            {
                "title": "Check EK completeness",
                "control": ft.Column(
                    controls=[
                        ft.Text("Check EK completeness", weight="bold"),
                        _flow_node(
                            "ek_decoder.has_message",
                            "yes" if completed else "no",
                            width=260,
                            tooltip=_tt("spqr_step_state_op"),
                            full_value=completed,
                        ),
                        ft.Text("↓", size=24),
                        _flow_node(
                            "state transition",
                            "Ct2Sampled" if completed else "Ct1Acknowledged",
                            width=300,
                            circle=True,
                            tooltip=_tt("spqr_step_next_state"),
                            full_value=after_state,
                        ),
                    ],
                    spacing=6,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            },
        ]

    return [
        {
            "title": "No matching branch",
            "control": ft.Column(
                controls=[
                    ft.Text("No matching branch", weight="bold"),
                    ft.Row(
                        controls=[
                            _var_node("msg.epoch", msg_epoch, "spqr_step_epoch"),
                            _flow_node("msg.type", msg_type_label, width=220, tooltip=_tt("spqr_step_msg_type"), full_value=msg_type_label),
                            _var_node("self.epoch", self_epoch, "spqr_step_epoch"),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=16,
                        wrap=True,
                    ),
                    ft.Text("↓", size=24),
                    _flow_node(
                        "state transition",
                        "Ct1Sampled (no-op)",
                        width=260,
                        circle=True,
                        tooltip=_tt("spqr_step_next_state"),
                        full_value=after_state,
                    ),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        }
    ]


def _receive_ek_received_ct1_sampled(step_data: dict[str, Any], tooltips: dict[str, str]) -> list[dict[str, Any]]:
    before = step_data.get("before") if isinstance(step_data.get("before"), dict) else {}
    after = step_data.get("after") if isinstance(step_data.get("after"), dict) else {}

    return [
        {
            "title": "Complete encapsulation",
            "control": ft.Column(
                controls=[
                    ft.Text("Complete encapsulation", weight="bold"),
                    _flow_node(
                        "EK_CT1_ACK",
                        str(step_data.get("header").msg.msg_type.value if isinstance(step_data.get("header"), SpqrHeader) else ""),
                        width=240,
                        tooltip=_tt("spqr_step_msg_type"),
                        full_value=step_data.get("header").msg.to_dict() if isinstance(step_data.get("header"), SpqrHeader) else None,
                    ),
                    ft.Text("↓", size=24),
                    _function_node(
                        "Encaps2 + MacCt",
                        "spqr_step_state_op",
                        full_value="ct2 = Encaps2(...); mac = MacCt(...)",
                    ),
                    ft.Text("↓", size=24),
                    _flow_node(
                        "state",
                        str(after.get("state", before.get("state"))),
                        width=260,
                        circle=True,
                        tooltip=_tt("spqr_step_next_state"),
                        full_value=after.get("state", before.get("state")),
                    ),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        },
    ]


def _receive_ct1_acknowledged(step_data: dict[str, Any], tooltips: dict[str, str]) -> list[dict[str, Any]]:
    header: SpqrHeader | None = step_data.get("header") if isinstance(step_data.get("header"), SpqrHeader) else None
    before = step_data.get("before") if isinstance(step_data.get("before"), dict) else {}
    after = step_data.get("after") if isinstance(step_data.get("after"), dict) else {}
    before_node = before.get("scka_node") if isinstance(before.get("scka_node"), dict) else {}

    chunk = header.msg.data if header is not None else None
    msg_epoch = header.msg.epoch if header is not None else before_node.get("epoch")
    msg_type = header.msg.msg_type.value if header is not None else None
    self_epoch = before_node.get("epoch")
    completed = after.get("state", before.get("state")) == "Ct2Sampled"

    return [
        {
            "title": "Add EK_CT1_ACK chunk",
            "control": ft.Column(
                controls=[
                    ft.Text("Add EK_CT1_ACK chunk", weight="bold"),
                    ft.Row(
                        controls=[
                            _var_node("msg.epoch", msg_epoch, "spqr_step_epoch"),
                            _flow_node("msg.type", str(msg_type), width=220, tooltip=_tt("spqr_step_msg_type"), full_value=msg_type),
                            _var_node("self.epoch", self_epoch, "spqr_step_epoch"),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=16,
                        wrap=True,
                    ),
                    ft.Text("↓", size=24),
                    _var_node("chunk", chunk, "spqr_step_chunk"),
                    ft.Text("↓", size=24),
                    _function_node(
                        "ek_decoder.add_chunk",
                        "spqr_step_state_op",
                        full_value="ek_decoder.add_chunk(chunk)",
                    ),
                    ft.Text("↓", size=24),
                    _flow_node(
                        "has_message",
                        "yes" if completed else "no",
                        width=220,
                        tooltip=_tt("spqr_step_state_op"),
                        full_value=completed,
                    ),
                    ft.Text("↓", size=24),
                    _flow_node(
                        "state transition",
                        str(after.get("state", before.get("state"))),
                        width=260,
                        circle=True,
                        tooltip=_tt("spqr_step_next_state"),
                        full_value=after.get("state", before.get("state")),
                    ),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        },
    ]


def _receive_ct2_sampled(step_data: dict[str, Any], tooltips: dict[str, str]) -> list[dict[str, Any]]:
    header: SpqrHeader | None = step_data.get("header") if isinstance(step_data.get("header"), SpqrHeader) else None
    before = step_data.get("before") if isinstance(step_data.get("before"), dict) else {}
    after = step_data.get("after") if isinstance(step_data.get("after"), dict) else {}
    before_node = before.get("scka_node") if isinstance(before.get("scka_node"), dict) else {}

    msg_epoch = header.msg.epoch if header is not None else before_node.get("epoch")
    next_epoch = msg_epoch + 1 if isinstance(msg_epoch, int) else None

    return [
        {
            "title": "Check next epoch",
            "control": ft.Column(
                controls=[
                    ft.Text("Check next epoch", weight="bold"),
                    _var_node("msg.epoch", msg_epoch, "spqr_step_epoch"),
                    ft.Text("↓", size=24),
                    _flow_node(
                        "Condition",
                        "msg.epoch == self.epoch + 1",
                        width=320,
                        tooltip=_tt("spqr_step_state_op"),
                        full_value=bool(next_epoch),
                    ),
                    ft.Text("↓", size=24),
                    _flow_node(
                        "Next state",
                        str(after.get("state", before.get("state"))),
                        width=260,
                        circle=True,
                        tooltip=_tt("spqr_step_next_state"),
                        full_value=after.get("state", before.get("state")),
                    ),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        },
    ]


def _receive_ct1_received(step_data: dict[str, Any], tooltips: dict[str, str]) -> list[dict[str, Any]]:
    header: SpqrHeader | None = step_data.get("header") if isinstance(step_data.get("header"), SpqrHeader) else None
    before = step_data.get("before") if isinstance(step_data.get("before"), dict) else {}
    after = step_data.get("after") if isinstance(step_data.get("after"), dict) else {}
    before_node = before.get("scka_node") if isinstance(before.get("scka_node"), dict) else {}

    chunk = header.msg.data if header is not None else None
    msg_epoch = header.msg.epoch if header is not None else before_node.get("epoch")
    msg_type = header.msg.msg_type.value if header is not None else None
    self_epoch = before_node.get("epoch")

    return [
        {
            "title": "Initialize ct2 decoder",
            "control": ft.Column(
                controls=[
                    ft.Text("Initialize ct2 decoder", weight="bold"),
                    ft.Row(
                        controls=[
                            _var_node("msg.epoch", msg_epoch, "spqr_step_epoch"),
                            _flow_node("msg.type", str(msg_type), width=220, tooltip=_tt("spqr_step_msg_type"), full_value=msg_type),
                            _var_node("self.epoch", self_epoch, "spqr_step_epoch"),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=16,
                        wrap=True,
                    ),
                    ft.Text("↓", size=24),
                    _flow_node(
                        "Condition",
                        "msg.epoch == self.epoch and msg.type == Ct2",
                        width=420,
                        tooltip=_tt("spqr_step_state_op"),
                        full_value=msg_type == "Ct2",
                    ),
                    ft.Text("↓", size=24),
                    _var_node("chunk", chunk, "spqr_step_chunk"),
                    ft.Text("↓", size=24),
                    _function_node(
                        "ct2_decoder = Decoder_new(CT2_SIZE + MAC_SIZE)",
                        "spqr_step_state_op",
                        full_value="ct2_decoder = Decoder_new(CT2_SIZE + MAC_SIZE)",
                    ),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        },
        {
            "title": "Add CT2 chunk",
            "control": ft.Column(
                controls=[
                    ft.Text("Add CT2 chunk", weight="bold"),
                    _function_node(
                        "ct2_decoder.add_chunk",
                        "spqr_step_state_op",
                        full_value="ct2_decoder.add_chunk(chunk)",
                    ),
                    ft.Text("↓", size=24),
                    _flow_node(
                        "state transition",
                        str(after.get("state", before.get("state"))),
                        width=260,
                        circle=True,
                        tooltip=_tt("spqr_step_next_state"),
                        full_value=after.get("state", before.get("state")),
                    ),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        },
    ]


def _receive_ek_sent_ct1_received(step_data: dict[str, Any], tooltips: dict[str, str]) -> list[dict[str, Any]]:
    header: SpqrHeader | None = step_data.get("header") if isinstance(step_data.get("header"), SpqrHeader) else None
    before = step_data.get("before") if isinstance(step_data.get("before"), dict) else {}
    after = step_data.get("after") if isinstance(step_data.get("after"), dict) else {}
    before_node = before.get("scka_node") if isinstance(before.get("scka_node"), dict) else {}

    chunk = header.msg.data if header is not None else None
    msg_epoch = header.msg.epoch if header is not None else before_node.get("epoch")
    msg_type = header.msg.msg_type.value if header is not None else None
    self_epoch = before_node.get("epoch")
    completed = after.get("state", before.get("state")) == "NoHeaderReceived"
    output_key = step_data.get("receive_trace", {}).get("scka_output_key") if isinstance(step_data.get("receive_trace"), dict) else None

    return [
        {
            "title": "Add CT2 chunk",
            "control": ft.Column(
                controls=[
                    ft.Text("Add CT2 chunk", weight="bold"),
                    ft.Row(
                        controls=[
                            _var_node("msg.epoch", msg_epoch, "spqr_step_epoch"),
                            _flow_node("msg.type", str(msg_type), width=220, tooltip=_tt("spqr_step_msg_type"), full_value=msg_type),
                            _var_node("self.epoch", self_epoch, "spqr_step_epoch"),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=16,
                        wrap=True,
                    ),
                    ft.Text("↓", size=24),
                    _var_node("chunk", chunk, "spqr_step_chunk"),
                    ft.Text("↓", size=24),
                    _function_node(
                        "ct2_decoder.add_chunk",
                        "spqr_step_state_op",
                        full_value="ct2_decoder.add_chunk(chunk)",
                    ),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        },
        {
            "title": "Decoder.has_message()",
            "control": ft.Column(
                controls=[
                    ft.Text("Decoder.has_message()", weight="bold"),
                    _flow_node(
                        "has_message",
                        "yes" if completed else "no",
                        width=220,
                        tooltip=_tt("spqr_step_state_op"),
                        full_value=completed,
                    ),
                    ft.Text("↓", size=24),
                    _flow_node(
                        "state transition" if completed else "remain in current state",
                        str(after.get("state", before.get("state"))),
                        width=260,
                        circle=True,
                        tooltip=_tt("spqr_step_next_state"),
                        full_value=after.get("state", before.get("state")),
                    ),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        },
        {
            "title": "Output key",
            "control": ft.Column(
                controls=[
                    ft.Text("Output key", weight="bold"),
                    _var_node("output_key", output_key, "spqr_step_output_key"),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        },
    ]


def _build_receive_chain_steps(state_name: str, step_data: dict[str, Any], tooltips: dict[str, str]) -> list[dict[str, Any]]:
    builders: dict[str, Callable[[dict[str, Any], dict[str, str]], list[dict[str, Any]]]] = {
        # "KeysUnsampled": _receive_keys_unsampled,
        "KeysSampled": _receive_keys_sampled,
        "HeaderSent": _receive_header_sent,
        "Ct1Received": _receive_ct1_received,
        "EkSentCt1Received": _receive_ek_sent_ct1_received,
        "NoHeaderReceived": _receive_no_header_received,
        "HeaderReceived": _receive_header_received,
        "Ct1Sampled": _receive_ct1_sampled,
        "EkReceivedCt1Sampled": _receive_ek_received_ct1_sampled,
        "Ct1Acknowledged": _receive_ct1_acknowledged,
        "Ct2Sampled": _receive_ct2_sampled,
    }
    builder = builders.get(state_name)
    if builder is None:
        return []
    return builder(step_data, tooltips)


def _build_send_message_pipeline_steps(step_data: dict[str, Any], tooltips: dict[str, str]) -> list[dict[str, Any]]:
    header: SpqrHeader | None = step_data.get("header") if isinstance(step_data.get("header"), SpqrHeader) else None
    plaintext = step_data.get("plaintext")
    ciphertext = step_data.get("cipher")
    encrypt_trace = step_data.get("encrypt_trace") if isinstance(step_data.get("encrypt_trace"), dict) else {}

    sending_epoch = encrypt_trace.get("sending_epoch", header.msg.epoch - 1 if header is not None else "-")
    counter = encrypt_trace.get("counter", header.n if header is not None else "-")
    chain_key_before = encrypt_trace.get("chain_key_before")
    chain_key_after = encrypt_trace.get("chain_key_after")
    mk = encrypt_trace.get("mk")
    ad_header = encrypt_trace.get("ad_header")

    header_msg = header.msg if header is not None else None
    header_payload = {
        "msg": header_msg.to_dict() if header_msg is not None else None,
        "n": header.n if header is not None else None,
    }

    steps: list[dict[str, Any]] = []

    # Message key derivation step
    steps.append(
        {
            "title": "Message key derivation",
            "control": ft.Column(
                controls=[
                    ft.Text("Message key derivation", weight="bold"),
                    _var_node("sending_epoch", sending_epoch, "spqr_step_sending_epoch"),
                    ft.Text("↓", size=24),
                    _function_node("Get sending chain", f"epoch {sending_epoch}"),
                    ft.Text("↓", size=24),
                    _var_node("CKs", chain_key_before, "spqr_step_send_ck"),
                    ft.Divider(height=1),
                    ft.Row(
                        controls=[
                            _var_node("counter", counter, "spqr_step_msg_epoch"),
                            _var_node("CKs", chain_key_before, "spqr_step_send_ck"),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=16,
                        wrap=True,
                    ),
                    ft.Text("↓", size=24),
                    _function_node("KDF_SCKA_CK", "spqr_step_kdf_scka_ck"),
                    ft.Text("↓", size=24),
                    ft.Row(
                        controls=[
                            _var_node("new CKs", chain_key_after, "spqr_step_send_ck"),
                            _var_node("mk", mk, "spqr_step_output_key"),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=16,
                        wrap=True,
                    ),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        }
    )

    steps.append(
        {
            "title": "Build SPQR header",
            "control": ft.Column(
                controls=[
                    ft.Text("Build SPQR header", weight="bold"),
                    ft.Row(
                        controls=[
                            _flow_node("msg", _header_preview(header) if header is not None else "None", width=260, tooltip=_tt("spqr_step_header"), full_value=header_msg.to_dict() if header_msg is not None else None),
                            _var_node("n", header.n if header is not None else None, "spqr_step_msg_epoch"),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=16,
                        wrap=True,
                    ),
                    ft.Text("↓", size=24),
                    _function_node(
                        "Build SpqrHeader",
                        "spqr_step_build_message",
                        full_value="header = SpqrHeader(msg=msg, n=n)",
                    ),
                    ft.Text("↓", size=24),
                    _flow_node(
                        "header",
                        _header_preview(header),
                        width=420,
                        tooltip=_tt("spqr_step_header"),
                        full_value=header_payload,
                    ),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        }
    )

    pqxdh_header = step_data.get("pqxdh_header") if isinstance(step_data.get("pqxdh_header"), dict) else None
    if isinstance(pqxdh_header, dict):
        pqxdh_preview = _pqxdh_header_preview(pqxdh_header)
        combined_header_full = {
            "header": header_payload,
            "pqxdh_header": pqxdh_header,
        }
        combined_header_preview = f"{_header_preview(header)} | pqxdh: {pqxdh_preview}"
        steps.append(
            {
                "title": "Add PQXDH header data",
                "control": ft.Column(
                    controls=[
                        ft.Text("Add PQXDH header data", weight="bold"),
                        ft.Row(
                            controls=[
                                _flow_node(
                                    "PQXDH header",
                                    pqxdh_preview,
                                    width=420,
                                    full_value=pqxdh_header,
                                    tooltip=_tt("pqxdh_step_node_verify_pq"),
                                ),
                                _flow_node(
                                    "Header",
                                    _header_preview(header),
                                    width=320,
                                    full_value=header_payload,
                                    tooltip=_tt("spqr_step_header"),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=16,
                            wrap=True,
                        ),
                        ft.Text("↓", size=24),
                        _flow_node("CONCAT", circle=True, width=220, tooltip=_tt("pqxdh_step_node_verify_pq")),
                        ft.Text("↓", size=24),
                        _flow_node(
                            "Header including PQXDH data",
                            combined_header_preview,
                            width=620,
                            height=110,
                            full_value=combined_header_full,
                            tooltip=_tt("pqxdh_step_node_verify_pq"),
                        ),
                    ],
                    spacing=6,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            }
        )

    steps.append(
        {
            "title": "Encrypt message",
            "control": ft.Column(
                controls=[
                    ft.Text("Encrypt message", weight="bold"),
                    ft.Row(
                        controls=[
                            _var_node("mk", mk, "spqr_step_output_key"),
                            _var_node("plaintext", _format_plaintext(plaintext), "spqr_step_chunk"),
                            _var_node("AD||header", ad_header, "spqr_step_header_with_mac"),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=16,
                        wrap=True,
                    ),
                    ft.Text("↓", size=24),
                    _function_node(
                        "Encrypt",
                        "spqr_step_build_message",
                        full_value="ciphertext = ENCRYPT(mk, plaintext, AD || header)",
                    ),
                    ft.Text("↓", size=24),
                    _var_node("ciphertext", ciphertext, "spqr_step_msg_data"),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        }
    )

    return steps


def _build_receive_message_pipeline_steps(step_data: dict[str, Any], tooltips: dict[str, str]) -> list[dict[str, Any]]:
    header: SpqrHeader | None = step_data.get("header") if isinstance(step_data.get("header"), SpqrHeader) else None
    ciphertext = step_data.get("cipher")
    decrypted = step_data.get("decrypted")
    receive_trace = step_data.get("receive_trace") if isinstance(step_data.get("receive_trace"), dict) else {}

    receiving_epoch = receive_trace.get("receiving_epoch", header.msg.epoch - 1 if header is not None else "-")
    counter = receive_trace.get("counter", header.n if header is not None else "-")
    chain_key_before = receive_trace.get("chain_key_before")
    chain_key_after = receive_trace.get("chain_key_after")
    mk = receive_trace.get("mk")
    used_skipped_key = bool(receive_trace.get("used_skipped_key", False))
    ad_header = receive_trace.get("ad_header")

    if used_skipped_key:
        derivation_note = "MK restored from skipped-key store"
    else:
        derivation_note = "MK derived from receive chain"

    return [
        {
            "title": "Message key derivation",
            "control": ft.Column(
                controls=[
                    ft.Text("Message key derivation", weight="bold"),
                    _var_node("receiving_epoch", receiving_epoch, "spqr_step_epoch"),
                    ft.Text("↓", size=24),
                    _flow_node(
                        "Get receiving chain",
                        f"epoch {receiving_epoch}",
                        circle=True,
                        width=260,
                        tooltip=_tt("spqr_step_recv_ck"),
                        full_value={"epoch": receiving_epoch},
                    ),
                    ft.Text("↓", size=24),
                    _flow_node(
                        "MK",
                        derivation_note,
                        width=320,
                        tooltip=_tt("spqr_step_state_op"),
                        full_value={"used_skipped_key": used_skipped_key},
                    ),
                    ft.Divider(height=1),
                    ft.Row(
                        controls=[
                            _var_node("counter", counter, "spqr_step_msg_epoch"),
                            _var_node("CKr", chain_key_before, "spqr_step_recv_ck"),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=16,
                        wrap=True,
                    ),
                    ft.Text("↓", size=24),
                    _function_node("KDF_SCKA_CK", "spqr_step_kdf_scka_ck"),
                    ft.Text("↓", size=24),
                    ft.Row(
                        controls=[
                            _var_node("new CKr", chain_key_after, "spqr_step_recv_ck"),
                            _var_node("mk", mk, "spqr_step_output_key"),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=16,
                        wrap=True,
                    ),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        },
        {
            "title": "Decrypt message",
            "control": ft.Column(
                controls=[
                    ft.Text("Decrypt message", weight="bold"),
                    ft.Row(
                        controls=[
                            _var_node("mk", mk, "spqr_step_output_key"),
                            _var_node("ciphertext", ciphertext, "spqr_step_msg_data"),
                            _var_node("AD||header", ad_header, "spqr_step_header_with_mac"),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=16,
                        wrap=True,
                    ),
                    ft.Text("↓", size=24),
                    _function_node(
                        "Decrypt",
                        "spqr_step_build_message",
                        full_value="plaintext = DECRYPT(mk, ciphertext, AD || header)",
                    ),
                    ft.Text("↓", size=24),
                    _var_node("plaintext", _format_plaintext(decrypted), "spqr_step_chunk"),
                ],
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        },
    ]


def _build_after_step(
    action: str,
    state_name: str,
    before: dict[str, Any],
    after: dict[str, Any],
    tooltips: dict[str, str],
) -> dict[str, Any]:
    before_rows = _before_after_rows(before, tooltips)
    after_rows = _before_after_rows(after, tooltips)

    before_state = before.get("state", before.get("node"))
    after_state = after.get("state", after.get("node"))

    changed_labels: set[str] = set()
    if before_state != after_state:
        changed_labels.add("State")
    if before.get("epoch") != after.get("epoch"):
        changed_labels.add("Epoch")
    if before.get("direction") != after.get("direction"):
        changed_labels.add("Direction")
    if before.get("rk_tail") != after.get("rk_tail"):
        changed_labels.add("RK")
    if before.get("send_ck_tail") != after.get("send_ck_tail"):
        changed_labels.add("CKs")
    if before.get("recv_ck_tail") != after.get("recv_ck_tail"):
        changed_labels.add("CKr")

    state_comparison = ft.Row(
        controls=[
            _party_state_panel(
                "Before",
                before_rows,
                tooltip=tooltips.get("spqr_step_before_panel", ""),
                highlight_labels=changed_labels,
            ),
            _party_state_panel(
                "After",
                after_rows,
                tooltip=tooltips.get("spqr_step_after_panel", ""),
                highlight_labels=changed_labels,
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.START,
        spacing=20,
        wrap=True,
    )

    after_control = ft.Column(
        controls=[
            ft.Text("State before and after", weight="bold"),
            state_comparison,
        ],
        spacing=6,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )
    return {
        "title": "State comparison",
        "control": after_control,
    }


def show_alice_pqxdh_bootstrap_visualization_dialog(
    page: ft.Page,
    pqxdh_state_data: dict[str, Any] | None,
    rk_after_init: bytes | None,
    cks_after_init: bytes | None,
    alice_scka_state: Any = None,
    session_ad: bytes | None = None,
    on_close: Callable[[], None] | None = None,
) -> None:
    tooltips = {
        **get_tooltip_messages("pqxdh"),
        **get_tooltip_messages("spqr"),
    }

    derived = {}
    last_bundle = {}
    real_pqxdh_header = {}
    if isinstance(pqxdh_state_data, dict):
        initial_message = pqxdh_state_data.get("initial_message", {})
        if isinstance(initial_message, dict) and isinstance(initial_message.get("header"), dict):
            real_pqxdh_header = initial_message["header"]
        else:
            real_pqxdh_header = pqxdh_state_data.get("initial_header") if isinstance(pqxdh_state_data.get("initial_header"), dict) else {}
        derived = pqxdh_state_data.get("alice_derived") if isinstance(pqxdh_state_data.get("alice_derived"), dict) else {}
        last_bundle = pqxdh_state_data.get("last_bundle_for_alice") if isinstance(pqxdh_state_data.get("last_bundle_for_alice"), dict) else {}
        if not derived:
            derived = pqxdh_state_data

    shared_secret = derived.get("shared_secret_hex") if isinstance(derived.get("shared_secret_hex"), str) else derived.get("shared_secret")
    associated_data = derived.get("associated_data_hex") if isinstance(derived.get("associated_data_hex"), str) else derived.get("associated_data")
    header_preview = _pqxdh_header_preview(real_pqxdh_header)
    alice_identity_public = None
    if isinstance(pqxdh_state_data, dict):
        alice_local = pqxdh_state_data.get("alice_local", {})
        alice_identity = alice_local.get("identity_dh", {})
        alice_identity_public = alice_identity.get("public", None)

    opk_pub = last_bundle.get("opk_public") if last_bundle.get("opk_public") not in {None, "", "-"} else None
    pq_opk_pub = last_bundle.get("pq_opk_public") if last_bundle.get("pq_opk_public") not in {None, "", "-"} else None
    pq_prekey_source = last_bundle.get("pq_prekey_source", "pqspk")

    bundle_controls = [
        ft.Text("Bundle from server:", size=12, weight="bold"),
        ft.Row(
            controls=[
                _flow_node("IK_B", _last_n_chars(last_bundle.get("identity_dh_public"), 8), width=180, full_value=last_bundle.get("identity_dh_public"), tooltip=tooltips.get("x3dh_step_key_ik_pub", "")),
                _flow_node("SPK_B", _last_n_chars(last_bundle.get("signed_prekey_public"), 8), width=180, full_value=last_bundle.get("signed_prekey_public"), tooltip=tooltips.get("x3dh_step_key_spk_pub", "")),
                _flow_node("SPK_B_sig", _last_n_chars(last_bundle.get("signed_prekey_signature"), 8), width=180, full_value=last_bundle.get("signed_prekey_signature"), tooltip=tooltips.get("x3dh_step_key_spk_sig", "")),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10,
            wrap=True,
        ),
    ]
    
    if opk_pub is not None:
        bundle_controls.append(
            ft.Row(
                controls=[
                    _flow_node("OPK_B", _last_n_chars(opk_pub), width=180, full_value=opk_pub, tooltip=tooltips.get("x3dh_step_key_opk_pub", "")),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=10,
            )
        )
    
    bundle_controls.extend([
        ft.Row(
            controls=[
                _flow_node("PQSPK_B", _last_n_chars(last_bundle.get("pq_signed_prekey_public"), 8), width=180, full_value=last_bundle.get("pq_signed_prekey_public"), tooltip=tooltips.get("x3dh_step_key_pqspk_pub", "")),
                _flow_node("PQSPK_B_sig", _last_n_chars(last_bundle.get("pq_signed_prekey_signature"), 8), width=180, full_value=last_bundle.get("pq_signed_prekey_signature"), tooltip=tooltips.get("x3dh_step_key_spk_sig", "")),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10,
            wrap=True,
        ),
    ])
    
    if pq_opk_pub is not None:
        bundle_controls.append(
            ft.Row(
                controls=[
                    _flow_node(f"PQ{pq_prekey_source.upper()}_B", _last_n_chars(pq_opk_pub), width=180, full_value=pq_opk_pub, tooltip=tooltips.get("x3dh_step_key_opk_pub", "")),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=10,
            )
        )

    step1 = ft.Column(
        controls=[
            ft.Text("1) Alice requests Bob's bundle", weight="bold"),
            *bundle_controls,
        ],
        spacing=8,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    step2 = ft.Column(
        controls=[
            ft.Text("2a) Alice verifies EC signature (SPK_B_sig)", weight="bold"),
            ft.Row(
                controls=[
                    _var_node("IK_B", last_bundle.get("identity_dh_public"), "x3dh_step_key_ik_pub"),
                    _var_node("SPK_B", last_bundle.get("signed_prekey_public"), "x3dh_step_key_spk_pub"),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=12,
                wrap=True,
            ),
            ft.Text("↓", size=20),
            _function_node("VERIFY_EC", "spqr_step_state_op", full_value="Verify EC signature"),
            ft.Text("↓", size=20),
            _flow_node("Verification result", "Valid signature",width=200, tooltip=_tt("spqr_step_state_op")),
        ],
        spacing=6,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    step3 = ft.Column(
        controls=[
            ft.Text("2b) Alice verifies PQ signature (PQSPK_B_sig)", weight="bold"),
            ft.Row(
                controls=[
                    _var_node("IK_B", last_bundle.get("identity_dh_public"), "x3dh_step_key_ik_pub"),
                    _var_node("PQSPK_B", last_bundle.get("pq_signed_prekey_public"), "x3dh_step_key_pqspk_pub"),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=12,
                wrap=True,
            ),
            ft.Text("↓", size=20),
            _function_node("VERIFY_PQ", "spqr_step_state_op", full_value="Verify PQ signature"),
            ft.Text("↓", size=20),
            _flow_node("Verification result", "Valid signature",width=200, tooltip=_tt("spqr_step_state_op")),
        ],
        spacing=6,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    pqpkb_pub = pq_opk_pub if pq_opk_pub else last_bundle.get("pq_signed_prekey_public")
    pq_shared_secret = derived.get("pq_secret") if isinstance(derived.get("pq_secret"), str) else derived.get("pq_shared_secret")
    step4 = ft.Column(
        controls=[
            ft.Text("3) Alice encapsulates PQ prekey material", weight="bold"),
            _var_node("PQPKB", pqpkb_pub, "x3dh_step_key_pqspk_pub"),
            ft.Text("↓", size=20),
            _function_node("PQKEM.Encaps", "spqr_step_state_op", full_value="PQPKB -> encaps -> CT, SS"),
            ft.Text("↓", size=20),
            ft.Row(
                controls=[
                    _flow_node("CT", _last_n_chars(derived.get("kem_ciphertext"), 8), width=200, full_value=derived.get("kem_ciphertext"), tooltip=tooltips.get("pqxdh_step_key_ct", "")),
                    _flow_node("SS (from PQKEM)", _last_n_chars(pq_shared_secret), width=220, full_value=pq_shared_secret, tooltip=tooltips.get("pqxdh_step_key_ss", "")),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=12,
                wrap=True,
            ),
        ],
        spacing=6,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    step5 = ft.Column(
        controls=[
            ft.Text("4) Alice derives shared secret SK", weight="bold"),
            ft.Row(
                controls=[
                    _function_node("DH1", "spqr_step_state_op", full_value="DH(IKA_priv, SPK_B)"),
                    _function_node("DH2", "spqr_step_state_op", full_value="DH(EKA_priv, IK_B)"),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=12,
                wrap=True,
            ),
            ft.Row(
                controls=[
                    _function_node("DH3", "spqr_step_state_op", full_value="DH(EKA_priv, SPK_B)"),
                    _function_node("DH4", "spqr_step_state_op", full_value="DH(EKA_priv, OPK_B)"),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=12,
                wrap=True,
            ),
            _flow_node("SS (from PQKEM)", _last_n_chars(pq_shared_secret), width=240, full_value=pq_shared_secret, tooltip=tooltips.get("pqxdh_step_key_ss", "")),
            ft.Text("↓", size=20),
            _function_node("KDF_SK", "spqr_step_state_op", full_value="KDF_SK(DH1 || DH2 || DH3 || DH4 || SS)"),
            ft.Text("↓", size=20),
            _var_node("SK", shared_secret, "pqxdh_step_key_ss"),
        ],
        spacing=6,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    step6 = ft.Column(
        controls=[
            ft.Text("5) Alice computes associated data and builds PQXDH header prefix", weight="bold"),
            ft.Row(
                controls=[
                    _flow_node("IK_A", _last_n_chars(alice_identity_public), width=220, full_value=alice_identity_public, tooltip=tooltips.get("x3dh_step_key_ik_pub", "")),
                    _flow_node("IK_B", _last_n_chars(last_bundle.get("identity_dh_public")), width=220, full_value=last_bundle.get("identity_dh_public"), tooltip=tooltips.get("x3dh_step_key_ik_pub", "")),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=12,
                wrap=True,
            ),
            ft.Text("↓", size=20),
            _function_node("CALC_AD", "spqr_step_state_op", full_value="IK_A, IK_B -> CALC_AD"),
            ft.Text("↓", size=20),
            _var_node("AD", associated_data, "pqxdh_step_key_ad"),
            ft.Divider(height=1),
            _flow_node("PQXDH header prefix", header_preview, width=580, full_value=real_pqxdh_header, tooltip=tooltips.get("pqxdh_step_node_verify_pq", "")),
        ],
        spacing=6,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    ckr_value = None
    if alice_scka_state is not None and hasattr(alice_scka_state, "kdfchains"):
        try:
            chains = alice_scka_state.kdfchains.get(alice_scka_state.epoch)
            if chains and hasattr(chains, "receive"):
                ckr_value = chains.receive.CK
        except Exception:
            pass

    step7 = ft.Column(
        controls=[
            ft.Text("6) Initialize Alice SPQR session state", weight="bold"),
            _var_node("SK", shared_secret, "pqxdh_step_key_ss"),
            ft.Text("↓", size=20),
            _function_node("RatchetInitAliceSCKA(SK)", "spqr_step_state_op", full_value="Initialize ratchet state"),
            ft.Text("↓", size=20),
            ft.Row(
                controls=[
                    _var_node("RK", rk_after_init, "spqr_step_rk"),
                    _var_node("CKs", cks_after_init, "spqr_step_send_ck"),
                    _var_node("CKr", ckr_value, "spqr_step_recv_ck"),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=12,
                wrap=True,
            ),
            ft.Divider(height=1),
            _flow_node("Direction", "A2B", width=200, tooltip=_tt("spqr_step_direction"), full_value="A2B"),
        ],
        spacing=6,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    steps = [
        {"title": "Alice requests Bob bundle", "control": step1},
        {"title": "Alice verifies EC signature", "control": step2},
        {"title": "Alice verifies PQ signature", "control": step3},
        {"title": "Alice encapsulates ephemeral KEM", "control": step4},
        {"title": "Alice derives shared secret SK", "control": step5},
        {"title": "Alice computes AD and header prefix", "control": step6},
        {"title": "Alice initializes SPQR state", "control": step7},
    ]
    _normalize_step_titles(steps)
    _show_step_dialog(page, "SPQR Alice bootstrap", steps, on_close=on_close)


def show_bob_pqxdh_bootstrap_visualization_dialog(
    page: ft.Page,
    pqxdh_header: dict[str, Any] | None,
    shared_secret: bytes | None,
    session_ad: bytes | None,
    bob_state: SpqrRatchetState | None,
    bob_ik_public: str | None = None,
    pq_shared_secret: bytes | None = None,
    bob_pq_prekey_public: str | None = None,
    on_close: Callable[[], None] | None = None,
) -> None:
    tooltips = {
        **get_tooltip_messages("pqxdh"),
        **get_tooltip_messages("spqr"),
    }

    header_preview = _pqxdh_header_preview(pqxdh_header)

    ik_a_public = pqxdh_header.get("ik_a_public") if isinstance(pqxdh_header, dict) else None
    kem_ciphertext = pqxdh_header.get("pq_ciphertext") if isinstance(pqxdh_header, dict) else None
    if kem_ciphertext is None and isinstance(pqxdh_header, dict):
        kem_ciphertext = pqxdh_header.get("kem_ciphertext")

    rk_value = bob_state.RK if bob_state is not None else None
    chains = bob_state.kdfchains.get(bob_state.epoch) if bob_state is not None else None
    ckr_value = chains.receive.CK if chains is not None and chains.receive is not None else None
    cks_value = chains.send.CK if chains is not None and chains.send is not None else None
    rk_after_init = rk_value
    cks_after_init = cks_value

    step1 = ft.Column(
        controls=[
            ft.Text("1) Extract PQXDH header", weight="bold"),
            _flow_node(
                "Received PQXDH header",
                header_preview,
                width=560,
                full_value=pqxdh_header,
                tooltip=tooltips.get("pqxdh_step_node_verify_pq", ""),
            ),
            ft.Text("↓", size=24),
            _function_node(
                "Extract components",
                "spqr_step_state_op",
                full_value="Extract ik_a, ek_a, bob_spk, pq_id, CT"
            ),
        ],
        spacing=6,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # Step 2: Decapsulate KEM
    step2 = ft.Column(
        controls=[
            ft.Text("2) Decapsulate KEM ciphertext", weight="bold"),
            ft.Row(
                controls=[
                    _var_node("CT", kem_ciphertext, "pqxdh_step_key_ct"),
                    _var_node("PQPKB", bob_pq_prekey_public, "x3dh_step_key_pqspk_pub"),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=12,
                wrap=True,
            ),
            ft.Text("↓", size=24),
            _function_node(
                "PQKEM.Decaps",
                "spqr_step_state_op",
                full_value="CT + Bob_pq_privkey -> SS"
            ),
            ft.Text("↓", size=24),
            _var_node(
                "SS (PQ shared secret)",
                pq_shared_secret,
                "pqxdh_step_key_ss",
            ),
        ],
        spacing=6,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    step3 = ft.Column(
        controls=[
            ft.Text("3) Calculate shared secret SK", weight="bold"),
            ft.Row(
                controls=[
                    _flow_node("DH1", "DH(Bob_priv_spk, EK_A)", width=320, full_value="Bob_priv_spk + EK_A -> DH1", tooltip=tooltips.get("x3dh_step_node_dh", "")),
                    _flow_node("DH2", "DH(Bob_priv_ik, EK_A)", width=320, full_value="Bob_priv_ik + EK_A -> DH2", tooltip=tooltips.get("x3dh_step_node_dh", "")),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=12,
                wrap=True,
            ),
            ft.Row(
                controls=[
                    _flow_node("DH3", "DH(Bob_priv_spk, EK_A)", width=320, full_value="Bob_priv_spk + EK_A -> DH3", tooltip=tooltips.get("x3dh_step_node_dh", "")),
                    _flow_node("DH4", "DH(Bob_priv_ik, EK_A)", width=320, full_value="Bob_priv_ik + EK_A -> DH4", tooltip=tooltips.get("x3dh_step_node_dh", "")),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=12,
                wrap=True,
            ),
            _var_node(
                "SS (from PQKEM)",
                pq_shared_secret,
                "pqxdh_step_key_ss",
            ),
            ft.Text("↓", size=24),
            _function_node(
                "KDF_SK",
                "spqr_step_state_op",
                full_value="KDF_SK(DH1 || DH2 || DH3 || DH4 || SS)"
            ),
            ft.Text("↓", size=24),
            _var_node("SK", shared_secret, "pqxdh_step_key_ss"),
        ],
        spacing=6,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # Step 4: Calculate AD
    step4 = ft.Column(
        controls=[
            ft.Text("4) Calculate associated data AD", weight="bold"),
            ft.Row(
                controls=[
                    _flow_node("IK_A", _last_n_chars(ik_a_public, 8), width=220, full_value=ik_a_public, tooltip=tooltips.get("x3dh_step_key_ik_pub", "")),
                    _flow_node("IK_B", _last_n_chars(bob_ik_public, 8), width=220, full_value=bob_ik_public, tooltip=tooltips.get("x3dh_step_key_ik_pub", "")),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=12,
                wrap=True,
            ),
            ft.Text("↓", size=24),
            _function_node("CALC_AD", "spqr_step_state_op", full_value="IK_A, IK_B -> CALC_AD"),
            ft.Text("↓", size=24),
            _var_node("AD", session_ad, "pqxdh_step_key_ad"),
        ],
        spacing=6,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # Step 5: Initialize SCKA
    step5 = ft.Column(
        controls=[
            ft.Text("5) Initialize Bob SCKA state", weight="bold"),
            _var_node("SK", shared_secret, "pqxdh_step_key_ss"),
            ft.Text("↓", size=20),
            _function_node(
                "RatchetInitBobSCKA",
                "spqr_step_state_op",
                full_value="RatchetInitBobSCKA(SK, AD)"
            ),
            ft.Text("↓", size=24),
            ft.Row(
                controls=[
                    _var_node("RK", rk_after_init, "spqr_step_rk"),
                    _var_node("CKs", cks_after_init, "spqr_step_send_ck"),
                    _var_node("CKr", ckr_value, "spqr_step_recv_ck"),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=12,
                wrap=True,
            ),
            ft.Divider(height=1),
            _flow_node(
                "Direction",
                "B2A (Bob receives, Alice sends)",
                width=280,
                tooltip=tooltips.get("spqr_step_direction", ""),
                full_value="B2A"
            ),
        ],
        spacing=6,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    steps = [
        {"title": "Extract PQXDH header", "control": step1},
        {"title": "Decapsulate KEM ciphertext", "control": step2},
        {"title": "Calculate shared secret SK", "control": step3},
        {"title": "Calculate associated data AD", "control": step4},
        {"title": "Initialize Bob SCKA state", "control": step5},
    ]
    _normalize_step_titles(steps)
    _show_step_dialog(page, "SPQR Bob PQXDH bootstrap", steps, on_close=on_close)


def _pqxdh_header_preview(pqxdh_header: dict[str, Any] | None) -> str:
    if not isinstance(pqxdh_header, dict):
        return "None"

    ik_a = _last_n_chars(pqxdh_header.get("ik_a_public"), 8)
    ek_a = _last_n_chars(pqxdh_header.get("ek_a_public"), 8)
    bob_spk = _last_n_chars(pqxdh_header.get("bob_spk_public"), 8)
    pq_prekey_id = pqxdh_header.get("bob_pq_prekey_id")
    pq_prekey_text = str(pq_prekey_id) if pq_prekey_id is not None else "None"
    return f"ik_a={ik_a}, ek_a={ek_a}, spk_b={bob_spk}, pq_id={pq_prekey_text}"


def _build_pqxdh_header_split_step(
    step_data: dict[str, Any],
    tooltips: dict[str, str],
) -> dict[str, Any] | None:
    pqxdh_header = step_data.get("pqxdh_header") if isinstance(step_data.get("pqxdh_header"), dict) else None
    header: SpqrHeader | None = step_data.get("header") if isinstance(step_data.get("header"), SpqrHeader) else None
    if not isinstance(pqxdh_header, dict):
        return None

    header_msg = header.msg if header is not None else None
    header_payload = {
        "msg": header_msg.to_dict() if header_msg is not None else None,
        "n": header.n if header is not None else None,
    }
    combined_header_full = {
        "header": header_payload,
        "pqxdh_header": pqxdh_header,
    }
    combined_header_preview = f"{_header_preview(header)} | pqxdh: {_pqxdh_header_preview(pqxdh_header)}"

    return {
        "title": "Header split (PQXDH metadata extraction)",
        "control": ft.Column(
            controls=[
                ft.Text("Header split (PQXDH metadata extraction)", weight="bold"),
                _flow_node(
                    "Complete header",
                    combined_header_preview,
                    width=620,
                    full_value=combined_header_full,
                    tooltip=tooltips.get("pqxdh_step_node_verify_pq", ""),
                ),
                ft.Text("↓", size=24),
                _flow_node(
                    "SPLIT",
                    "",
                    width=200,
                    height=70,
                    circle=True,
                    tooltip=tooltips.get("spqr_step_state_op", ""),
                ),
                ft.Text("↓", size=24),
                ft.Row(
                    controls=[
                        _flow_node(
                            "Message header",
                            _header_preview(header),
                            width=280,
                            full_value=header_payload,
                            tooltip=tooltips.get("spqr_step_header", ""),
                        ),
                        _flow_node(
                            "PQXDH header",
                            _pqxdh_header_preview(pqxdh_header),
                            width=420,
                            full_value=pqxdh_header,
                            tooltip=tooltips.get("pqxdh_step_node_verify_pq", ""),
                            bgcolor=ft.Colors.SECONDARY_CONTAINER,
                            text_color=ft.Colors.ON_SECONDARY_CONTAINER,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=16,
                    wrap=True,
                ),
            ],
            spacing=6,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    }


def _build_pqxdh_bootstrap_init_step(
    step_data: dict[str, Any],
    tooltips: dict[str, str],
    on_show_pqxdh_bootstrap: Callable[[], None] | None = None,
) -> dict[str, Any] | None:
    pqxdh_header = step_data.get("pqxdh_header") if isinstance(step_data.get("pqxdh_header"), dict) else None
    if not isinstance(pqxdh_header, dict):
        return None

    was_bootstrapped = bool(step_data.get("was_pqxdh_bootstrapped", False))
    already_initialized = not was_bootstrapped

    controls: list[ft.Control] = [
        ft.Text("PQXDH initialization (party bootstrap)", weight="bold"),
        _flow_node(
            "Party status",
            "Bob already initialized" if already_initialized else "Bob not initialized yet",
            width=320,
            tooltip=tooltips.get("spqr_step_state_op", ""),
            full_value=already_initialized,
            bgcolor=ft.Colors.SECONDARY_CONTAINER if already_initialized else ft.Colors.ERROR_CONTAINER,
            text_color=ft.Colors.ON_SECONDARY_CONTAINER if already_initialized else ft.Colors.ON_ERROR_CONTAINER,
        ),
        ft.Divider(height=1),
    ]

    if was_bootstrapped:
        controls.extend([
            _flow_node(
                "PQXDH header",
                _pqxdh_header_preview(pqxdh_header),
                width=420,
                full_value=pqxdh_header,
                tooltip=tooltips.get("pqxdh_step_node_verify_pq", ""),
            ),
            ft.Text("↓", size=24),
            _flow_node(
                "PQXDH Bootstrap",
                "Initialize SPQR state from PQXDH",
                width=360,
                height=90,
                circle=True,
                tooltip=tooltips.get("spqr_step_state_op", ""),
            ),
        ])
        if on_show_pqxdh_bootstrap is not None:
            controls.append(
                ft.Column(
                    controls=[
                        ft.Text("Click button to view detailed bootstrap steps:", size=12),
                        ft.Button("Show Bob SPQR PQXDH bootstrap", on_click=lambda _: on_show_pqxdh_bootstrap()),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=10,
                )
            )
        controls.extend([
            ft.Text("↓", size=24),
            _flow_node(
                "Result",
                "Bob was initialized during this receive",
                width=380,
                tooltip=tooltips.get("spqr_step_state_op", ""),
            ),
        ])

    return {
        "title": "PQXDH initialization (party bootstrap)",
        "control": ft.Column(
            controls=controls,
            spacing=6,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    }


def _normalize_step_titles(steps: list[dict[str, Any]]) -> None:
    for index, step in enumerate(steps):
        numbered_title = f"{index + 1}) {step['title']}"
        step["title"] = numbered_title
        control = step.get("control")
        if isinstance(control, ft.Column) and control.controls and isinstance(control.controls[0], ft.Text):
            control.controls[0].value = numbered_title


def show_spqr_step_visualization_dialog(
    page: ft.Page,
    step_data: dict[str, Any],
    on_close: Callable[[], None] | None = None,
    on_show_pqxdh_bootstrap: Callable[[], None] | None = None,
) -> None:
    tooltips = {
        **get_tooltip_messages("spqr"),
        **get_tooltip_messages("pqxdh"),
    }
    action = str(step_data.get("action", "send")).strip().lower()
    after = step_data.get("after") if isinstance(step_data.get("after"), dict) else {}
    header: SpqrHeader | None = step_data.get("header") if isinstance(step_data.get("header"), SpqrHeader) else None
    before = step_data.get("before") if isinstance(step_data.get("before"), dict) else {}
    state_name = str(before.get("state", before.get("node", "Unknown")))

    steps: list[dict[str, Any]] = [
        _build_intro_step(before, tooltips)
    ]

    if action == "receive":
        header_split_step = _build_pqxdh_header_split_step(step_data, tooltips)
        if header_split_step is not None:
            steps.append(header_split_step)
        bootstrap_init_step = _build_pqxdh_bootstrap_init_step(step_data, tooltips, on_show_pqxdh_bootstrap)
        if bootstrap_init_step is not None:
            steps.append(bootstrap_init_step)

    chain_steps = (
        _build_send_steps(state_name, step_data, tooltips)
        if action == "send"
        else _build_receive_chain_steps(state_name, step_data, tooltips)
    )
    steps.extend(chain_steps)

    steps.append(_build_output_key_step(action, state_name, before, after, header, tooltips))
    rk_derivation_step = _build_rk_derivation_step(action, state_name, before, after, step_data)
    if rk_derivation_step is not None:
        steps.append(rk_derivation_step)
    if action == "send":
        steps.extend(_build_send_message_pipeline_steps(step_data, tooltips))
    if action == "receive":
        steps.extend(_build_receive_message_pipeline_steps(step_data, tooltips))
    steps.append(_build_after_step(action, str(after.get("state", after.get("node", state_name))), before, after, tooltips))

    _normalize_step_titles(steps)
    dialog_title = f"SPQR {action.capitalize()} visualization:"
    _show_step_dialog(page, dialog_title, steps, on_close=on_close)
