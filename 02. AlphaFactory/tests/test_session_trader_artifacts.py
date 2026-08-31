from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

import pytest


ALPHA_ROOT = Path(__file__).resolve().parents[1]
if str(ALPHA_ROOT) not in sys.path:
    sys.path.insert(0, str(ALPHA_ROOT))

from session_trader.artifacts import (  # noqa: E402
    ArtifactExistsError,
    ArtifactIntegrityError,
    ArtifactStore,
    HashChainLedger,
    canonical_json_bytes,
    verify_artifact,
)
from session_trader.models import (  # noqa: E402
    Bias,
    KeyZone,
    Scenario,
    SessionConstraints,
    SessionName,
    SessionPlan,
    Stance,
)


NOW = datetime(2026, 8, 27, 6, 0, tzinfo=timezone.utc)


def _plan(version: int = 1, supersedes_sha256: str | None = None) -> SessionPlan:
    return SessionPlan(
        plan_id="SESSION_PLAN_2026-08-27_LONDON",
        version=version,
        session_date=date(2026, 8, 27),
        session=SessionName.LONDON,
        created_at_utc=NOW + timedelta(minutes=version - 1),
        market_asof_utc=NOW + timedelta(minutes=version - 1),
        created_by="test-planner",
        input_sha256="a" * 64,
        supersedes_sha256=supersedes_sha256,
        revision_reason="regime changed" if version > 1 else None,
        regime="range",
        biases=(Bias(symbol="EURUSD", stance=Stance.NEUTRAL, summary="range"),),
        key_zones=(
            KeyZone(
                zone_id="entry-1",
                symbol="EURUSD",
                lower=1.10,
                upper=1.101,
                purpose="ENTRY",
            ),
        ),
        scenarios=(
            Scenario(
                scenario_id="A",
                name="pullback",
                trigger="closed-bar rejection",
                action="consider long",
                invalidation="close below range",
            ),
        ),
        global_invalidation="range breaks",
        constraints=SessionConstraints(
            max_risk_pct_per_trade=0.25,
            max_trades=2,
            news_blackout_before_minutes=15,
            news_blackout_after_minutes=15,
            allowed_symbols=("EURUSD",),
            correlation_note="one EUR risk sleeve",
        ),
    )


def test_canonical_json_is_stable_and_artifact_is_write_once(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    value = {"z": 2, "a": {"unicode": "Việt Nam", "ok": True}}

    reference = store.write_artifact("nested/value.json", value, schema_version="test.v1")
    path = tmp_path / "nested" / "value.json"
    expected = canonical_json_bytes(value) + b"\n"

    assert path.read_bytes() == expected
    assert reference.sha256 == sha256(expected).hexdigest()
    assert reference.path == "nested/value.json"
    assert verify_artifact(tmp_path, reference) == path.resolve()

    with pytest.raises(ArtifactExistsError):
        store.write_artifact("nested/value.json", {"changed": True})
    assert path.read_bytes() == expected


def test_artifact_paths_cannot_escape_store(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "store")

    with pytest.raises(ValueError, match="escapes"):
        store.write_artifact("../outside.json", {"no": "escape"})


def test_session_plan_versions_preserve_v1_and_hash_link_immediate_prior(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    v1_ref = store.write_session_plan(_plan())
    v1_path = tmp_path / "SESSION_PLAN_2026-08-27_LONDON_v1.json"
    original_v1 = v1_path.read_bytes()

    v2_ref = store.write_session_plan(_plan(version=2, supersedes_sha256=v1_ref.sha256))

    assert v1_path.read_bytes() == original_v1
    assert v2_ref.path == "SESSION_PLAN_2026-08-27_LONDON_v2.json"
    assert (tmp_path / v2_ref.path).is_file()
    with pytest.raises(ArtifactExistsError):
        store.write_session_plan(_plan())


def test_session_plan_rejects_gap_or_wrong_predecessor_hash(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    store.write_session_plan(_plan())

    with pytest.raises(ArtifactIntegrityError, match="does not match"):
        store.write_session_plan(_plan(version=2, supersedes_sha256="b" * 64))

    with pytest.raises(ArtifactIntegrityError, match="missing"):
        store.write_session_plan(
            _plan(version=3, supersedes_sha256="c" * 64).model_copy(
                update={"revision_reason": "second real revision"}
            )
        )


def test_session_plan_rejects_backdated_revision(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    v1_ref = store.write_session_plan(_plan())
    backdated = _plan(version=2, supersedes_sha256=v1_ref.sha256).model_copy(
        update={"created_at_utc": NOW}
    )

    with pytest.raises(ArtifactIntegrityError, match="later than"):
        store.write_session_plan(backdated)


def test_session_plan_rejects_tampering_anywhere_in_historical_chain(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    v1_ref = store.write_session_plan(_plan())
    v2_ref = store.write_session_plan(_plan(version=2, supersedes_sha256=v1_ref.sha256))
    v1_path = tmp_path / v1_ref.path
    tampered_v1 = _plan().model_copy(update={"regime": "rewritten after v2"})
    v1_path.write_bytes(canonical_json_bytes(tampered_v1) + b"\n")

    with pytest.raises(ArtifactIntegrityError, match="chain is broken"):
        store.write_session_plan(_plan(version=3, supersedes_sha256=v2_ref.sha256))


def test_hash_chain_ledger_appends_canonical_records_and_detects_tampering(
    tmp_path: Path,
) -> None:
    path = tmp_path / "audit.jsonl"
    ledger = HashChainLedger(path)

    first = ledger.append({"event": "PLAN_CREATED", "ref": "a" * 64})
    second = ledger.append({"event": "WATCH_SLEEP"})
    verified = ledger.verify()

    assert len(verified) == 2
    assert first["previous_sha256"] == "0" * 64
    assert second["previous_sha256"] == first["entry_sha256"]
    assert path.read_bytes().endswith(b"\n")

    lines = path.read_text(encoding="utf-8").splitlines()
    corrupted = json.loads(lines[0])
    corrupted["payload"]["event"] = "REWRITTEN"
    lines[0] = json.dumps(corrupted, separators=(",", ":"), sort_keys=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(ArtifactIntegrityError, match="hash mismatch"):
        ledger.verify()
    with pytest.raises(ArtifactIntegrityError):
        ledger.append({"event": "MUST_NOT_APPEND_TO_CORRUPT_CHAIN"})


def test_ledger_rejects_truncated_tail(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    ledger = HashChainLedger(path)
    ledger.append({"ok": True})
    path.write_bytes(path.read_bytes()[:-1])

    with pytest.raises(ArtifactIntegrityError, match="incomplete"):
        ledger.verify()


def test_ledger_serializes_concurrent_writers_without_losing_entries(tmp_path: Path) -> None:
    ledger = HashChainLedger(tmp_path / "concurrent.jsonl")

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda number: ledger.append({"number": number}), range(32)))

    entries = ledger.verify()
    assert len(entries) == 32
    assert {entry["payload"]["number"] for entry in entries} == set(range(32))
    assert [entry["sequence"] for entry in entries] == list(range(1, 33))


def test_idempotency_reservation_is_atomic_across_concurrent_writers(tmp_path: Path) -> None:
    ledger = HashChainLedger(tmp_path / "reservations.jsonl")
    key = "d" * 64

    def reserve(_number: int):
        try:
            ledger.reserve_idempotency_key(
                key,
                {"event_type": "RESERVED", "idempotency_key": key},
            )
            return "reserved"
        except ArtifactExistsError:
            return "duplicate"

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(reserve, range(16)))

    assert results.count("reserved") == 1
    assert results.count("duplicate") == 15
    assert len(ledger.verify()) == 1
