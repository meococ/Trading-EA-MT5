from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pyarrow.parquet as parquet
import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "research"
    / "prepare_trendstack_002_source.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "prepare_trendstack_002_source", MODULE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _runtime_objects(*, server="FivePercentOnline-Real", company="Five Percent Online Ltd", trade_allowed=False):
    terminal = SimpleNamespace(build=6063, trade_allowed=trade_allowed, data_path="X:/demo")
    account = SimpleNamespace(trade_mode=0, server=server, company=company)
    symbol = SimpleNamespace(digits=5, point=0.00001)
    mt5 = SimpleNamespace(ACCOUNT_TRADE_MODE_DEMO=0)
    return mt5, terminal, account, symbol


def _h1_rows(mod, utc_times: list[pd.Timestamp]) -> np.ndarray:
    dtype = [
        ("time", "i8"),
        ("open", "f8"),
        ("high", "f8"),
        ("low", "f8"),
        ("close", "f8"),
        ("tick_volume", "i8"),
        ("spread", "i4"),
        ("real_volume", "i8"),
    ]
    rows = np.zeros(len(utc_times), dtype=dtype)
    for index, timestamp in enumerate(utc_times):
        encoded = mod.utc_to_server_api_datetime(timestamp.to_pydatetime())
        rows[index]["time"] = int(encoded.timestamp())
        value = 1.10 + index * 0.0001
        rows[index]["open"] = value
        rows[index]["high"] = value + 0.0003
        rows[index]["low"] = value - 0.0003
        rows[index]["close"] = value + 0.0001
        rows[index]["tick_volume"] = 100 + index
        rows[index]["spread"] = 10
    return rows


def _request_record(mod, frame: pd.DataFrame, request_id: str) -> dict:
    ordered = frame.sort_values("time_utc", kind="mergesort")
    utc_times = pd.to_datetime(ordered["time_utc"])
    server_times = pd.to_datetime(ordered["time_server"])
    canonical_from = pd.Timestamp(utc_times.iloc[0])
    source_end = pd.Timestamp(utc_times.iloc[-1]) + pd.Timedelta(hours=1)
    canonical_to = source_end - pd.Timedelta(seconds=1)
    gaps = utc_times.diff().dropna().dt.total_seconds() / 3600.0
    return {
        "record_type": "request",
        "request_id": request_id,
        "canonical_from_utc": canonical_from.tz_localize("UTC").isoformat(),
        "canonical_to_inclusive_utc": canonical_to.tz_localize("UTC").isoformat(),
        "source_end_exclusive_utc": source_end.tz_localize("UTC").isoformat(),
        "api_server_wall_from_encoded_as_utc": mod.utc_to_server_api_datetime(
            canonical_from.tz_localize("UTC").to_pydatetime()
        ).isoformat(),
        "api_server_wall_to_encoded_as_utc": mod.utc_to_server_api_datetime(
            canonical_to.tz_localize("UTC").to_pydatetime()
        ).isoformat(),
        "canonical_roundtrip_status": "PASS",
        "symbol": mod.SYMBOL,
        "timeframe": "H1",
        "response": {
            "rows": int(len(ordered)),
            "first_server_time": pd.Timestamp(server_times.iloc[0]).isoformat(),
            "last_server_time": pd.Timestamp(server_times.iloc[-1]).isoformat(),
            "first_utc_time": pd.Timestamp(utc_times.iloc[0]).isoformat(),
            "last_utc_time": pd.Timestamp(utc_times.iloc[-1]).isoformat(),
            "duplicate_utc_opens": 0,
            "gap_count": int((gaps > 1).sum()) if len(gaps) else 0,
            "maximum_gap_hours": float(gaps.max()) if len(gaps) else 0.0,
            "gap_multiple_status": "PASS",
            "geometry_status": "PASS",
            "holdout_rows_received": 0,
        },
    }


def _runtime_provenance_fixture(mod) -> dict:
    return {
        "terminal_executable_label": "terminal64.exe",
        "terminal_executable_sha256": "A" * 64,
        "terminal_build": 6063,
        "python_executable_label": "python.exe",
        "python_executable_sha256": "B" * 64,
        "metatrader5_version": "5.0.5260",
        "metatrader5_native_module_label": "_core.pyd",
        "metatrader5_native_module_sha256": "C" * 64,
        "clock_tool_label": Path(mod.CLOCK_REL).name,
        "clock_tool_sha256": mod.sha256_file(mod.WORKSPACE / mod.CLOCK_REL),
        "extractor_label": MODULE_PATH.name,
        "extractor_sha256": mod.sha256_file(MODULE_PATH),
        "source_plan_label": Path(mod.PLAN_REL).name,
        "source_plan_sha256": mod.PLAN_SHA256,
        "account_guard": {
            "terminal_build": 6063,
            "terminal_trade_allowed": False,
            "account_mode": "DEMO",
            "server": mod.EXPECTED_SERVER,
            "company": mod.EXPECTED_COMPANY,
            "symbol": mod.SYMBOL,
            "symbol_digits": mod.EXPECTED_DIGITS,
            "symbol_point": mod.EXPECTED_POINT,
        },
        "pandas_version": pd.__version__,
        "pyarrow_version": __import__("pyarrow").__version__,
    }


def _runtime_hashes(runtime: dict) -> dict:
    return {key: value for key, value in runtime.items() if key.endswith("sha256")}


def _server_time_for_utc(mod, utc_time: pd.Timestamp) -> pd.Timestamp:
    canonical = pd.Timestamp(utc_time)
    for offset in (2, 3):
        candidate = canonical + pd.Timedelta(hours=offset)
        if mod.server_to_utc(candidate.to_pydatetime()) == canonical.to_pydatetime():
            return candidate
    raise AssertionError(f"fixture cannot encode canonical UTC time {utc_time}")


def _full_frozen_source_fixture(mod) -> tuple[pd.DataFrame, list[dict]]:
    chunks = mod.month_chunks()
    rows = []
    dense_dates = pd.date_range("2019-01-01", periods=254, freq="D")
    dense_months = {(date.year, date.month) for date in dense_dates}
    for chunk in chunks:
        start = pd.Timestamp(chunk["canonical_from_utc"]).tz_localize(None)
        if (start.year, start.month) not in dense_months:
            rows.append((start, chunk["request_id"], 1.0))
    for day_index, date in enumerate(dense_dates):
        request_id = next(
            chunk["request_id"]
            for chunk in chunks
            if pd.Timestamp(chunk["canonical_from_utc"]).tz_localize(None)
            <= date
            < pd.Timestamp(chunk["source_end_exclusive_utc"]).tz_localize(None)
        )
        for hour in range(20):
            rows.append((date + pd.Timedelta(hours=hour), request_id, 1.0 + day_index * 0.001))
    records = []
    for index, (utc_time, request_id, base) in enumerate(sorted(rows)):
        server_time = _server_time_for_utc(mod, utc_time)
        value = base + (utc_time.hour * 0.00001) + index * 0.000000001
        records.append(
            {
                "time_server": server_time,
                "time_utc": utc_time,
                "utc_offset_h": int((server_time - utc_time) / pd.Timedelta(hours=1)),
                "open": value,
                "high": value + 0.0003,
                "low": value - 0.0003,
                "close": value + 0.0001,
                "tick_volume": 100,
                "spread": 10,
                "real_volume": 0,
                "request_id": request_id,
            }
        )
    frame = pd.DataFrame(records).sort_values("time_utc", kind="mergesort").reset_index(drop=True)
    requests = []
    for chunk in chunks:
        selected = frame.loc[frame["request_id"] == chunk["request_id"]]
        assert not selected.empty
        requests.append({**_request_record(mod, selected, chunk["request_id"]), **chunk})
    return frame, requests


def _sparse_frozen_source_fixture(mod) -> tuple[pd.DataFrame, list[dict]]:
    rows = []
    chunks = mod.month_chunks()
    for index, chunk in enumerate(chunks):
        utc_time = pd.Timestamp(chunk["canonical_from_utc"]).tz_localize(None)
        server_time = _server_time_for_utc(mod, utc_time)
        value = 1.0 + index * 0.0001
        rows.append(
            {
                "time_server": server_time,
                "time_utc": utc_time,
                "utc_offset_h": int((server_time - utc_time) / pd.Timedelta(hours=1)),
                "open": value,
                "high": value + 0.0003,
                "low": value - 0.0003,
                "close": value + 0.0001,
                "tick_volume": 100,
                "spread": 10,
                "real_volume": 0,
                "request_id": chunk["request_id"],
            }
        )
    frame = pd.DataFrame(rows)
    requests = []
    for chunk in chunks:
        selected = frame.loc[frame["request_id"] == chunk["request_id"]]
        requests.append({**_request_record(mod, selected, chunk["request_id"]), **chunk})
    return frame, requests


def _packet_base(mod) -> dict:
    packet = {
        "schema_version": "trendstack_002_decision_packet.v1",
        "hypothesis_id": mod.HYPOTHESIS_ID,
        "opportunity_id": "2022-01-03",
        "split": "VALIDATION_FEATURE_ONLY",
        "decision_cutoff_utc": "2022-01-03T12:00:00",
        "m252_direction": 1,
        "m6_direction": -1,
        "alignment": False,
        "atr20": 0.001,
        "control_m252_eligible": True,
        "control_m6_eligible": True,
        "challenger_stack_eligible": False,
        "negative_disagree_eligible": True,
        "exclusion_reason": "M252_M6_DISAGREE",
        "valid_prior_close_count": 253,
        "max_source_time_utc": "2022-01-03T11:00:00",
        "source_shard_chain_hashes": {
            "prior_completed_shards_sha256": "A" * 64,
            "current_pre12_sha256": "B" * 64,
        },
        "source_chain_sha256": "D" * 64,
        "extractor_sha256": "C" * 64,
        "source_plan_sha256": mod.PLAN_SHA256,
    }
    packet["source_chain_sha256"] = mod.sha256_bytes(
        mod.canonical_json_bytes(packet["source_shard_chain_hashes"])
    )
    return packet


def test_month_chunks_are_contiguous_bounded_and_never_request_2023() -> None:
    mod = load_module()

    chunks = mod.month_chunks()

    assert len(chunks) == 96
    assert chunks[0]["canonical_from_utc"] == "2015-01-02T00:00:00+00:00"
    assert chunks[-1]["source_end_exclusive_utc"] == "2023-01-01T00:00:00+00:00"
    for previous, current in zip(chunks, chunks[1:]):
        assert previous["source_end_exclusive_utc"] == current["canonical_from_utc"]
    assert all(pd.Timestamp(row["canonical_to_inclusive_utc"]) < mod.HOLDOUT_START for row in chunks)
    final = chunks[-1]
    api_ceiling = datetime.fromisoformat(final["api_server_wall_to_encoded_as_utc"])
    assert pd.Timestamp(api_ceiling) >= mod.HOLDOUT_START
    assert mod.server_to_utc(api_ceiling.replace(tzinfo=None)) == datetime(
        2022, 12, 31, 23, 59, 59
    )
    assert final["canonical_roundtrip_status"] == "PASS"


def test_runtime_guards_require_exact_read_only_fivepercent_demo() -> None:
    mod = load_module()
    mt5, terminal, account, symbol = _runtime_objects()

    observed = mod.validate_runtime_guards(mt5, terminal, account, symbol)

    assert observed["terminal_trade_allowed"] is False
    assert observed["account_mode"] == "DEMO"
    assert observed["server"] == "FivePercentOnline-Real"

    mt5, terminal, account, symbol = _runtime_objects(
        server="MetaQuotes-Demo", company="MetaQuotes Ltd."
    )
    with pytest.raises(RuntimeError, match="INVALID_ENGINEERING.*broker"):
        mod.validate_runtime_guards(mt5, terminal, account, symbol)
    mt5, terminal, account, symbol = _runtime_objects(trade_allowed=True)
    with pytest.raises(RuntimeError, match="INVALID_ENGINEERING.*trading"):
        mod.validate_runtime_guards(mt5, terminal, account, symbol)


def test_normalize_rates_uses_canonical_clock_and_rejects_illegal_rows() -> None:
    mod = load_module()
    chunk = mod.month_chunks(
        datetime(2022, 12, 1, tzinfo=timezone.utc), mod.HOLDOUT_START.to_pydatetime()
    )[0]
    legal_times = [
        pd.Timestamp("2022-12-30 10:00:00", tz="UTC"),
        pd.Timestamp("2022-12-30 11:00:00", tz="UTC"),
    ]

    frame, quality = mod.normalize_rates(_h1_rows(mod, legal_times), chunk)

    assert list(frame["time_utc"]) == [value.tz_localize(None) for value in legal_times]
    assert set(frame["utc_offset_h"]) == {2}
    assert quality["duplicate_utc_opens"] == 0
    assert quality["gap_multiple_status"] == "PASS"

    duplicated = np.concatenate([_h1_rows(mod, legal_times), _h1_rows(mod, [legal_times[-1]])])
    with pytest.raises(RuntimeError, match="INVALID_ENGINEERING.*duplicate"):
        mod.normalize_rates(duplicated, chunk)
    illegal = _h1_rows(mod, [pd.Timestamp("2023-01-02 06:00:00", tz="UTC")])
    with pytest.raises(RuntimeError, match="INVALID_ENGINEERING.*range"):
        mod.normalize_rates(illegal, chunk)


def test_utc_server_roundtrip_uses_eu_dst_plus_three() -> None:
    mod = load_module()
    utc = datetime(2022, 7, 1, 0, 0, tzinfo=timezone.utc)

    encoded = mod.utc_to_server_api_datetime(utc)

    assert encoded == datetime(2022, 7, 1, 3, 0, tzinfo=timezone.utc)
    assert mod.server_to_utc(encoded.replace(tzinfo=None)) == utc.replace(tzinfo=None)


def test_daily_shards_are_create_new_single_row_group_and_never_mix_segments(tmp_path: Path) -> None:
    mod = load_module()
    chunk = mod.month_chunks(
        datetime(2022, 6, 1, tzinfo=timezone.utc),
        datetime(2022, 7, 1, tzinfo=timezone.utc),
    )[0]
    rates = _h1_rows(
        mod,
        [
            pd.Timestamp("2022-06-06 06:00:00", tz="UTC"),
            pd.Timestamp("2022-06-06 11:00:00", tz="UTC"),
            pd.Timestamp("2022-06-06 12:00:00", tz="UTC"),
        ],
    )
    frame, _ = mod.normalize_rates(rates, chunk)
    frame["request_id"] = chunk["request_id"]

    records, index = mod.write_daily_shards(frame, tmp_path / "root", {"extractor_sha256": "A" * 64})

    assert len(records) == 2
    assert set(row["segment"] for row in records) == {"pre12", "post12"}
    for row in records:
        path = tmp_path / "root" / row["shard_path"]
        assert parquet.ParquetFile(path).metadata.num_row_groups == 1
        loaded = pd.read_parquet(path)
        if row["segment"] == "pre12":
            assert (loaded["time_utc"].dt.hour < 12).all()
        else:
            assert (loaded["time_utc"].dt.hour >= 12).all()
        assert row["sha256"] == mod.sha256_file(path)
    assert index[pd.Timestamp("2022-06-06")]["pre12_sha256"]
    with pytest.raises(FileExistsError):
        mod.write_daily_shards(frame, tmp_path / "root", {"extractor_sha256": "A" * 64})


def test_decision_packet_is_outcome_blind_causal_four_arm_and_deterministic() -> None:
    mod = load_module()
    rows = []
    dates = pd.date_range("2019-01-01", periods=254, freq="D")
    for day_index, date in enumerate(dates):
        base = 1.0 + day_index * 0.001
        for hour in range(20):
            value = base + hour * 0.00001
            rows.append(
                {
                    "time_utc": date + pd.Timedelta(hours=hour),
                    "open": value,
                    "high": value + 0.0003,
                    "low": value - 0.0003,
                    "close": value + 0.0001,
                }
            )
    frame = pd.DataFrame(rows)
    decision_date = dates[-1]
    shard_index = {
        date: {
            "pre12_sha256": "A" * 64,
            "post12_sha256": "B" * 64,
        }
        for date in dates
    }

    first_payloads, _ = mod.build_packet_set(
        frame,
        shard_index,
        "C" * 64,
        mod.PLAN_SHA256,
        decision_dates=[decision_date],
    )
    second_payloads, _ = mod.build_packet_set(
        frame,
        shard_index,
        "C" * 64,
        mod.PLAN_SHA256,
        decision_dates=[decision_date],
    )
    first = json.loads(next(iter(first_payloads.values())))
    second = json.loads(next(iter(second_payloads.values())))

    assert first_payloads == second_payloads
    assert first == second
    assert pd.Timestamp(first["max_source_time_utc"]) < pd.Timestamp(first["decision_cutoff_utc"])
    assert first["challenger_stack_eligible"] is True
    assert first["negative_disagree_eligible"] is False
    assert mod.scan_packet_forbidden(first) == []
    serialized = json.dumps(first).lower()
    for forbidden in ('"open"', '"high"', '"low"', '"close"', '"pnl"', '"exit"', '"mfe"', '"mae"'):
        assert forbidden not in serialized


def test_m252_uses_minus_253_not_minus_252() -> None:
    mod = load_module()
    dates = pd.date_range("2020-01-01", periods=253, freq="D")
    closes = [2.0, 0.5] + [0.75] * 250 + [1.0]
    daily = pd.DataFrame(
        {
            "date_utc": dates,
            "valid": True,
            "daily_close": closes,
            "close_time_utc": dates + pd.Timedelta(hours=23),
        }
    ).set_index("date_utc")

    result = mod._m252(daily, dates[-1] + pd.Timedelta(days=1))

    assert result["direction"] == -1
    assert closes[-1] > closes[-252]
    assert closes[-1] < closes[-253]


def test_atr20_is_numeric_sma_true_range_shift1_and_post12_sentinel_is_excluded() -> None:
    mod = load_module()
    end = pd.Timestamp("2022-06-06 11:00:00")
    times = pd.date_range(end=end, periods=21, freq="h")
    rows = []
    for index, timestamp in enumerate(times):
        value = 100.0 + index * 0.5
        rows.append(
            {
                "time_utc": timestamp,
                "open": value,
                "high": value + 1.0,
                "low": value - 1.0,
                "close": value + 0.25,
            }
        )
    sentinel = {
        "time_utc": pd.Timestamp("2022-06-06 12:00:00"),
        "open": 1000.0,
        "high": 2000.0,
        "low": 1.0,
        "close": 1500.0,
    }
    frame = pd.DataFrame(rows + [sentinel])
    context = mod._decision_context(frame)

    result = mod._atr20(context, pd.Timestamp("2022-06-06"))

    assert result["value"] == pytest.approx(2.0)
    assert result["latest_time"] == end
    payloads, _ = mod.build_packet_set(
        frame,
        {
            pd.Timestamp("2022-06-05"): {
                "pre12_sha256": "A" * 64,
                "post12_sha256": "B" * 64,
            },
            pd.Timestamp("2022-06-06"): {"pre12_sha256": "C" * 64},
        },
        "C" * 64,
        mod.PLAN_SHA256,
        decision_dates=[pd.Timestamp("2022-06-06")],
    )
    packet = json.loads(next(iter(payloads.values())))
    assert pd.Timestamp(packet["max_source_time_utc"]) < pd.Timestamp(
        packet["decision_cutoff_utc"]
    )


def test_packet_files_and_jsonl_are_create_new_and_hash_bound(tmp_path: Path) -> None:
    mod = load_module()
    decision_date = pd.Timestamp("2022-01-03")
    frame = pd.DataFrame(
        [
            {
                "time_utc": decision_date + pd.Timedelta(hours=5),
                "open": 1.2,
                "high": 1.2003,
                "low": 1.1997,
                "close": 1.2001,
            }
        ]
    )
    payloads, _ = mod.build_packet_set(
        frame,
        {decision_date: {"pre12_sha256": "B" * 64}},
        "C" * 64,
        mod.PLAN_SHA256,
        decision_dates=[decision_date],
    )

    first = mod.write_packet_files(payloads, tmp_path / "root")
    rebuilt = mod.packet_set_sha256(payloads)

    assert first[0]["packet_file_sha256"] == mod.sha256_file(
        tmp_path / "root" / "decision_packets" / first[0]["packet_path"]
    )
    assert rebuilt == mod.packet_set_sha256(dict(payloads))
    with pytest.raises(FileExistsError):
        mod.write_packet_files(payloads, tmp_path / "root")


def test_builder_projection_cannot_be_refinalized_or_token_forged() -> None:
    mod = load_module()
    decision_date = pd.Timestamp("2022-01-03")
    frame = pd.DataFrame(
        [
            {
                "time_utc": decision_date + pd.Timedelta(hours=5),
                "open": 1.2,
                "high": 1.2003,
                "low": 1.1997,
                "close": 1.2001,
            }
        ]
    )
    payloads, _ = mod.build_packet_set(
        frame,
        {decision_date: {"pre12_sha256": "B" * 64}},
        "C" * 64,
        mod.PLAN_SHA256,
        decision_dates=[decision_date],
    )
    packet = json.loads(next(iter(payloads.values())))
    mutations = {
        "m252_direction": 1,
        "m6_direction": 1,
        "atr20": 0.001,
        "alignment": False,
        "control_m252_eligible": True,
        "control_m6_eligible": True,
        "challenger_stack_eligible": True,
        "negative_disagree_eligible": True,
        "valid_prior_close_count": 253,
        "exclusion_reason": None,
    }
    for field, forged_value in mutations.items():
        forged = dict(packet, **{field: forged_value})
        assert "packet_payload_sha256_mismatch" in mod.validate_packet_schema(forged)

    for forbidden_api in (
        "finalize_packet_hash",
        "packet_bytes",
        "_CausalSourceEvidence",
        "_CAUSAL_SOURCE_EVIDENCE_TOKEN",
    ):
        assert not hasattr(mod, forbidden_api), f"forgeable packet API remains: {forbidden_api}"


def test_packet_schema_rejects_nested_unknown_types_enums_values_and_paths() -> None:
    mod = load_module()
    base = _packet_base(mod)
    assert mod.validate_packet_schema(base, require_payload_hash=False) == []

    attacks = []
    nested = json.loads(json.dumps(base))
    nested["source_shard_chain_hashes"]["raw_path"] = r"C:\secret\raw.parquet"
    attacks.append(nested)
    wrong_type = dict(base, control_m252_eligible=1)
    attacks.append(wrong_type)
    wrong_enum = dict(base, split="HOLDOUT")
    attacks.append(wrong_enum)
    local_path = dict(base, exclusion_reason=r"D:\local\file")
    attacks.append(local_path)
    raw_value = dict(base, exclusion_reason="M1_OUTCOME")
    attacks.append(raw_value)
    for attack in attacks:
        assert mod.validate_packet_schema(attack, require_payload_hash=False)


@pytest.mark.parametrize(
    ("changes", "expected_failure"),
    [
        ({"opportunity_id": "2024-01-03", "decision_cutoff_utc": "2024-01-03T12:00:00", "max_source_time_utc": "2024-01-03T11:00:00"}, "opportunity_outside_frozen_range"),
        ({"split": "DESIGN"}, "split_date_mismatch"),
        ({"alignment": True}, "alignment_direction_mismatch"),
        ({"valid_prior_close_count": 252}, "m252_direction_requires_253_closes"),
        ({"decision_cutoff_utc": "2022-01-04T12:00:00"}, "invalid_decision_cutoff"),
        ({"max_source_time_utc": "2022-01-03T12:00:00"}, "noncausal_max_source_time"),
        ({"control_m252_eligible": False}, "control_m252_eligibility_mismatch"),
        ({"control_m6_eligible": False}, "control_m6_eligibility_mismatch"),
        ({"negative_disagree_eligible": False}, "negative_disagree_eligibility_mismatch"),
        ({"challenger_stack_eligible": True}, "challenger_stack_eligibility_mismatch"),
        ({"exclusion_reason": None}, "exclusion_reason_mismatch"),
        ({"atr20": None}, "control_m252_eligibility_mismatch"),
        ({"max_source_time_utc": "2022-01-02T23:00:00"}, "atr20_source_time_mismatch"),
        ({"m252_direction": None}, "missing_m252_direction_with_sufficient_history"),
    ],
)
def test_packet_schema_rejects_cross_field_impossible_combinations(
    changes: dict, expected_failure: str
) -> None:
    mod = load_module()
    packet = dict(_packet_base(mod), **changes)

    failures = mod.validate_packet_schema(packet, require_payload_hash=False)

    assert expected_failure in failures


def test_packet_schema_accepts_only_consistent_frozen_incomplete_partitions() -> None:
    mod = load_module()
    base = _packet_base(mod)
    disabled = {
        "control_m252_eligible": False,
        "control_m6_eligible": False,
        "challenger_stack_eligible": False,
        "negative_disagree_eligible": False,
    }
    packets = [
        dict(
            base,
            **disabled,
            m252_direction=None,
            valid_prior_close_count=252,
            alignment=None,
            exclusion_reason="INSUFFICIENT_M252_HISTORY",
        ),
        dict(
            base,
            **disabled,
            m252_direction=0,
            alignment=None,
            exclusion_reason="M252_EQUALITY",
        ),
        dict(
            base,
            **disabled,
            m6_direction=None,
            alignment=None,
            exclusion_reason="MISSING_SIX_HOUR_BAR",
        ),
        dict(
            base,
            **disabled,
            atr20=None,
            exclusion_reason="INSUFFICIENT_OR_INVALID_ATR20",
        ),
        dict(
            base,
            **{**disabled, "control_m252_eligible": True},
            m6_direction=0,
            alignment=None,
            exclusion_reason="M6_EQUALITY",
        ),
    ]

    for packet in packets:
        assert mod.validate_packet_schema(packet, require_payload_hash=False) == []


def test_packet_schema_rejects_causal_source_chain_and_calendar_count_attacks() -> None:
    mod = load_module()
    base = _packet_base(mod)

    missing_current_hash = json.loads(json.dumps(base))
    missing_current_hash["source_shard_chain_hashes"]["current_pre12_sha256"] = None
    missing_current_hash["source_chain_sha256"] = mod.sha256_bytes(
        mod.canonical_json_bytes(missing_current_hash["source_shard_chain_hashes"])
    )

    current_feature_with_prior_max = dict(
        base, max_source_time_utc="2022-01-02T23:00:00"
    )

    impossible_calendar_count = dict(
        base,
        opportunity_id="2016-01-04",
        split="DESIGN",
        decision_cutoff_utc="2016-01-04T12:00:00",
        max_source_time_utc="2016-01-04T11:00:00",
        valid_prior_close_count=368,
    )

    attacks = [
        (missing_current_hash, "current_feature_requires_current_pre12_sha256"),
        (current_feature_with_prior_max, "current_feature_max_source_mismatch"),
        (impossible_calendar_count, "valid_prior_close_count_exceeds_calendar_bound"),
    ]
    for packet, expected_failure in attacks:
        failures = mod.validate_packet_schema(packet, require_payload_hash=False)
        assert expected_failure in failures


@pytest.mark.parametrize(
    ("valid_prior_close_count", "max_source_time_utc"),
    [
        (0, None),
        (0, "2022-01-02T23:00:00"),
        (252, "2022-01-02T23:00:00"),
    ],
)
def test_packet_schema_rejects_unbound_exclusion_source_assertions(
    valid_prior_close_count: int, max_source_time_utc: str | None
) -> None:
    mod = load_module()
    packet = dict(
        _packet_base(mod),
        m252_direction=None,
        m6_direction=None,
        alignment=None,
        atr20=None,
        control_m252_eligible=False,
        control_m6_eligible=False,
        challenger_stack_eligible=False,
        negative_disagree_eligible=False,
        exclusion_reason="INSUFFICIENT_M252_HISTORY",
        valid_prior_close_count=valid_prior_close_count,
        max_source_time_utc=max_source_time_utc,
    )
    packet["source_shard_chain_hashes"] = {
        "prior_completed_shards_sha256": "A" * 64,
        "current_pre12_sha256": None,
    }
    packet["source_chain_sha256"] = mod.sha256_bytes(
        mod.canonical_json_bytes(packet["source_shard_chain_hashes"])
    )

    failures = mod.validate_packet_schema(packet, require_payload_hash=False)

    assert "causal_source_evidence_required" in failures


@pytest.mark.parametrize("prior_close_count", [0, 252])
def test_builder_derives_causal_exclusion_time_from_current_bound_shard(
    prior_close_count: int,
) -> None:
    mod = load_module()
    decision_date = pd.Timestamp("2016-01-04")
    rows = []
    shard_index = {}
    if prior_close_count:
        prior_dates = pd.date_range(
            end=decision_date - pd.Timedelta(days=1),
            periods=prior_close_count,
            freq="D",
        )
        for day_index, date in enumerate(prior_dates):
            shard_index[date] = {
                "pre12_sha256": f"{day_index % 16:X}" * 64,
                "post12_sha256": f"{(day_index + 1) % 16:X}" * 64,
            }
            for hour in range(20):
                value = 1.0 + day_index * 0.001 + hour * 0.00001
                rows.append(
                    {
                        "time_utc": date + pd.Timedelta(hours=hour),
                        "open": value,
                        "high": value + 0.0003,
                        "low": value - 0.0003,
                        "close": value + 0.0001,
                    }
                )
    current_hash = "E" * 64
    shard_index[decision_date] = {"pre12_sha256": current_hash}
    rows.append(
        {
            "time_utc": decision_date + pd.Timedelta(hours=5),
            "open": 1.2,
            "high": 1.2003,
            "low": 1.1997,
            "close": 1.2001,
        }
    )

    payloads, _ = mod.build_packet_set(
        pd.DataFrame(rows),
        shard_index,
        "C" * 64,
        mod.PLAN_SHA256,
        decision_dates=[decision_date],
    )
    packet = json.loads(next(iter(payloads.values())))

    assert packet["valid_prior_close_count"] == prior_close_count
    assert packet["exclusion_reason"] == "INSUFFICIENT_M252_HISTORY"
    assert packet["source_shard_chain_hashes"]["current_pre12_sha256"] == current_hash
    assert packet["max_source_time_utc"] == "2016-01-04T05:00:00"


def test_builder_reachable_states_exhaust_packet_exclusion_enum() -> None:
    mod = load_module()
    observed = set()
    modes = {
        "aligned": None,
        "disagree": "M252_M6_DISAGREE",
        "m6_equality": "M6_EQUALITY",
        "m252_equality": "M252_EQUALITY",
        "missing_m6": "MISSING_SIX_HOUR_BAR",
        "invalid_atr": "INSUFFICIENT_OR_INVALID_ATR20",
        "insufficient_m252": "INSUFFICIENT_M252_HISTORY",
    }
    for mode, expected_exclusion in modes.items():
        decision_date = pd.Timestamp("2019-09-12")
        rows = []
        shard_index = {}
        if mode != "insufficient_m252":
            prior_dates = pd.date_range(
                end=decision_date - pd.Timedelta(days=1), periods=253, freq="D"
            )
            for day_index, date in enumerate(prior_dates):
                shard_index[date] = {
                    "pre12_sha256": "A" * 64,
                    "post12_sha256": "B" * 64,
                }
                for hour in range(20):
                    if mode == "m252_equality":
                        value = 1.0 + hour * 0.00001
                        high, low, close = value + 0.0003, value - 0.0003, value + 0.0001
                    elif mode == "invalid_atr" and date == prior_dates[-1]:
                        value = 1.5
                        high = low = close = value
                    else:
                        value = 1.0 + day_index * 0.001 + hour * 0.00001
                        high, low, close = value + 0.0003, value - 0.0003, value + 0.0001
                    rows.append(
                        {
                            "time_utc": date + pd.Timedelta(hours=hour),
                            "open": value,
                            "high": high,
                            "low": low,
                            "close": close,
                        }
                    )
        shard_index[decision_date] = {"pre12_sha256": "C" * 64}
        current_hours = [5] if mode in {"missing_m6", "insufficient_m252"} else list(range(12))
        for hour in current_hours:
            if mode == "disagree":
                value = 2.0 - hour * 0.001
                high, low, close = value + 0.0003, value - 0.0003, value - 0.0001
            elif mode in {"m6_equality", "invalid_atr"}:
                value = 1.5
                high = low = close = value
            else:
                value = 2.0 + hour * 0.001
                high, low, close = value + 0.0003, value - 0.0003, value + 0.0001
            rows.append(
                {
                    "time_utc": decision_date + pd.Timedelta(hours=hour),
                    "open": value,
                    "high": high,
                    "low": low,
                    "close": close,
                }
            )

        payloads, _ = mod.build_packet_set(
            pd.DataFrame(rows),
            shard_index,
            "D" * 64,
            mod.PLAN_SHA256,
            decision_dates=[decision_date],
        )
        packet = json.loads(next(iter(payloads.values())))
        assert packet["exclusion_reason"] == expected_exclusion
        assert mod.validate_packet_schema(packet) == []
        observed.add(packet["exclusion_reason"])

    assert observed == mod.PACKET_EXCLUSION_REASONS


def test_persisted_shards_are_reopened_validated_and_rebuild_packets_identically(tmp_path: Path) -> None:
    mod = load_module()
    frame, request_records = _full_frozen_source_fixture(mod)
    root = tmp_path / "frozen" / "attempt"
    runtime = _runtime_provenance_fixture(mod)

    receipt = mod.persist_source_package(
        frame,
        request_records,
        root,
        runtime,
        decision_dates=[pd.Timestamp("2019-09-11")],
    )
    reopened, _, validation = mod.reopen_validate_shards(root)

    assert len(reopened) == len(frame)
    assert validation["physical_partition_status"] == "PASS"
    assert receipt["deterministic_rebuild_status"] == "PASS_DISK_REOPEN"
    assert (
        receipt["strategy_process_raw_source_access"]
        == "NOT_YET_VERIFIED_STAGE0_REQUIRED"
    )
    assert (root / "source_manifest.jsonl").is_file()
    assert (root / "source_validation_receipt.json").is_file()
    assert (root / "decision_packet_manifest.jsonl").is_file()
    assert (root / "decision_packet_receipt.json").is_file()
    receipt_text = (root / "decision_packet_receipt.json").read_text(encoding="utf-8")
    assert ":\\" not in receipt_text
    assert str(tmp_path) not in receipt_text


@pytest.mark.parametrize("identity_style", ["truncated", "arbitrary_96_ids"])
def test_reopen_requires_exact_frozen_96_request_universe(
    tmp_path: Path, identity_style: str
) -> None:
    mod = load_module()
    date = pd.Timestamp("2022-06-06")
    rows = []
    for hour in range(20):
        utc_time = date + pd.Timedelta(hours=hour)
        server_time = _server_time_for_utc(mod, utc_time)
        value = 1.10 + hour * 0.0001
        rows.append(
            {
                "time_server": server_time,
                "time_utc": utc_time,
                "utc_offset_h": int((server_time - utc_time) / pd.Timedelta(hours=1)),
                "open": value,
                "high": value + 0.0003,
                "low": value - 0.0003,
                "close": value + 0.0001,
                "tick_volume": 100,
                "spread": 10,
                "real_volume": 0,
                "request_id": "TEST-001",
            }
        )
    frame = pd.DataFrame(rows)
    root = tmp_path / identity_style
    runtime_hashes = _runtime_hashes(_runtime_provenance_fixture(mod))
    shards, _ = mod.write_daily_shards(frame, root, runtime_hashes)
    request = _request_record(mod, frame, "TEST-001")
    request["runtime_hashes"] = runtime_hashes
    requests = [request]
    if identity_style == "arbitrary_96_ids":
        requests = [dict(request, request_id=f"ARBITRARY-{index:03d}") for index in range(96)]
    mod.write_jsonl_new(root / "source_manifest.jsonl", [*requests, *shards])

    with pytest.raises(RuntimeError, match="INVALID_ENGINEERING.*request universe"):
        mod.reopen_validate_shards(root)


@pytest.mark.parametrize("tamper", ["missing", "extra", "bad_hash"])
def test_persist_rejects_runtime_provenance_before_creating_artifacts(
    tmp_path: Path, tamper: str
) -> None:
    mod = load_module()
    runtime = _runtime_provenance_fixture(mod)
    if tamper == "missing":
        runtime.pop("python_executable_sha256")
    elif tamper == "extra":
        runtime["unexpected_runtime_field"] = "forbidden"
    else:
        runtime["terminal_executable_sha256"] = "not-a-hash"
    root = tmp_path / tamper

    with pytest.raises(RuntimeError, match="INVALID_ENGINEERING.*runtime provenance"):
        mod.persist_source_package(
            pd.DataFrame(), [], root, runtime, decision_dates=[]
        )
    assert not root.exists()


@pytest.mark.parametrize(
    "tamper",
    [
        "shard_bytes",
        "shard_split",
        "shard_date",
        "shard_segment",
        "shard_rows",
        "shard_sha",
        "shard_canonical_hash",
        "shard_first_utc",
        "shard_request_ids",
        "request_range",
        "request_first_server",
        "request_response_rows",
        "duplicate_shard_record",
        "duplicate_request_record",
        "orphan_file",
    ],
)
def test_reopen_rejects_manifest_content_request_and_file_set_tampering(
    tmp_path: Path, tamper: str
) -> None:
    mod = load_module()
    frame, request_records = _sparse_frozen_source_fixture(mod)
    root = tmp_path / tamper
    runtime_hashes = _runtime_hashes(_runtime_provenance_fixture(mod))
    shard_records, _ = mod.write_daily_shards(frame, root, runtime_hashes)
    for request in request_records:
        request["runtime_hashes"] = runtime_hashes
    records = [*request_records, *shard_records]
    first_shard = len(request_records)

    if tamper == "shard_bytes":
        records[first_shard]["bytes"] += 1
    elif tamper == "shard_split":
        records[first_shard]["split"] = "DESIGN"
    elif tamper == "shard_date":
        records[first_shard]["date_utc"] = "2015-01-03"
    elif tamper == "shard_segment":
        records[first_shard]["segment"] = "post12"
    elif tamper == "shard_rows":
        records[first_shard]["rows"] += 1
    elif tamper == "shard_sha":
        records[first_shard]["sha256"] = "F" * 64
    elif tamper == "shard_canonical_hash":
        records[first_shard]["canonical_row_content_sha256"] = "F" * 64
    elif tamper == "shard_first_utc":
        records[first_shard]["first_utc_time"] = "2015-01-03T00:00:00"
    elif tamper == "shard_request_ids":
        records[first_shard]["request_ids"] = ["ORPHAN-REQUEST"]
    elif tamper == "request_range":
        records[0]["canonical_from_utc"] = "2015-01-03T00:00:00+00:00"
    elif tamper == "request_first_server":
        records[0]["response"]["first_server_time"] = "2015-01-02T04:00:00"
    elif tamper == "request_response_rows":
        records[0]["response"]["rows"] += 1
    elif tamper == "duplicate_shard_record":
        records.append(dict(records[first_shard]))
    elif tamper == "duplicate_request_record":
        records.append(dict(records[0]))
    elif tamper == "orphan_file":
        original = root / records[first_shard]["shard_path"]
        orphan = root / "raw_h1" / "WARMUP" / "2015-01-03" / "pre12.parquet"
        orphan.parent.mkdir(parents=True)
        orphan.write_bytes(original.read_bytes())
    mod.write_jsonl_new(root / "source_manifest.jsonl", records)

    with pytest.raises(RuntimeError, match="INVALID_ENGINEERING"):
        mod.reopen_validate_shards(root)


def test_output_confinement_exclusive_paths_and_unique_quarantine(tmp_path: Path) -> None:
    mod = load_module()
    frozen = tmp_path / "trendstack_002"
    outside = tmp_path / "outside"
    assert mod.validate_output_root(frozen, frozen) == frozen.resolve()
    assert mod.validate_output_root(frozen / "child", frozen) == (frozen / "child").resolve()
    with pytest.raises(RuntimeError, match="INVALID_ENGINEERING.*root"):
        mod.validate_output_root(outside, frozen)
    with pytest.raises(RuntimeError, match="INVALID_ENGINEERING.*path"):
        mod.write_packet_files({"../escape.json": b"{}"}, frozen)

    attempt = mod.create_attempt_root(frozen, frozen_root=frozen)
    (attempt / "partial.txt").write_text("partial", encoding="utf-8")
    quarantine = mod.quarantine_attempt(frozen, attempt)
    assert quarantine.is_dir()
    assert (quarantine / "partial.txt").is_file()
    second = mod.create_attempt_root(frozen, frozen_root=frozen)
    assert second.name != quarantine.name


class _FakeMt5:
    ACCOUNT_TRADE_MODE_DEMO = 0

    def __init__(self, *, initialize_result=True, wrong_broker=True):
        self.initialize_result = initialize_result
        self.wrong_broker = wrong_broker
        self.initialize_calls = []
        self.shutdown_calls = 0

    def initialize(self, **kwargs):
        self.initialize_calls.append(kwargs)
        return self.initialize_result

    def shutdown(self):
        self.shutdown_calls += 1

    def last_error(self):
        return (1, "fake")

    def terminal_info(self):
        return SimpleNamespace(build=6063, trade_allowed=False, data_path="X:/demo")

    def account_info(self):
        return SimpleNamespace(
            trade_mode=0,
            server="MetaQuotes-Demo" if self.wrong_broker else "FivePercentOnline-Real",
            company="MetaQuotes Ltd." if self.wrong_broker else "Five Percent Online Ltd",
        )

    def symbol_info(self, _symbol):
        return SimpleNamespace(digits=5, point=0.00001)


def test_portable_initialize_and_shutdown_attempted_on_init_and_guard_failures(tmp_path: Path) -> None:
    mod = load_module()
    terminal = tmp_path / "terminal64.exe"
    terminal.write_bytes(b"terminal")

    init_fail = _FakeMt5(initialize_result=False)
    with pytest.raises(RuntimeError, match="initialize"):
        mod.acquire_source(
            terminal,
            tmp_path / "root1",
            mt5_api=init_fail,
            frozen_root=tmp_path,
        )
    assert init_fail.initialize_calls[0]["portable"] is True
    assert init_fail.shutdown_calls == 1

    guard_fail = _FakeMt5(initialize_result=True, wrong_broker=True)
    with pytest.raises(RuntimeError, match="broker"):
        mod.acquire_source(
            terminal,
            tmp_path / "root2",
            mt5_api=guard_fail,
            frozen_root=tmp_path,
        )
    assert guard_fail.initialize_calls[0]["portable"] is True
    assert guard_fail.shutdown_calls == 1
    assert not (tmp_path / "root2").exists()


def test_source_contains_no_order_or_backtest_surface() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8").lower()
    assert "copy_rates_range" in source
    assert "timeframe_h1" in source
    for forbidden_call in (
        "order_send(",
        "positions_get(",
        "history_deals_get(",
        "copy_ticks",
        "timeframe_m1",
    ):
        assert forbidden_call not in source
