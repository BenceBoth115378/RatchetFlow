"""Key history tracking utilities for the SPQR module."""

from typing import Any

from components.data_classes import (
    KeyEvent,
    SpqrRatchetState,
    SpqrSessionState,
)


def _keys_differ(key1: Any, key2: Any) -> bool:
    """Return True when key values changed."""
    if key1 is None and key2 is None:
        return False
    if key1 is None or key2 is None:
        return True
    return key1 != key2


def _tail(value: bytes | None, size: int = 12) -> str:
    """Get hex tail of bytes value."""
    if value is None:
        return "None"
    text = value.hex() if isinstance(value, bytes) else str(value)
    if len(text) <= size:
        return text
    return text[-size:]


def initialize_key_history(session: SpqrSessionState) -> None:
    """Seed initial key history entries after session initialization."""
    for party in (session.alice, session.bob):
        if party is None:
            continue
        history = party.key_history
        
        if party.RK and not history.rk_events:
            history.add_rk_event(
                KeyEvent(
                    key_type="RK",
                    key_number=0,
                    key_value=party.RK,
                    created_at_step="init",
                    created_in_context="Initial root key",
                    party=party.direction,
                    start_send_n=0,
                    start_recv_n=0,
                    used_for=["session bootstrap"],
                )
            )
        
        # Track initial chain keys for epoch 0
        chains_epoch_0 = party.kdfchains.get(0)
        if chains_epoch_0 is not None:
            if chains_epoch_0.send is not None and not history.cks_events:
                history.add_cks_event(
                    KeyEvent(
                        key_type="CK",
                        key_number=0,
                        key_value=chains_epoch_0.send.CK,
                        created_at_step="init",
                        created_in_context="Initial sending chain key (epoch 0)",
                        party=party.direction,
                        direction="send",
                        start_n=0,
                        used_for=["outgoing chain"],
                    )
                )
            if chains_epoch_0.receive is not None and not history.ckr_events:
                history.add_ckr_event(
                    KeyEvent(
                        key_type="CK",
                        key_number=0,
                        key_value=chains_epoch_0.receive.CK,
                        created_at_step="init",
                        created_in_context="Initial receiving chain key (epoch 0)",
                        party=party.direction,
                        direction="recv",
                        start_n=0,
                        used_for=["incoming chain"],
                    )
                )


def track_keys_from_send_step(
    party: SpqrRatchetState,
    party_name: str,
    message_id: int,
    before: dict[str, Any],
    after: dict[str, Any],
) -> None:
    """Track keys after a send step."""
    before_rk = before.get("rk_tail")
    after_rk = after.get("rk_tail")
    
    # Track RK changes
    if before_rk != after_rk and after_rk not in {None, "None"}:
        # RK was ratcheted
        before_epoch = before.get("epoch", 0)
        after_epoch = after.get("epoch", 0)
        if before_epoch != after_epoch:
            party.key_history.add_rk_event(
                KeyEvent(
                    key_type="RK",
                    key_number=0,
                    key_value=after_rk,
                    created_at_step=f"send#{message_id}:epoch{after_epoch}",
                    created_in_context=f"Root key after epoch transition (send message #{message_id})",
                    party=party_name,
                    start_send_n=0,
                    start_recv_n=0,
                    used_for=[f"message #{message_id}"],
                )
            )
    
    # Track CK send changes
    before_ck_s = before.get("send_ck_tail")
    after_ck_s = after.get("send_ck_tail")
    if before_ck_s != after_ck_s and after_ck_s not in {None, "None"}:
        latest_cks = party.key_history.cks_events[-1].key_value if party.key_history.cks_events else None
        latest_cks_tail = _tail(latest_cks) if isinstance(latest_cks, bytes) else str(latest_cks)
        if before_ck_s != latest_cks_tail:
            party.key_history.add_cks_event(
                KeyEvent(
                    key_type="CK",
                    key_number=0,
                    key_value=before_ck_s,
                    created_at_step=f"send#{message_id}",
                    created_in_context=f"Sending chain key used (msg #{message_id}, epoch {before.get('epoch', 0)})",
                    party=party_name,
                    direction="send",
                    start_n=message_id,
                    used_for=[f"message #{message_id}"],
                )
            )


def track_keys_from_receive_step(
    party: SpqrRatchetState,
    party_name: str,
    message_id: int,
    before: dict[str, Any],
    after: dict[str, Any],
) -> None:
    """Track keys after a receive step."""
    before_rk = before.get("rk_tail")
    after_rk = after.get("rk_tail")
    
    # Track RK changes
    if before_rk != after_rk and after_rk not in {None, "None"}:
        before_epoch = before.get("epoch", 0)
        after_epoch = after.get("epoch", 0)
        if before_epoch != after_epoch:
            party.key_history.add_rk_event(
                KeyEvent(
                    key_type="RK",
                    key_number=0,
                    key_value=after_rk,
                    created_at_step=f"receive#{message_id}:epoch{after_epoch}",
                    created_in_context=f"Root key after epoch transition (received message #{message_id})",
                    party=party_name,
                    start_send_n=0,
                    start_recv_n=0,
                    used_for=[f"message #{message_id}"],
                )
            )
    
    # Track CK receive changes
    before_ck_r = before.get("recv_ck_tail")
    after_ck_r = after.get("recv_ck_tail")
    if before_ck_r != after_ck_r and before_ck_r not in {None, "None"}:
        latest_ckr = party.key_history.ckr_events[-1].key_value if party.key_history.ckr_events else None
        latest_ckr_tail = _tail(latest_ckr) if isinstance(latest_ckr, bytes) else str(latest_ckr)
        if before_ck_r != latest_ckr_tail:
            party.key_history.add_ckr_event(
                KeyEvent(
                    key_type="CK",
                    key_number=0,
                    key_value=before_ck_r,
                    created_at_step=f"receive#{message_id}",
                    created_in_context=f"Receiving chain key used (msg #{message_id}, epoch {before.get('epoch', 0)})",
                    party=party_name,
                    direction="recv",
                    start_n=message_id,
                    used_for=[f"message #{message_id}"],
                )
            )



def get_key_display_label(key_type: str, key_number: int) -> str:
    return f"{key_type}#{key_number}"


def get_key_tooltip_text(event: KeyEvent) -> str:
    """Build tooltip text for key history entries."""
    lines = []

    lines.append(f"Type: {event.key_type} (#{event.key_number})")
    lines.append(f"Generated: {event.created_at_step}")
    lines.append(f"Context: {event.created_in_context}")

    key_hex = (
        event.key_value.hex()
        if isinstance(event.key_value, bytes)
        else str(event.key_value)
    )
    lines.append(f"Value (last 16 chars): ...{key_hex[-16:]}")

    if event.used_for:
        lines.append(f"Used in: {', '.join(event.used_for[:3])}")
        if len(event.used_for) > 3:
            lines.append(f"  ... and {len(event.used_for) - 3} more")
    else:
        lines.append("Not yet used")

    return "\n".join(lines)
