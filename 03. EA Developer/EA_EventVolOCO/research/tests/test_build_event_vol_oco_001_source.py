from __future__ import annotations

import csv
import io
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


RESEARCH_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH_DIR))

import build_event_vol_oco_001_source as sut


UTC = timezone.utc


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def raw_event(
    event_id: str,
    at: datetime,
    name: str = "CPI m/m",
    currency: str = "USD",
    impact: str = "High Impact Expected",
) -> dict[str, str]:
    local = at.astimezone(timezone(timedelta(hours=7)))
    return {
        "actual": "9.9%",
        "currency": currency,
        "date_local_text": local.strftime("%a %b %d"),
        "event_id": event_id,
        "event_name": name,
        "forecast": "8.8%",
        "impact": impact,
        "previous": "7.7%",
        "time_local_text": local.strftime("%-I:%M%p").lower() if os.name != "nt" else local.strftime("%I:%M%p").lstrip("0").lower(),
        "event_date_local": local.strftime("%Y-%m-%d"),
        "timezone": "GMT+7",
        "event_time_utc": iso(at),
        "source_week": "2019-01-01",
        "source_url": "https://example.test/week",
    }


def normalized(event: dict[str, str]) -> dict[str, str]:
    return {key: event[key] for key in sut.NORMALIZED_FIELDS}


def clean(raw: list[dict[str, str]], rows: list[dict[str, str]] | None = None):
    if rows is None:
        rows = [normalized(event) for event in raw]
    return sut.build_clean_clocks(
        {"events": raw},
        rows,
        start=datetime(2019, 1, 1, tzinfo=UTC),
        end=datetime(2021, 1, 1, tzinfo=UTC),
        expected_clusters=None,
        expected_member_rows=None,
    )


def test_group_before_semantic_filter_rejects_entire_mixed_cluster() -> None:
    at = datetime(2019, 1, 3, 15, tzinfo=UTC)
    point = raw_event("a", at, "CPI m/m")
    speech = raw_event("b", at, "Fed Chair Powell Speaks")
    clocks, stats = clean([point, speech])
    assert clocks == []
    assert stats["window_cluster_count"] == 1
    assert stats["semantic_excluded_cluster_count"] == 1


@pytest.mark.parametrize(
    "name",
    [
        "ECB President Speaks",
        "Governor Speech",
        "Officials Speeches",
        "Chair Testify",
        "Chair Testifies",
        "Chair Testified",
        "Monetary Policy Testimony",
        "Press Conference",
        "Press Conferences",
        "Senate Hearing",
        "Committee Hearings",
    ],
)
def test_semantic_exclusion_regex_variants(name: str) -> None:
    event = raw_event("a", datetime(2019, 1, 3, 15, tzinfo=UTC), name)
    assert clean([event])[0] == []


@pytest.mark.parametrize("name", ["FOMC Meeting Minutes", "ECB Monetary Policy Statement", "Federal Funds Rate"])
def test_point_release_minutes_statements_and_rate_decisions_are_retained(name: str) -> None:
    event = raw_event("a", datetime(2019, 1, 3, 15, tzinfo=UTC), name)
    clocks, _ = clean([event])
    assert len(clocks) == 1
    assert clocks[0]["event_names"] == name


def test_fixed_gmt_plus_7_clock_is_recomputed() -> None:
    event = raw_event("a", datetime(2019, 1, 3, 15, tzinfo=UTC))
    event["time_local_text"] = "10:00pm"
    clocks, _ = clean([event])
    assert clocks[0]["event_time_utc"] == "2019-01-03T15:00:00.000Z"


def test_raw_normalized_mismatch_is_fatal() -> None:
    event = raw_event("a", datetime(2019, 1, 3, 15, tzinfo=UTC))
    row = normalized(event)
    row["event_name"] = "Different"
    with pytest.raises(sut.ContractError, match="normalized/raw mismatch"):
        clean([event], [row])


def test_duplicate_event_id_is_fatal() -> None:
    event = raw_event("a", datetime(2019, 1, 3, 15, tzinfo=UTC))
    with pytest.raises(sut.ContractError, match="duplicate raw event_id"):
        clean([event, dict(event)], [normalized(event)])


def test_duplicate_normalized_clock_is_fatal() -> None:
    event = raw_event("a", datetime(2019, 1, 3, 15, tzinfo=UTC))
    row = normalized(event)
    with pytest.raises(sut.ContractError, match="duplicate normalized event_id"):
        clean([event], [row, dict(row)])


def test_forbidden_surprise_fields_never_escape_clean_output() -> None:
    event = raw_event("a", datetime(2019, 1, 3, 15, tzinfo=UTC))
    clocks, _ = clean([event])
    serialized = json.dumps(clocks).lower()
    for forbidden in ("actual", "forecast", "previous", "return", "pnl", "mfe", "mae"):
        assert forbidden not in serialized
    sut.assert_no_forbidden_output_fields(clocks)


def make_market_reader(t: datetime, missing: set[datetime] | None = None, leak_post_price: bool = False):
    missing = missing or set()
    start = t.replace(minute=0, second=0, microsecond=0) - timedelta(hours=21)
    end = t + timedelta(minutes=30)
    rows: dict[datetime, dict[str, object]] = {}
    cursor = start
    i = 0
    while cursor <= end:
        base = 1.1000 + (i % 31) * 0.0001
        rows[cursor] = {
            "time_utc": cursor,
            "open": base,
            "high": base + 0.0008,
            "low": base - 0.0008,
            "close": base + 0.0001,
        }
        cursor += timedelta(minutes=1)
        i += 1
    calls: list[tuple[datetime, datetime, tuple[str, ...]]] = []

    def reader(read_start: datetime, read_end: datetime, columns: tuple[str, ...]):
        calls.append((read_start, read_end, columns))
        out = []
        cursor = read_start
        while cursor <= read_end:
            if cursor not in missing:
                row = {key: rows[cursor][key] for key in columns}
                if leak_post_price and read_start >= t:
                    row["close"] = rows[cursor]["close"]
                out.append(row)
            cursor += timedelta(minutes=1)
        return out

    reader.calls = calls
    return reader


def test_post_t_projection_is_time_only_and_pre_price_bounds_are_exact() -> None:
    t = datetime(2019, 6, 7, 12, 30, tzinfo=UTC)
    reader = make_market_reader(t)
    geometry = sut.compute_pre_event_geometry(t, reader)
    assert geometry["timestamp_coverage_complete"] is True
    post_calls = [call for call in reader.calls if call[0] >= t]
    assert post_calls == [(t, t + timedelta(minutes=30), ("time_utc",))]
    price_calls = [call for call in reader.calls if "high" in call[2]]
    assert price_calls == [
        (t.replace(minute=0) - timedelta(hours=21), t.replace(minute=0) - timedelta(minutes=1), sut.OHLC_COLUMNS),
        (t - timedelta(minutes=16), t - timedelta(minutes=2), sut.OHLC_COLUMNS),
    ]


def test_post_t_reader_leaking_price_is_fatal() -> None:
    t = datetime(2019, 6, 7, 12, 30, tzinfo=UTC)
    with pytest.raises(sut.ContractError, match="post-T projection returned forbidden"):
        sut.compute_pre_event_geometry(t, make_market_reader(t, leak_post_price=True))


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("open", float("nan"), "invalid box.open"),
        ("close", float("inf"), "invalid box.close"),
        ("high", 1.0, "invalid box OHLC ordering"),
        ("low", 2.0, "invalid box OHLC ordering"),
    ],
)
def test_every_box_row_requires_finite_ordered_ohlc(field: str, value: float, error: str) -> None:
    t = datetime(2019, 6, 7, 12, 30, tzinfo=UTC)
    base_reader = make_market_reader(t)

    def reader(start: datetime, end: datetime, columns: tuple[str, ...]):
        rows = base_reader(start, end, columns)
        if start == t - timedelta(minutes=16) and columns == sut.OHLC_COLUMNS:
            rows[3][field] = value
        return rows

    with pytest.raises(sut.ContractError, match=error):
        sut.compute_pre_event_geometry(t, reader)


def test_missing_m1_minute_is_fatal() -> None:
    t = datetime(2019, 6, 7, 12, 30, tzinfo=UTC)
    missing = {t - timedelta(minutes=7)}
    with pytest.raises(sut.ContractError, match="box timestamp coverage"):
        sut.compute_pre_event_geometry(t, make_market_reader(t, missing))


def test_missing_h1_minute_is_fatal() -> None:
    t = datetime(2019, 6, 7, 12, 30, tzinfo=UTC)
    missing = {t.replace(minute=0) - timedelta(hours=3, minutes=17)}
    with pytest.raises(sut.ContractError, match="H1 timestamp coverage"):
        sut.compute_pre_event_geometry(t, make_market_reader(t, missing))


def test_missing_post_t_timestamp_is_fatal_without_price_read() -> None:
    t = datetime(2019, 6, 7, 12, 30, tzinfo=UTC)
    missing = {t + timedelta(minutes=9)}
    reader = make_market_reader(t, missing)
    with pytest.raises(sut.ContractError, match="post-T timestamp coverage"):
        sut.compute_pre_event_geometry(t, reader)
    assert all(call[2] == ("time_utc",) for call in reader.calls if call[0] >= t)


def test_structural_reader_failure_is_not_downgraded_to_event_incompleteness() -> None:
    t = datetime(2019, 6, 7, 12, 30, tzinfo=UTC)
    clocks = [{"event_clock_id": "EVOCO0001", "event_time_utc": iso(t)}]

    class Reader:
        @staticmethod
        def read_range(*_args):
            raise sut.ContractError("public DESIGN shard SHA mismatch")

    with pytest.raises(sut.ContractError, match="shard SHA mismatch"):
        sut._audit_geometries(clocks, Reader())


def test_event_local_coverage_failure_is_counted_without_hiding_structure_errors() -> None:
    t = datetime(2019, 6, 7, 12, 30, tzinfo=UTC)
    clocks = [{"event_clock_id": "EVOCO0001", "event_time_utc": iso(t)}]

    class Reader:
        @staticmethod
        def read_range(*_args):
            raise sut.EventSourceIncomplete("H1 timestamp coverage mismatch")

    ledger, geometries, selected, skipped = sut._audit_geometries(clocks, Reader())
    assert geometries == {}
    assert selected == [t]
    assert skipped == []
    assert ledger[0]["source_complete"] is False
    assert "H1 timestamp coverage mismatch" in ledger[0]["source_incomplete_reason"]


def test_greedy_reservation_treats_touching_boundary_as_overlap() -> None:
    t = datetime(2019, 1, 1, 10, tzinfo=UTC)
    selected, skipped = sut.greedy_primary_schedule([t, t + timedelta(minutes=31), t + timedelta(minutes=32)])
    assert selected == [t, t + timedelta(minutes=32)]
    assert skipped == [t + timedelta(minutes=31)]


def test_matched_control_rejects_any_clean_event_within_two_hours() -> None:
    t = datetime(2019, 1, 10, 10, tzinfo=UTC)
    control = t - timedelta(days=7)
    pairs, rejected = sut.match_controls([t], [t, control + timedelta(hours=2)], {control})
    assert pairs == []
    assert rejected == [{"event_time_utc": iso(t), "reason": "control_contaminated_by_clean_event"}]


def test_matched_control_accepts_exact_frozen_offset_when_clean() -> None:
    t = datetime(2019, 1, 10, 10, tzinfo=UTC)
    control = t - timedelta(days=7)
    pairs, rejected = sut.match_controls([t], [t], {control})
    assert pairs == [(t, control)]
    assert rejected == []


def gate_inputs(**overrides):
    values = {
        "observed_clean_clusters": 319,
        "complete_clean_clusters": 316,
        "matched_pair_count": 209,
        "primary_risks_pips": [5.0] * 80 + [8.0] * 159 + [12.0] * 80,
        "elapsed_weeks": 104.42857142857143,
    }
    values.update(overrides)
    return values


def test_exact_99_percent_completeness_boundary() -> None:
    assert sut.evaluate_source_gates(**gate_inputs())["gates"]["history_complete_99pct"] is True
    failed = sut.evaluate_source_gates(**gate_inputs(complete_clean_clusters=315))
    assert failed["gates"]["history_complete_99pct"] is False


def test_pair_count_boundary_and_cadence() -> None:
    passed = sut.evaluate_source_gates(**gate_inputs())
    assert passed["gates"]["matched_pairs_gte_209"] is True
    assert passed["gates"]["pair_cadence_2_to_5"] is True
    failed = sut.evaluate_source_gates(**gate_inputs(matched_pair_count=208))
    assert failed["gates"]["matched_pairs_gte_209"] is False
    assert failed["gates"]["pair_cadence_2_to_5"] is False


def test_geometry_gates_include_median_p25_and_cost_ratio() -> None:
    passed = sut.evaluate_source_gates(**gate_inputs())
    assert passed["gates"]["median_planned_risk_gte_8"] is True
    assert passed["gates"]["p25_planned_risk_gte_5"] is True
    assert passed["gates"]["six_pip_to_median_lte_0_75"] is True
    failed = sut.evaluate_source_gates(**gate_inputs(primary_risks_pips=[7.9] * 319))
    assert failed["gates"]["median_planned_risk_gte_8"] is False
    assert failed["gates"]["six_pip_to_median_lte_0_75"] is False


def test_receipt_must_bind_public_design_and_keep_sealed_sets_closed() -> None:
    valid = {
        "m1_source_sha256": sut.PUBLIC_M1_SOURCE_SHA256,
        "research_validation_opened": False,
        "research_holdout_opened": False,
    }
    sut.validate_design_receipt(valid)
    for mutation in (
        {"m1_source_sha256": "0" * 64},
        {"research_validation_opened": True},
        {"research_holdout_opened": True},
    ):
        with pytest.raises(sut.ContractError):
            sut.validate_design_receipt(valid | mutation)


def test_safe_input_rejects_path_escape_and_reparse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "public" / "DESIGN"
    root.mkdir(parents=True)
    good = root / "m1.parquet"
    good.write_bytes(b"x")
    sut.assert_safe_regular_file(good, exact_root=root)
    outside = tmp_path / "outside.parquet"
    outside.write_bytes(b"x")
    with pytest.raises(sut.ContractError, match="outside exact root"):
        sut.assert_safe_regular_file(outside, exact_root=root)
    alias = root / "alias.parquet"
    alias.write_bytes(b"alias")
    original = sut._has_reparse_attribute
    monkeypatch.setattr(sut, "_has_reparse_attribute", lambda path: Path(path) == alias or original(Path(path)))
    with pytest.raises(sut.ContractError, match="symlink|reparse"):
        sut.assert_safe_regular_file(alias, exact_root=root)


def test_safe_input_rejects_hardlink(tmp_path: Path) -> None:
    root = tmp_path / "public" / "DESIGN"
    root.mkdir(parents=True)
    good = root / "m1.parquet"
    good.write_bytes(b"x")
    hard = root / "hard.parquet"
    os.link(good, hard)
    with pytest.raises(sut.ContractError, match="single-link"):
        sut.assert_safe_regular_file(good, exact_root=root)


def test_input_rejects_reparse_ancestor_cross_platform(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "workspace"
    ancestor = root / "public"
    ancestor.mkdir(parents=True)
    source = ancestor / "authority.json"
    source.write_text("{}", encoding="utf-8")
    original = sut._has_reparse_attribute
    monkeypatch.setattr(
        sut,
        "_has_reparse_attribute",
        lambda path: Path(path) == ancestor or original(Path(path)),
    )
    with pytest.raises(sut.ContractError, match="ancestor.*symlink|ancestor.*reparse"):
        sut.assert_safe_regular_file(source, exact_root=root)


def test_output_rejects_escape_and_reparse_ancestor_before_mkdir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "workspace"
    ancestor = root / "research"
    ancestor.mkdir(parents=True)
    target = ancestor / "new" / "artifact.json"
    sut.assert_safe_output_path(target, exact_root=root)
    with pytest.raises(sut.ContractError, match="outside exact root"):
        sut.assert_safe_output_path(tmp_path / "outside" / "artifact.json", exact_root=root)
    original = sut._has_reparse_attribute
    monkeypatch.setattr(
        sut,
        "_has_reparse_attribute",
        lambda path: Path(path) == ancestor or original(Path(path)),
    )
    with pytest.raises(sut.ContractError, match="ancestor.*symlink|ancestor.*reparse"):
        sut.assert_safe_output_path(target, exact_root=root)


def test_wrong_input_hash_is_fatal(tmp_path: Path) -> None:
    root = tmp_path / "public"
    root.mkdir()
    source = root / "manifest.json"
    source.write_bytes(b"authority")
    with pytest.raises(sut.ContractError, match="SHA256 mismatch"):
        sut.verify_file_sha256(source, "0" * 64, exact_root=root)


def test_authority_bundle_reads_each_file_once_and_hashes_returned_bytes(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    one = root / "one.json"
    two = root / "two.json"
    one.write_bytes(b'{"value":1}')
    two.write_bytes(b'{"value":2}')
    calls: list[Path] = []

    def reader(path: Path, *, exact_root: Path) -> bytes:
        calls.append(path)
        return sut.read_safe_bytes_once(path, exact_root=exact_root)

    specs = {
        "one": ("one.json", sut.sha256_bytes(b'{"value":1}')),
        "two": ("two.json", sut.sha256_bytes(b'{"value":2}')),
    }
    blobs = sut.read_authority_blobs(root, specs, reader=reader)
    assert calls == [one, two]
    assert json.loads(blobs["one"]) == {"value": 1}
    assert json.loads(blobs["two"]) == {"value": 2}


def review_fixture(tmp_path: Path):
    root = tmp_path / "workspace"
    builder_rel = "research/builder.py"
    test_rel = "research/tests/test_builder.py"
    registry_rel = "registry.jsonl"
    receipt_rel = "research/reviews/independent_review_receipt.json"
    builder = root / builder_rel
    tests = root / test_rel
    receipt = root / receipt_rel
    builder.parent.mkdir(parents=True)
    tests.parent.mkdir(parents=True)
    receipt.parent.mkdir(parents=True)
    builder.write_bytes(b"builder-final")
    tests.write_bytes(b"tests-final")
    builder_sha = sut.sha256_bytes(builder.read_bytes())
    test_sha = sut.sha256_bytes(tests.read_bytes())
    receipt_payload = {
        "schema_version": sut.INDEPENDENT_REVIEW_SCHEMA,
        "hypothesis_id": sut.HYPOTHESIS_ID,
        "review_status": "PASS",
        "reviewed_builder": {"path": builder_rel, "sha256": builder_sha},
        "reviewed_tests": {"path": test_rel, "sha256": test_sha},
        "v1_plan": {"path": sut.V1_PLAN_REL, "sha256": sut.V1_PLAN_SHA256},
        "v2_plan": {"path": sut.V2_PLAN_REL, "sha256": sut.V2_PLAN_SHA256},
        "permissions": {
            "source_feasibility_run": True,
            "performance_or_economics": False,
            "mt5_or_mql5": False,
        },
    }
    receipt_bytes = sut.canonical_json_bytes(receipt_payload)
    receipt.write_bytes(receipt_bytes)
    registry_row = {
        "hypothesis_id": sut.HYPOTHESIS_ID,
        "prereg_path": sut.V2_PLAN_REL,
        "prereg_sha256": sut.V2_PLAN_SHA256,
        "source_path": None,
        "source_hash": None,
        "model": None,
        "verdict": "FROZEN_SOURCE_FEASIBILITY_RUN_AUTHORIZED_AFTER_INDEPENDENT_REVIEW",
        "source_provenance": f"superseded_v1_sha256={sut.V1_PLAN_SHA256}",
        "validation": {
            "independent_pre_run_review_status": "PASS",
            "source_run_authorized": True,
            "performance_metrics_authorized": False,
            "reviewed_builder_path": builder_rel,
            "reviewed_builder_sha256": builder_sha,
            "reviewed_test_path": test_rel,
            "reviewed_test_sha256": test_sha,
            "independent_review_receipt_path": receipt_rel,
            "independent_review_receipt_sha256": sut.sha256_bytes(receipt_bytes),
        },
    }
    (root / registry_rel).write_bytes(sut.canonical_json_bytes(registry_row))
    return root, builder_rel, test_rel, registry_rel, receipt_rel, registry_row


def test_code_review_binding_requires_exact_builder_test_and_external_receipt_hash(tmp_path: Path) -> None:
    root, builder_rel, test_rel, registry_rel, receipt_rel, _ = review_fixture(tmp_path)
    binding = sut.validate_code_review_authority(
        root,
        builder_rel=builder_rel,
        test_rel=test_rel,
        registry_rel=registry_rel,
        receipt_rel=receipt_rel,
    )
    assert binding["builder_sha256"] == sut.sha256_bytes(b"builder-final")
    assert binding["test_sha256"] == sut.sha256_bytes(b"tests-final")
    assert binding["independent_review_receipt_sha256"] == sut.sha256_file(root / receipt_rel)


def test_code_review_binding_rejects_builder_changed_after_review(tmp_path: Path) -> None:
    root, builder_rel, test_rel, registry_rel, receipt_rel, _ = review_fixture(tmp_path)
    (root / builder_rel).write_bytes(b"builder-mutated-after-review")
    with pytest.raises(sut.ContractError, match="reviewed builder SHA"):
        sut.validate_code_review_authority(
            root,
            builder_rel=builder_rel,
            test_rel=test_rel,
            registry_rel=registry_rel,
            receipt_rel=receipt_rel,
        )


def test_code_review_binding_rejects_receipt_hash_or_content_mismatch(tmp_path: Path) -> None:
    root, builder_rel, test_rel, registry_rel, receipt_rel, _ = review_fixture(tmp_path)
    receipt_path = root / receipt_rel
    receipt_path.write_bytes(receipt_path.read_bytes() + b"\n")
    with pytest.raises(sut.ContractError, match="independent review receipt SHA"):
        sut.validate_code_review_authority(
            root,
            builder_rel=builder_rel,
            test_rel=test_rel,
            registry_rel=registry_rel,
            receipt_rel=receipt_rel,
        )


def test_code_snapshot_is_hashed_before_registry_and_review_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, builder_rel, test_rel, registry_rel, receipt_rel, _ = review_fixture(tmp_path)
    events: list[str] = []

    def reader(path: Path, *, exact_root: Path) -> bytes:
        events.append(f"read:{path.relative_to(root).as_posix()}")
        return sut.read_safe_bytes_once(path, exact_root=exact_root)

    original_sha256 = sut.sha256_bytes

    def tracked_sha256(payload: bytes) -> str:
        if payload in {b"builder-final", b"tests-final"}:
            events.append(f"hash:{payload.decode('ascii')}")
        return original_sha256(payload)

    monkeypatch.setattr(sut, "sha256_bytes", tracked_sha256)

    sut.validate_code_review_authority(
        root,
        builder_rel=builder_rel,
        test_rel=test_rel,
        registry_rel=registry_rel,
        receipt_rel=receipt_rel,
        reader=reader,
    )
    assert events[:6] == [
        f"read:{builder_rel}",
        "hash:builder-final",
        f"read:{test_rel}",
        "hash:tests-final",
        f"read:{registry_rel}",
        f"read:{receipt_rel}",
    ]


def test_review_preflight_rejects_workspace_reparse_ancestor_before_any_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, builder_rel, test_rel, registry_rel, receipt_rel, _ = review_fixture(tmp_path)
    ancestor = root.parent
    original = sut._has_reparse_attribute
    monkeypatch.setattr(
        sut,
        "_has_reparse_attribute",
        lambda path: Path(path) == ancestor or original(Path(path)),
    )
    reads: list[Path] = []

    def reader(path: Path, *, exact_root: Path) -> bytes:
        reads.append(path)
        return path.read_bytes()

    with pytest.raises(sut.ContractError, match="ancestor.*symlink|ancestor.*reparse"):
        sut.validate_code_review_authority(
            root,
            builder_rel=builder_rel,
            test_rel=test_rel,
            registry_rel=registry_rel,
            receipt_rel=receipt_rel,
            reader=reader,
        )
    assert reads == []


def test_started_and_final_receipt_bind_exact_reviewed_snapshot(tmp_path: Path) -> None:
    root, builder_rel, test_rel, registry_rel, receipt_rel, registry_row = review_fixture(tmp_path)
    binding = sut.validate_code_review_authority(
        root,
        builder_rel=builder_rel,
        test_rel=test_rel,
        registry_rel=registry_rel,
        receipt_rel=receipt_rel,
    )
    started = sut.make_attempt_started_payload(registry_row, binding)
    receipt_fields = sut.review_binding_fields(binding)
    for payload in (started, receipt_fields):
        assert payload["builder_sha256"] == binding["builder_sha256"]
        assert payload["test_sha256"] == binding["test_sha256"]
        assert payload["independent_review_receipt_sha256"] == binding["independent_review_receipt_sha256"]


def test_explicit_zero_outcome_counters_are_legal_but_nonzero_is_fatal() -> None:
    sut.assert_no_forbidden_output_fields({"metrics": dict(sut.ZERO_COUNTERS)})
    with pytest.raises(sut.ContractError, match="forbidden output field"):
        sut.assert_no_forbidden_output_fields({"return": 0.1})
    with pytest.raises(sut.ContractError, match="forbidden outcome counter"):
        sut.assert_no_forbidden_output_fields({"metrics": {"returns_computed": 1}})


def test_create_new_output_refuses_conflict(tmp_path: Path) -> None:
    path = tmp_path / "artifact.json"
    sut.write_json_create_new(path, {"a": 1})
    before = path.read_bytes()
    with pytest.raises(sut.ContractError, match="output conflict"):
        sut.write_json_create_new(path, {"a": 2})
    assert path.read_bytes() == before


def test_canonical_json_and_clean_clock_transform_are_deterministic() -> None:
    events = [
        raw_event("b", datetime(2019, 1, 4, 15, tzinfo=UTC)),
        raw_event("a", datetime(2019, 1, 3, 15, tzinfo=UTC)),
    ]
    one = clean(events)[0]
    two = clean(list(reversed(events)), list(reversed([normalized(e) for e in events])))[0]
    assert sut.canonical_json_bytes(one) == sut.canonical_json_bytes(two)


def test_exception_after_attempt_start_writes_null_terminal_and_zero_counters(tmp_path: Path) -> None:
    def fail():
        raise RuntimeError("synthetic failure")

    with pytest.raises(RuntimeError, match="synthetic failure"):
        sut.execute_with_terminal_guard(tmp_path, fail)
    terminal = json.loads((tmp_path / "attempt_terminal.json").read_text(encoding="utf-8"))
    assert terminal["market_verdict"] is None
    assert terminal["engineering_status"] == "ERROR"
    assert terminal["metrics"]["performance_trials_executed"] == 0
    assert terminal["metrics"]["post_t_price_values_read"] == 0
    assert terminal["metrics"]["trades_simulated"] == 0


def test_model_four_is_frozen_for_later_economics_and_model_zero_prohibited() -> None:
    assert sut.LATER_ECONOMICS_MT5_MODEL == 4
    assert sut.LATER_ECONOMICS_MODEL_LABEL == "Every tick based on real ticks"
    assert sut.MODEL_ZERO_ALLOWED_FOR_LATER_ECONOMICS is False
