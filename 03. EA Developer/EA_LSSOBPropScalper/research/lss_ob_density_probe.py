#!/usr/bin/env python3
"""Run the frozen LSS-OB M15 pre-outcome fidelity/cadence probe."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[2]
SDK = WORKSPACE / "02. AlphaFactory" / "tools" / "research"
if str(SDK) not in sys.path:
    sys.path.insert(0, str(SDK))

from sealed_loader import load_sealed_bars, sha256_file  # noqa: E402

from lss_ob_probe_engine import (  # noqa: E402
    CONTRACT_ID,
    FrozenSpec,
    NewsGuard,
    assert_no_outcome_schema,
    attach_context,
    density_summary,
    density_verdict,
    resample_ohlc,
    scan_detector,
)


HYPOTHESIS_ID = "HYP-LSS-OB-REPL-EURUSD-M15-001"
PREREG = HERE / f"{HYPOTHESIS_ID}_PROBE_PLAN.md"
EXPECTED_PREREG_SHA = "7F051DE01B89E6A41A01B0C7EC023ED7435AF74420EA2E6D89AB9348279C26BD"
M1_PATH = WORKSPACE / "02. AlphaFactory" / "data" / "fivepercent" / "EURUSD" / "EURUSD_M1_2015_now.parquet"
EXPECTED_M1_SHA = "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"
MANIFEST_PATH = M1_PATH.parent / "manifest.json"
EXPECTED_MANIFEST_SHA = "2CD996FD4416B1E888BF1C9D272BF49056DB3A4CE477CF74FA4E31D474A41B54"
NEWS_PATH = WORKSPACE / "02. AlphaFactory" / "data" / "forexfactory" / "EURUSD" / "news_events" / "forexfactory_high_impact_eurusd_2019_2022.csv"
EXPECTED_NEWS_SHA = "80B9DE46517B42F8B1D9A3ACCEFA6CC6D3DCB4DD06CAE357F16DE46228C64307"
HOLDOUT_START = pd.Timestamp("2023-01-01T00:00:00")
WINDOW_START = pd.Timestamp("2019-01-03T00:00:00")
PARITY_PATH = HERE / "evidence" / f"{HYPOTHESIS_ID}_NATIVE_MT5_PARITY.json"


def verify_hash(path: Path, expected: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"SHA mismatch for {path}: expected={expected} actual={actual}")


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def write_events(path: Path, events: list[dict]) -> None:
    fieldnames = list(events[0].keys()) if events else [
        "event_id",
        "contract_id",
        "arm",
        "symbol",
        "timeframe",
        "direction",
        "decision_time_utc",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(events)


def run(output_dir: Path) -> dict:
    verify_hash(PREREG, EXPECTED_PREREG_SHA)
    verify_hash(M1_PATH, EXPECTED_M1_SHA)
    verify_hash(MANIFEST_PATH, EXPECTED_MANIFEST_SHA)
    verify_hash(NEWS_PATH, EXPECTED_NEWS_SHA)
    if not PARITY_PATH.is_file():
        raise RuntimeError("native MT5 parity receipt is required before density verdict")
    parity = json.loads(PARITY_PATH.read_text(encoding="utf-8"))
    if (
        parity.get("hypothesis_id") != HYPOTHESIS_ID
        or parity.get("overall") != "PASS"
        or parity.get("outcomes_included") is not False
        or int(parity.get("holdout_bars_loaded", -1)) != 0
        or parity.get("detector_parity", {}).get("event_identity_status") != "PASS"
        or parity.get("detector_parity", {}).get("funnel_identity_status") != "PASS"
    ):
        raise RuntimeError("native MT5 parity receipt is not a fail-closed PASS")

    columns = ["time_server", "time_utc", "utc_offset_h", "open", "high", "low", "close", "tick_volume"]
    loaded, seal = load_sealed_bars(M1_PATH, HOLDOUT_START, time_col="time_utc")
    m1 = loaded.loc[loaded["time_utc"] >= WINDOW_START, columns].copy().reset_index(drop=True)
    if len(m1) == 0 or pd.Timestamp(m1["time_utc"].max()) >= HOLDOUT_START:
        raise RuntimeError("holdout seal or frozen window violation")

    spec = FrozenSpec()
    m15 = resample_ohlc(m1, "15min")
    h1 = resample_ohlc(m1, "1h")
    h4 = resample_ohlc(m1, "4h")
    m15 = attach_context(m15, h1, h4, spec)
    news_df = pd.read_csv(NEWS_PATH, usecols=["event_time_utc"])
    news = NewsGuard(pd.to_datetime(news_df["event_time_utc"], utc=True), spec.news_blackout_minutes)
    events, funnel = scan_detector(m15, m1, news, spec)
    density = density_summary(events)
    verdict, gates = density_verdict(density)

    output_dir.mkdir(parents=True, exist_ok=True)
    event_path = output_dir / "HYP-LSS-OB-REPL-EURUSD-M15-001_DENSITY_EVENTS.csv"
    write_events(event_path, events)
    artifact = {
        "schema_version": "lss_ob_no_outcome_density_probe.v1",
        "authority": "PRE_OUTCOME_FIDELITY_CADENCE_ONLY",
        "hypothesis_id": HYPOTHESIS_ID,
        "contract_id": CONTRACT_ID,
        "promotion_eligible": False,
        "performance_metrics_authorized": False,
        "outcomes_included": False,
        "model0_authorized": False,
        "source_build_authorized": verdict == "DENSITY_FEASIBLE_ONLY",
        "verdict": verdict,
        "input_identity": {
            "prereg_path": PREREG.relative_to(WORKSPACE).as_posix(),
            "prereg_sha256": EXPECTED_PREREG_SHA,
            "manifest_path": MANIFEST_PATH.relative_to(WORKSPACE).as_posix(),
            "manifest_sha256": EXPECTED_MANIFEST_SHA,
            "m1_path": M1_PATH.relative_to(WORKSPACE).as_posix(),
            "m1_sha256": EXPECTED_M1_SHA,
            "news_path": NEWS_PATH.relative_to(WORKSPACE).as_posix(),
            "news_sha256": EXPECTED_NEWS_SHA,
            "engine_sha256": file_sha(HERE / "lss_ob_probe_engine.py"),
            "runner_sha256": file_sha(Path(__file__)),
            "ohlc_parity_status": "PASS_NATIVE_M1_UTC_REPLAY",
            "parity_path": PARITY_PATH.relative_to(WORKSPACE).as_posix(),
            "parity_sha256": file_sha(PARITY_PATH),
        },
        "seal": seal | {
            "bars_loaded_in_frozen_window": int(len(m1)),
            "first_bar_loaded": str(pd.Timestamp(m1["time_utc"].min())),
            "last_bar_loaded": str(pd.Timestamp(m1["time_utc"].max())),
            "holdout_bars_loaded": 0,
        },
        "resample": {
            "m15_bars": int(len(m15)),
            "m15_partial_nonempty_bins": int((m15["m1_count"] < 15).sum()),
            "h1_bars": int(len(h1)),
            "h4_bars": int(len(h4)),
            "bar_labels": "UTC_OPEN_LEFT_CLOSED",
        },
        "frozen_spec": spec.__dict__,
        "funnel": funnel,
        "density": density,
        "gates": gates,
        "events_path": event_path.relative_to(WORKSPACE).as_posix(),
        "events_sha256": file_sha(event_path),
        "event_count_all_arms": int(len(events)),
    }
    assert_no_outcome_schema(artifact)
    artifact_path = output_dir / "HYP-LSS-OB-REPL-EURUSD-M15-001_DENSITY_PROBE.json"
    artifact_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"artifact": str(artifact_path), "verdict": verdict, "density": density}, indent=2))
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=HERE / "evidence")
    args = parser.parse_args()
    run(args.output_dir.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
