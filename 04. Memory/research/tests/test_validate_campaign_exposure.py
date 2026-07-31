from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
MODULE_PATH = RESEARCH / "validate_campaign_exposure.py"
SCHEMA_PATH = RESEARCH / "CAMPAIGN_EXPOSURE.schema.json"
SPEC = importlib.util.spec_from_file_location("campaign_exposure_validator", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
SUT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUT)


def row_body(row: dict[str, object]) -> bytes:
    return json.dumps(row, separators=(",", ":")).encode("utf-8")


def row_sha(row: dict[str, object]) -> str:
    return hashlib.sha256(row_body(row)).hexdigest().upper()


def chain_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    chained: list[dict[str, object]] = []
    latest_by_campaign: dict[str, dict[str, object]] = {}
    for original in rows:
        row = copy.deepcopy(original)
        campaign_id = str(row["campaign_id"])
        prior = latest_by_campaign.get(campaign_id)
        row["prior_campaign_row_sha256"] = None if prior is None else row_sha(prior)
        chained.append(row)
        latest_by_campaign[campaign_id] = row
    return chained


def campaign_row(
    *,
    campaign_id: str = "CAMPAIGN-EXPOSURE-001",
    ts: str = "2026-07-31T00:00:00Z",
    generation: int = 1,
    campaign_state: str = "ACTIVE",
    event: str = "OPEN",
    phase: str = "P0",
    active_hypothesis_id: str | None = None,
    split_state: str = "SEALED",
    opened_count: int = 0,
    viewed_arms: list[str] | None = None,
    trial_total: int = 10,
    trial_spent: int = 0,
    trial_remaining: int = 10,
    alpha_ppm_total: int = 1000,
    alpha_ppm_spent: int = 0,
    alpha_ppm_remaining: int = 1000,
    carry_debt_ppm: int = 0,
    bound_status: str = "UNBOUND",
    epoch: str | None = None,
    manifest_path: str | None = None,
    manifest_sha256: str | None = None,
    charter_path: str = "04. Memory/research/PRO_TRADER_REPLACEMENT_CAMPAIGN.md",
    charter_sha256: str = "A" * 64,
) -> dict[str, object]:
    return {
        "record_type": "campaign_exposure_state",
        "schema_version": "alphafactory_campaign_exposure.v1",
        "campaign_id": campaign_id,
        "generation": generation,
        "state": campaign_state,
        "event": event,
        "phase": phase,
        "active_hypothesis_id": active_hypothesis_id,
        "charter": {"path": charter_path, "sha256": charter_sha256},
        "prior_campaign_row_sha256": None,
        "budget": {
            "trial_total": trial_total,
            "trial_spent": trial_spent,
            "trial_remaining": trial_remaining,
            "alpha_ppm_total": alpha_ppm_total,
            "alpha_ppm_spent": alpha_ppm_spent,
            "alpha_ppm_remaining": alpha_ppm_remaining,
            "carry_debt_ppm": carry_debt_ppm,
        },
        "viewed_arms": viewed_arms or [],
        "split": {"state": split_state, "opened_count": opened_count},
        "bound_data": {
            "status": bound_status,
            "epoch": epoch,
            "manifest_path": manifest_path,
            "manifest_sha256": manifest_sha256,
            "multiplicity": 1,
            "reopen_condition": "owner_freeze_v2",
        },
        "reason": "campaign exposure state fixture",
        "updated_at_utc": ts,
    }


def bound_row(**overrides: object) -> dict[str, object]:
    defaults = {
        "bound_status": "BOUND",
        "epoch": "fivepercent-EURUSD-M1-202607",
        "manifest_path": "02. AlphaFactory/data/fivepercent/EURUSD/manifest.json",
        "manifest_sha256": "B" * 64,
    }
    defaults.update(overrides)
    return campaign_row(**defaults)


def write_ledger(tmp_path: Path, rows: list[dict[str, object]]) -> Path:
    ledger = tmp_path / "campaign_exposure.jsonl"
    ledger.write_bytes(b"".join(row_body(row) + b"\n" for row in rows))
    return ledger


def validate_rows(tmp_path: Path, rows: list[dict[str, object]]) -> list[str]:
    return SUT.validate_ledger(
        write_ledger(tmp_path, rows),
        SCHEMA_PATH,
        verify_bound_artifacts=False,
    )


def test_bound_manifest_is_rehashed_fail_closed(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(SUT, "WORKSPACE_ROOT", tmp_path)
    manifest = tmp_path / "epoch.json"
    manifest.write_text('{"epoch":"frozen"}\n', encoding="utf-8")
    manifest_sha = hashlib.sha256(manifest.read_bytes()).hexdigest().upper()
    rows = chain_rows(
        [
            campaign_row(),
            bound_row(
                ts="2026-07-31T00:01:00Z",
                event="DATA_BIND",
                phase="P4",
                manifest_path="epoch.json",
                manifest_sha256=manifest_sha,
            ),
        ]
    )
    ledger = write_ledger(tmp_path, rows)
    assert SUT.validate_ledger(ledger, SCHEMA_PATH, verify_bound_artifacts=True) == []
    manifest.write_text('{"epoch":"tampered"}\n', encoding="utf-8")
    errors = SUT.validate_ledger(ledger, SCHEMA_PATH, verify_bound_artifacts=True)
    assert any("bound_data.manifest_sha256 mismatch" in error for error in errors)


def test_campaign_exposure_cli_accepts_valid_ledger(tmp_path: Path) -> None:
    ledger = write_ledger(tmp_path, chain_rows([campaign_row()]))
    result = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(MODULE_PATH),
            "--ledger",
            str(ledger),
            "--schema",
            str(SCHEMA_PATH),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "CAMPAIGN_EXPOSURE_OK rows=1"


def test_campaign_exposure_rejects_null_charter_sha256(tmp_path: Path) -> None:
    row = campaign_row()
    row["charter"] = {"path": "04. Memory/research/PRO_TRADER_REPLACEMENT_CAMPAIGN.md", "sha256": None}
    assert any("None is not of type 'string'" in error for error in validate_rows(tmp_path, [row]))


def test_campaign_exposure_first_row_contract_is_exact(tmp_path: Path) -> None:
    row = bound_row(
        generation=2,
        campaign_state="CLOSED",
        event="DATA_BIND",
        phase="P4",
        active_hypothesis_id="HYP-CAMPAIGN-TEST-001",
        split_state="OPENED",
        opened_count=1,
        viewed_arms=["ARM-A"],
        trial_spent=1,
        trial_remaining=9,
        alpha_ppm_spent=1,
        alpha_ppm_remaining=999,
    )

    errors = validate_rows(tmp_path, [row])
    assert any("first row must start ACTIVE" in error for error in errors)
    assert any("first row generation must be 1" in error for error in errors)
    assert any("first row must use OPEN event" in error for error in errors)
    assert any("first row must start at P0" in error for error in errors)
    assert any("first row active_hypothesis_id must be null" in error for error in errors)
    assert any("first row viewed_arms must be []" in error for error in errors)
    assert any("first row split must be SEALED/0" in error for error in errors)
    assert any("first row bound_data must be UNBOUND" in error for error in errors)
    assert any("first row trial_spent must be 0" in error for error in errors)
    assert any("first row alpha_ppm_spent must be 0" in error for error in errors)


def test_campaign_exposure_accepts_legal_chain_and_data_binding(tmp_path: Path) -> None:
    rows = chain_rows(
        [
            campaign_row(),
            bound_row(
                ts="2026-07-31T00:01:00Z",
                event="DATA_BIND",
                phase="P4",
            ),
            bound_row(
                ts="2026-07-31T00:02:00Z",
                event="BIND_HYPOTHESIS",
                phase="P5",
                active_hypothesis_id="HYP-CAMPAIGN-TEST-001",
                alpha_ppm_spent=100,
                alpha_ppm_remaining=900,
            ),
            bound_row(
                ts="2026-07-31T00:03:00Z",
                event="AUTHORIZE_ATTEMPT",
                phase="P6",
                active_hypothesis_id="HYP-CAMPAIGN-TEST-001",
                split_state="AUTHORIZED",
                alpha_ppm_spent=200,
                alpha_ppm_remaining=800,
                carry_debt_ppm=10,
            ),
            bound_row(
                ts="2026-07-31T00:04:00Z",
                event="ATTEMPT_TERMINAL",
                phase="P7",
                active_hypothesis_id="HYP-CAMPAIGN-TEST-001",
                split_state="OPENED",
                opened_count=1,
                viewed_arms=["ARM-A"],
                trial_spent=1,
                trial_remaining=9,
                alpha_ppm_spent=300,
                alpha_ppm_remaining=700,
                carry_debt_ppm=10,
            ),
        ]
    )
    assert validate_rows(tmp_path, rows) == []


def test_campaign_exposure_rejects_missing_or_wrong_prior_sha(tmp_path: Path) -> None:
    first, second = chain_rows(
        [campaign_row(), campaign_row(ts="2026-07-31T00:01:00Z")]
    )
    second["prior_campaign_row_sha256"] = None
    assert any("prior_campaign_row_sha256 must equal raw SHA256" in error for error in validate_rows(tmp_path, [first, second]))

    second["prior_campaign_row_sha256"] = "C" * 64
    assert any("prior_campaign_row_sha256 must equal raw SHA256" in error for error in validate_rows(tmp_path, [first, second]))

    first["prior_campaign_row_sha256"] = "D" * 64
    assert any("first campaign row prior_campaign_row_sha256 must be null" in error for error in validate_rows(tmp_path, [first]))


def test_campaign_exposure_rejects_budget_arithmetic_and_within_generation_reset(tmp_path: Path) -> None:
    rows = chain_rows(
        [
            campaign_row(),
            campaign_row(
                ts="2026-07-31T00:01:00Z",
                viewed_arms=["A", "B", "C", "D"],
                trial_spent=4,
                trial_remaining=6,
                alpha_ppm_spent=400,
                alpha_ppm_remaining=600,
                carry_debt_ppm=20,
            ),
            campaign_row(
                ts="2026-07-31T00:02:00Z",
                trial_total=11,
                viewed_arms=["A", "B"],
                trial_spent=2,
                trial_remaining=8,
                alpha_ppm_total=900,
                alpha_ppm_spent=300,
                alpha_ppm_remaining=700,
                carry_debt_ppm=10,
            ),
        ]
    )
    errors = validate_rows(tmp_path, rows)
    assert any("trial budget spent+remaining must equal total" in error for error in errors)
    assert any("alpha_ppm budget spent+remaining must equal total" in error for error in errors)
    assert any("budget trial_total changed within generation" in error for error in errors)
    assert any("budget alpha_ppm_total changed within generation" in error for error in errors)
    assert any("budget trial_spent cannot decrease" in error for error in errors)
    assert any("budget alpha_ppm_spent cannot decrease" in error for error in errors)
    assert any("budget carry_debt_ppm cannot decrease" in error for error in errors)


def test_campaign_exposure_requires_trial_spent_to_match_viewed_arms(tmp_path: Path) -> None:
    row = campaign_row(viewed_arms=["ARM-A"], trial_spent=0)
    assert any("trial_spent must equal len(viewed_arms)" in error for error in validate_rows(tmp_path, [row]))


def test_campaign_exposure_rejects_phase_regression_within_generation(tmp_path: Path) -> None:
    rows = chain_rows(
        [
            campaign_row(),
            campaign_row(ts="2026-07-31T00:01:00Z", phase="P3"),
            campaign_row(ts="2026-07-31T00:02:00Z", phase="P2"),
        ]
    )
    assert any("phase cannot move backward within generation" in error for error in validate_rows(tmp_path, rows))


def test_campaign_exposure_closed_requires_terminal_event_and_phase(tmp_path: Path) -> None:
    closed_bad = chain_rows(
        [
            campaign_row(),
            campaign_row(ts="2026-07-31T00:01:00Z", campaign_state="CLOSED", event="OPEN", phase="P11"),
        ]
    )
    active_bad = chain_rows(
        [
            campaign_row(),
            campaign_row(ts="2026-07-31T00:01:00Z", event="GENERATION_CLOSE", phase="P12"),
        ]
    )

    closed_errors = validate_rows(tmp_path, closed_bad)
    active_errors = validate_rows(tmp_path, active_bad)
    assert any("CLOSED row must use GENERATION_CLOSE event" in error for error in closed_errors)
    assert any("CLOSED row must be phase P12" in error for error in closed_errors)
    assert any("GENERATION_CLOSE/P12 requires CLOSED state" in error for error in active_errors)


def test_campaign_exposure_rejects_rows_after_closed_same_generation(tmp_path: Path) -> None:
    rows = chain_rows(
        [
            campaign_row(),
            campaign_row(
                ts="2026-07-31T00:01:00Z",
                campaign_state="CLOSED",
                event="GENERATION_CLOSE",
                phase="P12",
            ),
            campaign_row(
                ts="2026-07-31T00:02:00Z",
                campaign_state="CLOSED",
                event="GENERATION_CLOSE",
                phase="P12",
            ),
        ]
    )
    assert any("no rows may follow CLOSED in the same generation" in error for error in validate_rows(tmp_path, rows))


def test_campaign_exposure_event_semantics_are_strict(tmp_path: Path) -> None:
    data_wrong_event = chain_rows([campaign_row(), bound_row(ts="2026-07-31T00:01:00Z", event="OPEN", phase="P4")])
    data_wrong_phase = chain_rows([campaign_row(), bound_row(ts="2026-07-31T00:01:00Z", event="DATA_BIND", phase="P3")])
    bind_unbound = chain_rows(
        [
            campaign_row(),
            campaign_row(
                ts="2026-07-31T00:01:00Z",
                event="BIND_HYPOTHESIS",
                phase="P5",
                active_hypothesis_id="HYP-CAMPAIGN-TEST-001",
            ),
        ]
    )
    authorize_bad = chain_rows([campaign_row(), campaign_row(ts="2026-07-31T00:01:00Z", event="AUTHORIZE_ATTEMPT")])
    terminal_bad = chain_rows([campaign_row(), campaign_row(ts="2026-07-31T00:01:00Z", event="ATTEMPT_TERMINAL", split_state="AUTHORIZED")])
    opened_wrong_event = chain_rows(
        [
            campaign_row(),
            bound_row(ts="2026-07-31T00:01:00Z", event="DATA_BIND", phase="P4"),
            bound_row(
                ts="2026-07-31T00:02:00Z",
                event="BIND_HYPOTHESIS",
                phase="P5",
                active_hypothesis_id="HYP-CAMPAIGN-TEST-001",
            ),
            bound_row(
                ts="2026-07-31T00:03:00Z",
                event="AUTHORIZE_ATTEMPT",
                phase="P6",
                active_hypothesis_id="HYP-CAMPAIGN-TEST-001",
                split_state="OPENED",
                opened_count=1,
                viewed_arms=["ARM-A"],
                trial_spent=1,
                trial_remaining=9,
            ),
        ]
    )
    generation_too_high = campaign_row(generation=101)
    epoch_same_gen = chain_rows([campaign_row(), campaign_row(ts="2026-07-31T00:01:00Z", event="EPOCH_REOPEN")])

    assert any("DATA_BIND is required for UNBOUND->BOUND" in error for error in validate_rows(tmp_path, data_wrong_event))
    assert any("DATA_BIND must occur at P4" in error for error in validate_rows(tmp_path, data_wrong_phase))
    bind_errors = validate_rows(tmp_path, bind_unbound)
    assert any("BIND_HYPOTHESIS requires bound data" in error for error in bind_errors)
    authorize_errors = validate_rows(tmp_path, authorize_bad)
    assert any("AUTHORIZE_ATTEMPT requires bound data" in error for error in authorize_errors)
    assert any("AUTHORIZE_ATTEMPT requires active_hypothesis_id" in error for error in authorize_errors)
    assert any("AUTHORIZE_ATTEMPT requires split AUTHORIZED" in error for error in authorize_errors)
    terminal_errors = validate_rows(tmp_path, terminal_bad)
    assert any("ATTEMPT_TERMINAL requires bound data" in error for error in terminal_errors)
    assert any("ATTEMPT_TERMINAL requires active_hypothesis_id" in error for error in terminal_errors)
    assert any("ATTEMPT_TERMINAL requires split OPENED" in error for error in terminal_errors)
    assert any("split OPENED requires ATTEMPT_TERMINAL" in error for error in validate_rows(tmp_path, opened_wrong_event))
    assert any("EPOCH_REOPEN is allowed only on generation+1" in error for error in validate_rows(tmp_path, epoch_same_gen))
    assert any("101 is greater than the maximum of 100" in error for error in validate_rows(tmp_path, [generation_too_high]))


def test_campaign_exposure_bound_data_identity_is_immutable_before_bound(tmp_path: Path) -> None:
    rows = chain_rows(
        [
            campaign_row(),
            campaign_row(
                ts="2026-07-31T00:01:00Z",
                bound_status="UNBOUND",
                epoch=None,
                manifest_path=None,
                manifest_sha256=None,
            ),
        ]
    )
    rows[1]["bound_data"]["multiplicity"] = 2
    rows[1]["bound_data"]["reopen_condition"] = "changed"

    errors = validate_rows(tmp_path, rows)
    assert any("bound_data.multiplicity changed within generation" in error for error in errors)
    assert any("bound_data.reopen_condition changed within generation" in error for error in errors)


def test_campaign_exposure_rejects_append_split_bound_hypothesis_and_charter_tamper(tmp_path: Path) -> None:
    rows = chain_rows(
        [
            campaign_row(),
            bound_row(
                ts="2026-07-31T00:01:00Z",
                event="DATA_BIND",
                phase="P4",
            ),
            bound_row(
                ts="2026-07-31T00:02:00Z",
                event="BIND_HYPOTHESIS",
                phase="P5",
                active_hypothesis_id="HYP-CAMPAIGN-TEST-001",
            ),
            bound_row(
                ts="2026-07-31T00:03:00Z",
                event="AUTHORIZE_ATTEMPT",
                phase="P6",
                active_hypothesis_id="HYP-CAMPAIGN-TEST-001",
                split_state="AUTHORIZED",
            ),
            bound_row(
                ts="2026-07-31T00:04:00Z",
                event="ATTEMPT_TERMINAL",
                phase="P7",
                active_hypothesis_id="HYP-CAMPAIGN-TEST-001",
                split_state="OPENED",
                opened_count=2,
                viewed_arms=["ARM-A", "ARM-B"],
                trial_spent=2,
                trial_remaining=8,
            ),
            bound_row(
                ts="2026-07-31T00:05:00Z",
                event="AUTHORIZE_ATTEMPT",
                phase="P8",
                active_hypothesis_id="HYP-CAMPAIGN-TEST-002",
                split_state="AUTHORIZED",
                opened_count=1,
                viewed_arms=["ARM-A"],
                trial_spent=1,
                trial_remaining=9,
                epoch="tampered-epoch",
                charter_sha256="C" * 64,
            ),
        ]
    )
    errors = validate_rows(tmp_path, rows)
    assert any("viewed_arms must be append-only" in error for error in errors)
    assert any("split state cannot move backward" in error for error in errors)
    assert any("split opened_count cannot decrease" in error for error in errors)
    assert any("bound_data.epoch changed after BOUND" in error for error in errors)
    assert any("active_hypothesis_id cannot change after binding" in error for error in errors)
    assert any("charter cannot change within generation" in error for error in errors)


def test_campaign_exposure_rejects_resurrection_and_parallel_active_campaigns(tmp_path: Path) -> None:
    resurrected = chain_rows(
        [
            campaign_row(),
            campaign_row(
                ts="2026-07-31T00:01:00Z",
                campaign_state="CLOSED",
                event="GENERATION_CLOSE",
                phase="P12",
            ),
            campaign_row(ts="2026-07-31T00:02:00Z"),
        ]
    )
    assert any("CLOSED generation cannot resurrect as ACTIVE" in error for error in validate_rows(tmp_path, resurrected))

    parallel = [
        campaign_row(campaign_id="CAMPAIGN-EXPOSURE-001"),
        campaign_row(campaign_id="CAMPAIGN-EXPOSURE-002", ts="2026-07-31T00:01:00Z"),
    ]
    assert any("one active campaign/generation already exists" in error for error in validate_rows(tmp_path, parallel))


def test_campaign_exposure_split_cross_fields_are_strict(tmp_path: Path) -> None:
    sealed_bad = campaign_row(opened_count=5)
    opened_bad = campaign_row(split_state="OPENED", opened_count=0)

    assert any("SEALED split requires opened_count=0" in error for error in validate_rows(tmp_path, [sealed_bad]))
    assert any("OPENED split requires opened_count>=1" in error for error in validate_rows(tmp_path, [opened_bad]))


def test_campaign_exposure_allows_legal_generation_reset_and_new_epoch(tmp_path: Path) -> None:
    rows = chain_rows(
        [
            campaign_row(),
            bound_row(
                ts="2026-07-31T00:01:00Z",
                event="DATA_BIND",
                phase="P4",
            ),
            bound_row(
                ts="2026-07-31T00:02:00Z",
                event="BIND_HYPOTHESIS",
                phase="P5",
                active_hypothesis_id="HYP-CAMPAIGN-TEST-001",
            ),
            bound_row(
                ts="2026-07-31T00:03:00Z",
                event="AUTHORIZE_ATTEMPT",
                phase="P6",
                active_hypothesis_id="HYP-CAMPAIGN-TEST-001",
                split_state="AUTHORIZED",
            ),
            bound_row(
                ts="2026-07-31T00:04:00Z",
                event="ATTEMPT_TERMINAL",
                phase="P7",
                active_hypothesis_id="HYP-CAMPAIGN-TEST-001",
                split_state="OPENED",
                opened_count=1,
                viewed_arms=["ARM-A"],
                trial_spent=1,
                trial_remaining=9,
                alpha_ppm_spent=500,
                alpha_ppm_remaining=500,
                carry_debt_ppm=25,
            ),
            bound_row(
                ts="2026-07-31T00:05:00Z",
                campaign_state="CLOSED",
                event="GENERATION_CLOSE",
                phase="P12",
                active_hypothesis_id="HYP-CAMPAIGN-TEST-001",
                split_state="OPENED",
                opened_count=1,
                viewed_arms=["ARM-A"],
                trial_spent=1,
                trial_remaining=9,
                alpha_ppm_spent=500,
                alpha_ppm_remaining=500,
                carry_debt_ppm=25,
            ),
            campaign_row(
                ts="2026-07-31T00:06:00Z",
                generation=2,
                event="EPOCH_REOPEN",
                phase="P0",
                trial_total=3,
                trial_spent=0,
                trial_remaining=3,
                alpha_ppm_total=300,
                alpha_ppm_spent=0,
                alpha_ppm_remaining=300,
                carry_debt_ppm=25,
                charter_sha256="C" * 64,
            ),
            bound_row(
                ts="2026-07-31T00:07:00Z",
                generation=2,
                event="DATA_BIND",
                phase="P4",
                trial_total=3,
                trial_spent=0,
                trial_remaining=3,
                alpha_ppm_total=300,
                alpha_ppm_spent=0,
                alpha_ppm_remaining=300,
                carry_debt_ppm=25,
                epoch="fivepercent-EURUSD-M1-202608",
                manifest_sha256="D" * 64,
                charter_sha256="C" * 64,
            ),
        ]
    )
    assert validate_rows(tmp_path, rows) == []


def test_campaign_exposure_reopen_requires_exact_reset_contract(tmp_path: Path) -> None:
    rows = chain_rows(
        [
            campaign_row(carry_debt_ppm=4),
            campaign_row(
                ts="2026-07-31T00:01:00Z",
                campaign_state="CLOSED",
                event="GENERATION_CLOSE",
                phase="P12",
                carry_debt_ppm=4,
            ),
            campaign_row(
                ts="2026-07-31T00:02:00Z",
                generation=2,
                event="OPEN",
                viewed_arms=["ARM-A"],
                trial_spent=1,
                trial_remaining=9,
                split_state="AUTHORIZED",
                active_hypothesis_id="HYP-CAMPAIGN-TEST-001",
                carry_debt_ppm=3,
            ),
        ]
    )
    errors = validate_rows(tmp_path, rows)
    assert any("reopened generation must use EPOCH_REOPEN event" in error for error in errors)
    assert any("reopened generation must reset viewed_arms to []" in error for error in errors)
    assert any("reopened generation must reset split to SEALED/0" in error for error in errors)
    assert any("reopened generation must reset active_hypothesis_id to null" in error for error in errors)
    assert any("reopened generation must carry carry_debt_ppm exactly" in error for error in errors)


def test_campaign_exposure_rejects_invalid_cross_type_leakage(tmp_path: Path) -> None:
    campaign = campaign_row()
    campaign["hypothesis_id"] = "HYP-LEAK-001"
    assert any("Additional properties are not allowed" in error or "hypothesis-only fields" in error for error in validate_rows(tmp_path, [campaign]))


def test_data_repair_is_preoutcome_and_fail_closed(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    research = workspace / "04. Memory/research"
    research.mkdir(parents=True)
    monkeypatch.setattr(SUT, "WORKSPACE_ROOT", workspace)
    monkeypatch.setattr(SUT, "RESEARCH_DIR", research)
    charter = {"path": "04. Memory/research/charter.json", "sha256": "C" * 64}
    old_manifest = research / "old_epoch.json"
    old_manifest.write_text('{"tester_model":0}\n', encoding="utf-8")
    old_sha = hashlib.sha256(old_manifest.read_bytes()).hexdigest().upper()
    new_manifest_payload = {
        "campaign_id": "CAMPAIGN-PTR-E01",
        "generation": 2,
        "generation_id": "T2",
        "charter": charter,
        "timeframe": "M5",
        "tester_model": 4,
        "requested_from": "1970.01.01",
        "history_quality": {"operator": "gt", "threshold_pct": 97.0},
        "no_skip": True,
        "mandatory_symbols": SUT.MANDATORY_SYMBOLS,
    }
    new_manifest = research / "new_epoch.json"
    new_manifest.write_text(json.dumps(new_manifest_payload), encoding="utf-8")
    new_sha = hashlib.sha256(new_manifest.read_bytes()).hexdigest().upper()
    closeout_payload = {
        "status": "PARKED_DATA_QUALITY_CONTRACT_FAIL",
        "selected_pass_count": 1,
        "required_pass_count": 9,
        "economic_trials_consumed": 0,
        "trades_authorized": False,
        "performance_metrics_authorized": False,
        "economics_authorized": False,
        "market_edge_claim_authorized": False,
        "symbols": [{"symbol": symbol} for symbol in SUT.MANDATORY_SYMBOLS],
    }
    closeout = research / "closeout.json"
    closeout.write_text(json.dumps(closeout_payload), encoding="utf-8")
    closeout_sha = hashlib.sha256(closeout.read_bytes()).hexdigest().upper()
    hypothesis_id = "HYP-PTR-T2-DATA-EPOCH-D0-M5-004"
    prereg = research / "prereg.md"
    prereg.write_text(
        f"{hypothesis_id}\nTester model: integer `4`\n"
        "DATA_ACQUISITION_ONLY_NO_PERFORMANCE\nno trading\n",
        encoding="utf-8",
    )
    prereg_sha = hashlib.sha256(prereg.read_bytes()).hexdigest().upper()
    registry_row = {
        "hypothesis_id": hypothesis_id,
        "state": "screened",
        "model": 4,
        "run_ids": [],
        "updated_at_utc": "2026-07-30T23:59:00Z",
        "prereg_sha256": prereg_sha,
        "validation": {
            "performance_metrics_authorized": False,
            "economics_authorized": False,
            "model4_data_acquisition_authorized": True,
            "model4_performance_authorized": False,
        },
    }
    (research / "CANDIDATE_REGISTRY.jsonl").write_text(
        json.dumps(registry_row) + "\n", encoding="utf-8"
    )
    prior = campaign_row(
        campaign_id="CAMPAIGN-PTR-E01",
        generation=2,
        event="DATA_BIND",
        phase="P4",
        bound_status="BOUND",
        epoch="OLD",
        manifest_path=str(old_manifest.relative_to(workspace)).replace("\\", "/"),
        manifest_sha256=old_sha,
        charter_path=charter["path"],
        charter_sha256=charter["sha256"],
    )
    current = copy.deepcopy(prior)
    current["schema_version"] = "alphafactory_campaign_exposure.v2"
    current["event"] = "DATA_REPAIR"
    current["bound_data"]["epoch"] = "NEW"  # type: ignore[index]
    current["bound_data"]["manifest_path"] = str(new_manifest.relative_to(workspace)).replace("\\", "/")  # type: ignore[index]
    current["bound_data"]["manifest_sha256"] = new_sha  # type: ignore[index]
    current["data_repair"] = {
        "classification": "INVALID_REPAIR_ZERO_ECONOMICS",
        "predecessor_bound_data": {
            "epoch": "OLD",
            "manifest_path": str(old_manifest.relative_to(workspace)).replace("\\", "/"),
            "manifest_sha256": old_sha,
        },
        "predecessor_closeout": {
            "path": str(closeout.relative_to(workspace)).replace("\\", "/"),
            "sha256": closeout_sha,
        },
        "replacement_prereg": {
            "hypothesis_id": hypothesis_id,
            "path": str(prereg.relative_to(workspace)).replace("\\", "/"),
            "sha256": prereg_sha,
        },
        "prior_diagnostic_runs": 9,
        "prior_selected_pass_count": 1,
        "economic_trials_consumed": 0,
        "data_acquisition_authorized": True,
        "performance_metrics_authorized": False,
        "economics_authorized": False,
        "promotion_eligible": False,
    }
    errors: list[str] = []
    SUT._validate_data_repair(current, prior, "repair", errors)
    assert errors == []

    current["budget"]["trial_spent"] = 1  # type: ignore[index]
    errors = []
    SUT._validate_data_repair(current, prior, "repair", errors)
    assert any("cannot change budget" in error or "exposure must remain zero" in error for error in errors)


def test_data_repair_chronology_requires_immediate_hash_bound_correction(
    tmp_path: Path, monkeypatch
) -> None:
    workspace = tmp_path / "workspace"
    runtime = workspace / "02. AlphaFactory/runtime"
    runtime.mkdir(parents=True)
    monkeypatch.setattr(SUT, "WORKSPACE_ROOT", workspace)
    hypothesis_id = "HYP-PTR-T2-DATA-EPOCH-D0-M5-004"
    receipt = {
        "hypothesis_id": hypothesis_id,
        "generated_at_utc": "2026-07-31T01:55:46Z",
    }
    (runtime / "ea_execution_receipt_001.json").write_text(
        json.dumps(receipt), encoding="utf-8"
    )
    repair = {
        "campaign_id": "CAMPAIGN-PTR-E01",
        "event": "DATA_REPAIR",
        "updated_at_utc": "2026-07-31T02:19:20Z",
        "data_repair": {
            "replacement_prereg": {"hypothesis_id": hypothesis_id},
        },
    }
    repair_sha = row_sha(repair)
    parsed = [
        (
            7,
            repair,
            datetime.fromisoformat("2026-07-31T02:19:20+00:00"),
            repair_sha,
        )
    ]
    errors: list[str] = []
    SUT._validate_data_repair_chronology(parsed, errors)
    assert any("DATA_REPAIR is post-launch" in error for error in errors)

    correction = {
        "campaign_id": "CAMPAIGN-PTR-E01",
        "event": "GOVERNANCE_CORRECTION",
        "governance_correction": {
            "invalid_event": {
                "line": 7,
                "raw_sha256": repair_sha,
                "hypothesis_id": hypothesis_id,
            }
        },
    }
    parsed.append(
        (
            8,
            correction,
            datetime.fromisoformat("2026-07-31T02:30:00+00:00"),
            row_sha(correction),
        )
    )
    errors = []
    SUT._validate_data_repair_chronology(parsed, errors)
    assert errors == []


def test_governance_correction_restores_binding_and_binds_invalid_launch(
    tmp_path: Path, monkeypatch
) -> None:
    workspace = tmp_path / "workspace"
    monkeypatch.setattr(SUT, "WORKSPACE_ROOT", workspace)
    hypothesis_id = "HYP-PTR-T2-DATA-EPOCH-D0-M5-004"
    evidence = workspace / "evidence"
    evidence.mkdir(parents=True)
    receipt_payload = {
        "hypothesis_id": hypothesis_id,
        "authority": "DATA_ACQUISITION_ONLY_NO_PERFORMANCE",
        "generated_at_utc": "2026-07-31T01:55:46Z",
        "binding": {
            "hypothesis_id": hypothesis_id,
            "model": 4,
            "symbol": "XAUUSD",
            "period": "M5",
        },
    }
    receipt = evidence / "receipt.json"
    receipt.write_text(json.dumps(receipt_payload), encoding="utf-8")
    failed_payload = {
        "hypothesis_id": hypothesis_id,
        "error": "MT5 journal delta requires one distinct D0 series proof",
        "state_transitions": [{"state": "execution_started"}, {"state": "failed"}],
    }
    failed = evidence / "failed.json"
    failed.write_text(json.dumps(failed_payload), encoding="utf-8")
    receipt_ref = {
        "path": str(receipt.relative_to(workspace)).replace("\\", "/"),
        "sha256": hashlib.sha256(receipt.read_bytes()).hexdigest().upper(),
    }
    failed_ref = {
        "path": str(failed.relative_to(workspace)).replace("\\", "/"),
        "sha256": hashlib.sha256(failed.read_bytes()).hexdigest().upper(),
    }
    closeout_payload = {
        "hypothesis_id": hypothesis_id,
        "status": "INVALID_GOVERNANCE_PRE_BIND_MT5_LAUNCH",
        "mt5_launches": 1,
        "trades_executed": 0,
        "economic_trials_consumed": 0,
        "performance_metrics_authorized": False,
        "economics_authorized": False,
        "market_edge_claim_authorized": False,
        "artifacts": {
            "execution_receipt": receipt_ref,
            "failed_loop": failed_ref,
        },
    }
    closeout = evidence / "closeout.json"
    closeout.write_text(json.dumps(closeout_payload), encoding="utf-8")
    closeout_ref = {
        "path": str(closeout.relative_to(workspace)).replace("\\", "/"),
        "sha256": hashlib.sha256(closeout.read_bytes()).hexdigest().upper(),
    }
    prior = bound_row(
        campaign_id="CAMPAIGN-PTR-E01",
        generation=2,
        event="DATA_REPAIR",
        phase="P4",
        epoch="NEW",
        manifest_path="new.json",
        manifest_sha256="D" * 64,
        ts="2026-07-31T02:19:20Z",
    )
    prior["schema_version"] = "alphafactory_campaign_exposure.v2"
    prior["data_repair"] = {
        "predecessor_bound_data": {
            "epoch": "OLD",
            "manifest_path": "old.json",
            "manifest_sha256": "B" * 64,
        },
        "replacement_prereg": {"hypothesis_id": hypothesis_id},
    }
    prior_sha = row_sha(prior)
    correction = copy.deepcopy(prior)
    correction["schema_version"] = "alphafactory_campaign_exposure.v3"
    correction["event"] = "GOVERNANCE_CORRECTION"
    correction.pop("data_repair")
    correction["updated_at_utc"] = "2026-07-31T02:30:00Z"
    correction["bound_data"] = {
        "status": "BOUND",
        "epoch": "OLD",
        "manifest_path": "old.json",
        "manifest_sha256": "B" * 64,
        "multiplicity": 1,
        "reopen_condition": "owner_freeze_v2",
    }
    correction["governance_correction"] = {
        "classification": "POST_OUTCOME_BINDING_INVALIDATED_ZERO_ECONOMICS",
        "invalid_event": {
            "line": 7,
            "raw_sha256": prior_sha,
            "event": "DATA_REPAIR",
            "hypothesis_id": hypothesis_id,
            "updated_at_utc": prior["updated_at_utc"],
        },
        "execution_receipt": receipt_ref,
        "failed_loop": failed_ref,
        "terminal_closeout": closeout_ref,
        "mt5_launches": 1,
        "symbols_started": ["XAUUSD"],
        "trades_executed": 0,
        "economic_trials_consumed": 0,
        "performance_metrics_authorized": False,
        "economics_authorized": False,
        "promotion_eligible": False,
        "fresh_hypothesis_required": True,
    }
    errors: list[str] = []
    SUT._validate_governance_correction(
        correction,
        prior,
        7,
        prior_sha,
        "correction",
        errors,
    )
    assert errors == []

    correction["bound_data"]["epoch"] = "TAMPERED"  # type: ignore[index]
    errors = []
    SUT._validate_governance_correction(
        correction,
        prior,
        7,
        prior_sha,
        "correction",
        errors,
    )
    assert any("restore the pre-DATA_REPAIR bound_data exactly" in error for error in errors)
