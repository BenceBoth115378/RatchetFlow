from __future__ import annotations

from components.data_classes import PQXDHState, X3DHState
from modules import external as ext
from modules.base_logic import BaseLogic

KeyExchangeState = X3DHState | PQXDHState


class KeyExchangeBaseLogic(BaseLogic):
    """Shared logic-layer base for key-exchange protocols (X3DH, PQXDH, ...)."""


def _generate_dh_key_pair() -> dict[str, str]:
    pair = ext.GENERATE_DH()
    return {
        "private": pair.private,
        "public": pair.public,
    }


def add_event(state: KeyExchangeState, message: str) -> None:
    state.events.append(message)


def ensure_alice_local(state: KeyExchangeState) -> dict:
    alice = state.alice_local
    if not isinstance(alice, dict):
        raise ValueError("Alice must generate keys first.")
    return alice


def ensure_bob_local(state: KeyExchangeState) -> dict:
    bob = state.bob_local
    if not isinstance(bob, dict):
        raise ValueError("Bob local state is missing.")
    return bob


def is_phase1_done(state: KeyExchangeState) -> bool:
    return isinstance(state.server_state.get("alice_bundle"), dict)


def is_phase2_done(state: KeyExchangeState) -> bool:
    derived = state.alice_derived
    return isinstance(derived, dict) and isinstance(derived.get("associated_data"), str)


def alice_calculates_associated_data(state: KeyExchangeState) -> None:
    alice = ensure_alice_local(state)
    derived = state.alice_derived
    bundle = state.last_bundle_for_alice
    if not isinstance(derived, dict) or not isinstance(bundle, dict):
        raise ValueError("Derive SK first.")

    associated_data = ext.CALC_AD(
        initiator_identity_public=alice["identity_dh"]["public"],
        responder_identity_public=bundle["identity_dh_public"],
    )

    derived["associated_data"] = associated_data
    add_event(state, "Alice calculated Associated Data (AD).")


__all__ = [
    "KeyExchangeBaseLogic",
    "KeyExchangeState",
    "_generate_dh_key_pair",
    "add_event",
    "alice_calculates_associated_data",
    "ensure_alice_local",
    "ensure_bob_local",
    "is_phase1_done",
    "is_phase2_done",
]
FAMILY_ID = "key_exchange"
