#!/usr/bin/env python3
"""No-outcome audit of Unicorn probe/source signal-identity semantics."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5
import numpy as np

import probe_unicorn_event_anchored_closedbar as event_probe


BASE_OVERLAP = event_probe.best_overlap_ratio


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def storage_inventory(root: Path) -> dict[str, object]:
    digest = hashlib.sha256()
    files = sorted((path for path in root.rglob("*") if path.is_file()), key=lambda path: str(path).lower())
    total_bytes = 0
    for path in files:
        stat = path.stat()
        total_bytes += stat.st_size
        row = f"{path.relative_to(root)}|{stat.st_size}|{stat.st_mtime_ns}\n"
        digest.update(row.encode("utf-8"))
    return {
        "root": str(root.resolve()),
        "file_count": len(files),
        "total_bytes": total_bytes,
        "metadata_sha256": digest.hexdigest().upper(),
    }


def invalidated_through_decision(
    rates: np.ndarray, sweep_index: int, left: int, direction: int, extreme: float
) -> bool:
    """Check every closed bar after the sweep through the decision bar."""
    decision_index = left + 2
    closes = rates["close"][sweep_index + 1 : decision_index + 1].astype(float)
    if direction > 0:
        return bool(np.any(closes <= extreme))
    return bool(np.any(closes >= extreme))


def overlap_with_source_lookback(
    rates: np.ndarray, _start: int, end: int, direction: int, lo: float, hi: float
) -> float:
    """Mirror InpBreakerLookback=6 used by the frozen Model-0 source."""
    return BASE_OVERLAP(rates, max(0, end - 6), end, direction, lo, hi)


def identities(rows: list[dict[str, object]]) -> set[str]:
    return {
        f"{row['decision_time_utc']}|{row['direction']}"
        for row in rows
    }


def detect_variant(
    rates: np.ndarray,
    h4: np.ndarray,
    d1: np.ndarray,
    invalidation,
    overlap,
) -> list[dict[str, object]]:
    original_invalidation = event_probe.structurally_invalidated
    original_overlap = event_probe.best_overlap_ratio
    try:
        event_probe.structurally_invalidated = invalidation
        event_probe.best_overlap_ratio = overlap
        candidates, _ = event_probe.detect(rates, h4, d1)
        return candidates
    finally:
        event_probe.structurally_invalidated = original_invalidation
        event_probe.best_overlap_ratio = original_overlap


def variant_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    ids = identities(rows)
    return {
        "candidate_count": len(rows),
        "unique_identity_count": len(ids),
        "long_count": sum(row["direction"] == "long" for row in rows),
        "short_count": sum(row["direction"] == "short" for row in rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--terminal", type=Path, required=True)
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--protected-common-root", type=Path, required=True)
    args = parser.parse_args()

    common_before = storage_inventory(args.protected_common_root)

    if not mt5.initialize(path=str(args.terminal), timeout=60_000, portable=True):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        terminal = mt5.terminal_info()
        if terminal is None or not terminal.connected:
            raise RuntimeError("MT5 terminal is not connected")
        data_path = Path(terminal.data_path).resolve()
        if data_path.drive.upper() != "D:":
            raise RuntimeError(f"portable MT5 data path must be on D:, got {data_path}")

        warmup = event_probe.WARMUP_FROM
        end = event_probe.WINDOW_TO
        m5 = mt5.copy_rates_range(args.symbol, mt5.TIMEFRAME_M5, warmup, end)
        h4 = mt5.copy_rates_range(args.symbol, mt5.TIMEFRAME_H4, warmup, end)
        d1 = mt5.copy_rates_range(args.symbol, mt5.TIMEFRAME_D1, warmup, end)
        if m5 is None or h4 is None or d1 is None:
            raise RuntimeError(f"MT5 rates unavailable: {mt5.last_error()}")

        frozen_probe = detect_variant(
            m5, h4, d1, event_probe.structurally_invalidated, BASE_OVERLAP
        )
        model0_source = detect_variant(
            m5, h4, d1, event_probe.structurally_invalidated, overlap_with_source_lookback
        )
        invalidation_fixed_probe8 = detect_variant(
            m5, h4, d1, invalidated_through_decision, BASE_OVERLAP
        )
        corrected_source = detect_variant(
            m5, h4, d1, invalidated_through_decision, overlap_with_source_lookback
        )

        frozen_ids = identities(frozen_probe)
        source_ids = identities(model0_source)
        fixed_probe_ids = identities(invalidation_fixed_probe8)
        corrected_ids = identities(corrected_source)
        common_after = storage_inventory(args.protected_common_root)
        payload = {
            "schema_version": "unicorn_signal_identity_audit.v1",
            "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "purpose": "correctness and candidate identity only; no fills or outcomes",
            "outcomes_evaluated": False,
            "terminal": {
                "company": terminal.company,
                "build": terminal.build,
                "connected": bool(terminal.connected),
                "portable": True,
                "data_path": str(data_path),
            },
            "data": {
                "symbol": args.symbol,
                "window_from": "2024.01.01",
                "window_to_inclusive": "2025.12.25",
                "m5_bars": len(m5),
                "h4_bars": len(h4),
                "d1_bars": len(d1),
                "raw_bars_persisted_to_workspace": False,
            },
            "source_identity": {
                "audit_script_sha256": sha256_file(Path(__file__)),
                "frozen_probe_script_sha256": sha256_file(Path(event_probe.__file__)),
                "canonical_ea_sha256": sha256_file(Path(__file__).resolve().parent.parent / "EA_UnicornPrecisionScalper.mq5"),
            },
            "protected_common_storage": {
                "before": common_before,
                "after": common_after,
                "unchanged": common_before == common_after,
            },
            "variants": {
                "frozen_build_probe_breaker8_invalidation_to_left": variant_summary(frozen_probe),
                "model0_source_breaker6_invalidation_to_left": variant_summary(model0_source),
                "invalidation_fixed_breaker8_through_decision": variant_summary(invalidation_fixed_probe8),
                "corrected_source_breaker6_through_decision": variant_summary(corrected_source),
            },
            "identity_deltas": {
                "probe8_vs_model0_source6_symmetric_difference": len(frozen_ids ^ source_ids),
                "probe8_removed_by_full_invalidation": len(frozen_ids - fixed_probe_ids),
                "source6_removed_by_full_invalidation": len(source_ids - corrected_ids),
                "corrected_source_vs_frozen_probe_symmetric_difference": len(corrected_ids ^ frozen_ids),
                "source6_removed_identity_sample": sorted(source_ids - corrected_ids)[:20],
            },
            "verdict": "IDENTITY_DRIFT" if frozen_ids != corrected_ids else "IDENTITY_MATCH",
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(payload["variants"], indent=2))
        print(json.dumps(payload["identity_deltas"], indent=2))
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
