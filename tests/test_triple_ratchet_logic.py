from __future__ import annotations

import hashlib
import itertools
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from components.data_classes import (  # noqa: E402
    DHKeyPair,
    DRHeader,
    PartyState,
    SpqrMessageType,
    SpqrSckaMessage,
)
from modules.messaging.spqr import logic as spqr_logic  # noqa: E402
from modules.messaging.triple_ratchet import logic  # noqa: E402


@pytest.fixture(autouse=True)
def deterministic_crypto(monkeypatch: pytest.MonkeyPatch):
    pair_ids = itertools.count(1)
    private_by_public: dict[str, str] = {}

    def fake_generate_dh() -> DHKeyPair:
        index = next(pair_ids)
        private_hex = f"{index:064x}"
        public_hex = f"{index + 1000:064x}"
        private_by_public[public_hex] = private_hex
        return DHKeyPair(private=private_hex, public=public_hex)

    def fake_dh(dh_pair, dh_pub: str) -> bytes:
        if isinstance(dh_pair, dict):
            private_hex = dh_pair["private"]
        else:
            private_hex = dh_pair.private

        peer_private_hex = private_by_public.get(dh_pub, dh_pub)
        shared_parts = sorted([private_hex, peer_private_hex])
        return hashlib.sha256("|".join(shared_parts).encode("utf-8")).digest()

    def fake_kdf_rk(rk: bytes, dh_out: bytes) -> tuple[bytes, bytes]:
        material = rk + b"|" + dh_out
        return (
            hashlib.sha256(material + b"|root").digest(),
            hashlib.sha256(material + b"|chain").digest(),
        )

    def fake_kdf_ck(ck: bytes) -> tuple[bytes, bytes]:
        next_ck = hashlib.sha256(ck + b"|next").digest()
        mk = hashlib.sha256(ck + b"|msg").digest()
        return next_ck, mk

    def fake_header(dh_pair: DHKeyPair, pn: int, n: int) -> DRHeader:
        return DRHeader(dh=dh_pair.public, pn=pn, n=n)

    def fake_concat(ad: bytes, header) -> bytes:
        if ad is None:
            ad = b""
        payload = {"dh": header.dh, "pn": header.pn, "n": header.n}
        return ad + b"|" + json.dumps(payload, sort_keys=True).encode("utf-8")

    def fake_encrypt(mk: bytes, plaintext: bytes, associated_data: bytes) -> bytes:
        tag = hashlib.sha256(mk + associated_data).digest()[:8]
        return b"ct:" + tag + plaintext

    def fake_decrypt(mk: bytes, ciphertext: bytes, associated_data: bytes) -> bytes:
        prefix = b"ct:"
        if not ciphertext.startswith(prefix):
            raise ValueError("Unexpected ciphertext format")
        body = ciphertext[len(prefix):]
        if len(body) < 8:
            raise ValueError("Ciphertext too short")
        expected_tag = hashlib.sha256(mk + associated_data).digest()[:8]
        actual_tag = body[:8]
        if actual_tag != expected_tag:
            raise ValueError("Authentication failed")
        return body[8:]

    monkeypatch.setattr(logic.ext, "GENERATE_DH", fake_generate_dh)
    monkeypatch.setattr(logic.ext, "DH", fake_dh)
    monkeypatch.setattr(logic.ext, "KDF_RK", fake_kdf_rk)
    monkeypatch.setattr(logic.ext, "KDF_CK", fake_kdf_ck)
    monkeypatch.setattr(logic.ext, "HEADER", fake_header)
    monkeypatch.setattr(logic.ext, "CONCAT", fake_concat)
    monkeypatch.setattr(logic.ext, "ENCRYPT", fake_encrypt)
    monkeypatch.setattr(logic.ext, "DECRYPT", fake_decrypt)


@pytest.fixture()
def deterministic_spqr(monkeypatch: pytest.MonkeyPatch):
    counter = itertools.count(1)

    def fake_send(_state):
        idx = next(counter)
        msg = SpqrSckaMessage(epoch=1, msg_type=SpqrMessageType.NONE, data=b"")
        pq_mk = hashlib.sha256(f"pq:{idx}".encode("utf-8")).digest()
        trace = {"counter": idx}
        return msg, idx, pq_mk, trace

    def fake_receive(_state, header):
        idx = header.n
        pq_mk = hashlib.sha256(f"pq:{idx}".encode("utf-8")).digest()
        trace = {"counter": idx}
        return pq_mk, trace

    monkeypatch.setattr(logic, "SCKARatchetSendKey", fake_send)
    monkeypatch.setattr(logic, "SCKARatchetReceiveKey", fake_receive)


def _bootstrap_triple_states() -> tuple[PartyState, object, PartyState, object]:
    shared_secret = hashlib.sha256(b"triple-ratchet-shared-secret").digest()
    sk_dr, sk_spqr = logic.KDF_TR_SPLIT(shared_secret)

    bob_spk_pair = logic.ext.GENERATE_DH()

    alice_dr = PartyState("Alice")
    bob_dr = PartyState("Bob")
    logic.RatchetInitAlice(alice_dr, sk_dr, bob_spk_pair.public)
    logic.RatchetInitBobTripleRatchet(bob_dr, sk_dr, bob_spk_pair)

    alice_spqr = spqr_logic.RatchetInitAliceSCKA(sk_spqr)
    bob_spqr = spqr_logic.RatchetInitBobSCKA(sk_spqr)

    return alice_dr, alice_spqr, bob_dr, bob_spqr


def test_kdf_tr_split_produces_distinct_seeds():
    sk = hashlib.sha256(b"split-seed").digest()

    sk_dr, sk_spqr = logic.KDF_TR_SPLIT(sk)

    assert len(sk_dr) == 32
    assert len(sk_spqr) == 32
    assert sk_dr != sk_spqr

    sk_dr2, sk_spqr2 = logic.KDF_TR_SPLIT(sk)
    assert sk_dr2 == sk_dr
    assert sk_spqr2 == sk_spqr


def test_initialize_session_from_pqxdh_sets_alice_only():
    sk = hashlib.sha256(b"pqxdh-shared-secret").digest()
    bob_spk = logic.ext.GENERATE_DH()

    session = logic.initialize_session_from_pqxdh(sk, bob_spk)

    assert session.alice is not None
    assert session.bob is None
    assert session.message_log == []
    assert session.alice.dr.DHr == bob_spk.public
    assert session.alice.spqr.direction == "A2B"


def test_ratchet_init_bob_triple_ratchet_sets_dh_and_root_key():
    sk = hashlib.sha256(b"bob-init-seed").digest()
    sk_dr, _ = logic.KDF_TR_SPLIT(sk)
    bob_spk = logic.ext.GENERATE_DH()
    bob_dr = PartyState("Bob")

    logic.RatchetInitBobTripleRatchet(bob_dr, sk_dr, bob_spk)

    assert bob_dr.DHs == bob_spk
    assert bob_dr.RK == sk_dr
    assert bob_dr.CKs is None


def test_triple_ratchet_encrypt_decrypt_roundtrip(deterministic_spqr):
    alice_dr, alice_spqr, bob_dr, bob_spqr = _bootstrap_triple_states()

    header, cipher, ec_mk, pq_mk, mk, _dr_trace, _spqr_trace = logic.TripleRatchetEncrypt(
        alice_dr,
        alice_spqr,
        b"hello",
        b"ad",
    )

    plaintext, ec_mk_2, pq_mk_2, mk_2, _dr_trace_2, _spqr_trace_2 = logic.TripleRatchetDecrypt(
        bob_dr,
        bob_spqr,
        header,
        cipher,
        b"ad",
    )

    assert plaintext == b"hello"
    assert ec_mk_2 == ec_mk
    assert pq_mk_2 == pq_mk
    assert mk_2 == mk
    assert mk == logic.KDF_HYBRID(ec_mk, pq_mk)
    assert header.spqr.n == 1


def test_triple_ratchet_decrypt_rejects_wrong_ad(deterministic_spqr):
    alice_dr, alice_spqr, bob_dr, bob_spqr = _bootstrap_triple_states()

    header, cipher, _ec_mk, _pq_mk, _mk, _dr_trace, _spqr_trace = logic.TripleRatchetEncrypt(
        alice_dr,
        alice_spqr,
        b"payload",
        b"ad-ok",
    )

    with pytest.raises(ValueError, match="Authentication failed"):
        logic.TripleRatchetDecrypt(
            bob_dr,
            bob_spqr,
            header,
            cipher,
            b"ad-wrong",
        )
