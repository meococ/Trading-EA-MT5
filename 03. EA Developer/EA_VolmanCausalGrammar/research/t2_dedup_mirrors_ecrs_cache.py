"""Cache-only successor for the frozen ECRS identity mirror.

The frozen mirror recomputes two full rolling arrays for every signal index.
This successor computes those same arrays once per immutable state and changes
no gate, threshold, source, schedule, event key or comparison behavior.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from math import isfinite
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

import t2_dedup_mirrors as frozen


REPO_ROOT = frozen.REPO_ROOT.resolve()
LOCK_PATH = REPO_ROOT / "04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_P3_ECRS_CACHE_LOCK_V4.json"
LOCK_SCHEMA = "t2_p3_ecrs_cache_lock.v4"


def build_cached_ecrs_state(
    rows: Sequence[frozen.EcrsBar | Mapping[str, Any]],
) -> dict[str, Any]:
    """Return the frozen state plus the two formerly repeated arrays."""
    state = frozen._ecrs_state(rows)
    state["atr_sma20"] = frozen._rolling_mean(state["atr14"], 20)
    state["tv_sma20"] = frozen._rolling_mean(state["volumes"], 20)
    return state


def ecrs_v1_gate_trace_cached_from_state(
    state: Mapping[str, Any],
    signal_index: int,
    *,
    symbol: str,
    timeframe: str,
    news_calendar: frozen.NewsCalendar,
    allow_formula_generalization: bool,
) -> frozen.EcrsGateTrace:
    """Exact frozen trace with only rolling-array lookup substituted."""
    bars: list[frozen.EcrsBar] = state["bars"]
    if signal_index <= 0 or signal_index >= len(bars) - 1:
        return frozen.EcrsGateTrace(
            signal_index,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            None,
        )

    closes: list[float] = state["closes"]
    highs: list[float] = state["highs"]
    lows: list[float] = state["lows"]
    volumes: list[float] = state["volumes"]
    atr14: list[float | None] = state["atr14"]
    atr_sma20: list[float | None] = state["atr_sma20"]
    ema20: list[float | None] = state["ema20"]
    tv_sma20: list[float | None] = state["tv_sma20"]
    er: list[float | None] = state["er"]
    i = signal_index

    g1 = frozen.ecrs_er_cross(er[i - 1], er[i])
    g2 = (
        atr14[i - 1] is not None
        and atr_sma20[i - 1] is not None
        and float(atr14[i - 1]) <= 0.70 * float(atr_sma20[i - 1])
    )
    g3_long = i >= 12 and closes[i] > max(highs[i - 12 : i])
    g3_short = i >= 12 and closes[i] < min(lows[i - 12 : i])
    g3 = g3_long or g3_short
    g4 = tv_sma20[i - 1] is not None and volumes[i] >= 1.7 * float(tv_sma20[i - 1])
    ema_now = ema20[i]
    ema_lag = ema20[i - 3] if i >= 3 else None
    g5_long = (
        ema_now is not None
        and ema_lag is not None
        and closes[i] > float(ema_now)
        and float(ema_now) > float(ema_lag)
    )
    g5_short = (
        ema_now is not None
        and ema_lag is not None
        and closes[i] < float(ema_now)
        and float(ema_now) < float(ema_lag)
    )
    direction: frozen.Side | None = None
    if g3_long and g5_long:
        direction = "LONG"
    elif g3_short and g5_short:
        direction = "SHORT"
    entry = bars[i + 1]
    g6 = (
        entry.time_utc - bars[i].time_utc == frozen.timedelta(minutes=5)
        and frozen._session_ok(entry.time_utc)
    )
    g7 = frozen._news_pass(entry.time_utc, news_calendar)
    spread_pips = entry.spread / 10.0
    g8 = isfinite(spread_pips) and 0.0 < spread_pips <= 0.8
    if not frozen._scope_ok(
        symbol,
        timeframe,
        entry.time_utc,
        allow_formula_generalization=allow_formula_generalization,
    ):
        g6 = False
    return frozen.EcrsGateTrace(i, g1, g2, g3, g4, bool(direction), g6, g7, g8, direction)


def ecrs_v1_gate_trace_cached(
    rows: Sequence[frozen.EcrsBar | Mapping[str, Any]],
    signal_index: int,
    *,
    symbol: str,
    news_calendar: frozen.NewsCalendar | None,
    timeframe: str = "M5",
    allow_formula_generalization: bool = False,
    allow_synthetic_calendar: bool = False,
) -> frozen.EcrsGateTrace:
    calendar = frozen._require_news_calendar(
        news_calendar,
        allow_synthetic_calendar=allow_synthetic_calendar,
    )
    state = build_cached_ecrs_state(rows)
    return ecrs_v1_gate_trace_cached_from_state(
        state,
        signal_index,
        symbol=symbol,
        timeframe=timeframe,
        news_calendar=calendar,
        allow_formula_generalization=allow_formula_generalization,
    )


def emit_ecrs_v1_identities_cached(
    rows: Sequence[frozen.EcrsBar | Mapping[str, Any]],
    *,
    symbol: str,
    news_calendar: frozen.NewsCalendar | None,
    timeframe: str = "M5",
    allow_formula_generalization: bool = False,
    allow_synthetic_calendar: bool = False,
) -> list[dict[str, Any]]:
    """Emit the same identities with O(n) rolling-state construction."""
    calendar = frozen._require_news_calendar(
        news_calendar,
        allow_synthetic_calendar=allow_synthetic_calendar,
    )
    state = build_cached_ecrs_state(rows)
    bars: list[frozen.EcrsBar] = state["bars"]
    events: list[dict[str, Any]] = []
    for i in range(1, len(bars) - 1):
        trace = ecrs_v1_gate_trace_cached_from_state(
            state,
            i,
            symbol=symbol,
            timeframe=timeframe,
            news_calendar=calendar,
            allow_formula_generalization=allow_formula_generalization,
        )
        if not trace.final or trace.direction is None:
            continue
        event = {
            "namespace": "D7_ECRS_V1_EXACT",
            "symbol": symbol,
            "timeframe": timeframe,
            "signal_time_utc": frozen.utc_key(bars[i].time_utc),
            "entry_time_utc": frozen.utc_key(bars[i + 1].time_utc),
            "direction": trace.direction,
        }
        event["event_key"] = "|".join(
            str(value) for value in frozen.canonical_key(event, frozen.ECRS_IDENTITY_FIELDS)
        )
        events.append(event)
    allowed = set(frozen.ECRS_IDENTITY_FIELDS) | {"namespace", "event_key"}
    frozen._ensure_unique(
        events,
        frozen.ECRS_IDENTITY_FIELDS,
        "ECRS",
        allowed_fields=allowed,
    )
    return events


def _exact_keys(value: Mapping[str, Any], expected: set[str], name: str) -> None:
    if set(value) != expected:
        raise frozen.IdentityContractError(f"{name} requires exact keys")


def verify_lock(path: Path = LOCK_PATH) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    _exact_keys(
        document,
        {
            "schema_version", "campaign", "generation", "phase", "status", "authority",
            "frozen_at_utc", "owner_scope", "bindings", "test_gate", "prohibitions",
        },
        "ECRS cache lock",
    )
    if (
        document["schema_version"] != LOCK_SCHEMA
        or document["campaign"] != "PRO_TRADER_REPLACEMENT"
        or document["generation"] != "T2"
        or document["phase"] != "P3_OUTCOME_BLIND_DEDUP"
        or document["status"] != "FROZEN_CACHE_PARITY_ONLY_NO_SOURCE_RUN"
        or document["authority"] != "ENGINEERING_CACHE_SUCCESSOR_ONLY"
        or document["owner_scope"] != "XAU_FOREX_ONLY_BTC_NOT_GATING"
    ):
        raise frozen.IdentityContractError("ECRS cache lock authority/scope mismatch")
    frozen_at = datetime.fromisoformat(str(document["frozen_at_utc"]).replace("Z", "+00:00"))
    if frozen_at.tzinfo is None or frozen_at.astimezone(timezone.utc) > datetime.now(timezone.utc):
        raise frozen.IdentityContractError("ECRS cache lock timestamp is invalid")
    if document["test_gate"] != {
        "command": 'python -m pytest -q "03. EA Developer/EA_VolmanCausalGrammar"',
        "required_passed": 78,
        "required_failed": 0,
        "old_vs_new_trace_parity": True,
        "old_vs_new_event_parity": True,
        "real_source_rows_read": 0,
    }:
        raise frozen.IdentityContractError("ECRS cache test gate mismatch")
    required_prohibitions = {
        "NO_REAL_SOURCE_PREFIX_OR_FULL_REPLAY",
        "NO_EDIT_TO_FROZEN_MIRROR_RUNNER_GRAMMAR_OR_CONTRACT",
        "NO_GATE_THRESHOLD_KEY_SOURCE_SCHEDULE_OR_COMPARISON_CHANGE",
        "NO_OUTCOMES_OPTIMIZATION_EA_BUILD_MT5_OR_GIT",
        "NO_CLAIM_PACKET_OR_FULL_REPLAY_AUTHORITY",
    }
    if not isinstance(document["prohibitions"], list) or set(document["prohibitions"]) != required_prohibitions:
        raise frozen.IdentityContractError("ECRS cache prohibitions mismatch")
    verified: dict[str, str] = {}
    for name, binding in document["bindings"].items():
        _exact_keys(binding, {"path", "sha256", "role"}, f"binding {name}")
        relative = binding["path"]
        expected = binding["sha256"]
        if (
            not isinstance(relative, str)
            or re.fullmatch(r"[0-9A-F]{64}", str(expected)) is None
            or not isinstance(binding["role"], str)
            or not binding["role"]
        ):
            raise frozen.IdentityContractError(f"invalid ECRS cache binding: {name}")
        candidate = (REPO_ROOT / relative).resolve()
        try:
            candidate.relative_to(REPO_ROOT)
        except ValueError as exc:
            raise frozen.IdentityContractError(f"binding escapes repository: {name}") from exc
        actual = frozen.sha256_file(candidate)
        if actual != expected:
            raise frozen.IdentityContractError(f"ECRS cache binding SHA mismatch: {name}")
        verified[name] = actual
    return {"path": str(path), "sha256": frozen.sha256_file(path), "verified": verified}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true", required=True)
    args = parser.parse_args()
    if not args.verify_only:
        raise SystemExit("cache successor supports verify-only; no source execution")
    lock = verify_lock()
    print(json.dumps({
        "status": "PASS_CACHE_SUCCESSOR_VERIFY_ONLY",
        "authority": "ENGINEERING_CACHE_SUCCESSOR_ONLY_NO_SOURCE_RUN",
        "lock_sha256": lock["sha256"],
        "verified_bindings": sorted(lock["verified"]),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
