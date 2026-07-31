"""Outcome-blind T2/P3 V2 de-duplication mirrors.

The module implements only identity mirrors from the frozen V2 contract.  It
does not read market datasets, MT5 artifacts, reports, charts, registry
outcomes, or PnL.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
import csv
from datetime import datetime, time, timedelta, timezone
from hashlib import sha256
import importlib
import json
from math import isfinite
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping, Sequence


Side = Literal["LONG", "SHORT"]

CONTRACT_PATH = (
    "04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_P3_DEDUP_CONTRACT_V2.json"
)
CONTRACT_SHA256 = "30DD1EBC7DFD722A5F6C2765E1577845FB012983EB943E5C0E4A6CAD5B6C0290"
P2_PRODUCER_SPEC_SHA256 = "CB1DDA2B678D2F450BB2DDE05327D2734E2A430BBBC4809BB08C71110FA0BA7D"
BOUND_ECRS_NEWS_SOURCE = "bound_v2_forexfactory_eurusd_high_impact"
BOUND_ECRS_NEWS_COVERAGE_START_UTC = datetime(2019, 1, 1, tzinfo=timezone.utc)
BOUND_ECRS_NEWS_COVERAGE_END_UTC = datetime(2022, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
BOUND_ECRS_NEWS_CSV_SHA256 = "80B9DE46517B42F8B1D9A3ACCEFA6CC6D3DCB4DD06CAE357F16DE46228C64307"
BOUND_ECRS_NEWS_MANIFEST_SHA256 = "79C40AE0C7DFF7CF44539D00FD108E6D038648694EABD7AA44E234ACC00EF5B1"

ECRS_ALLOWED_BAR_FIELDS = frozenset(
    {"time_utc", "open", "high", "low", "close", "tick_volume", "spread"}
)
ECRS_IDENTITY_FIELDS = (
    "symbol",
    "timeframe",
    "signal_time_utc",
    "entry_time_utc",
    "direction",
)
NORMALIZED_OVERLAP_FIELDS = (
    "symbol",
    "timeframe",
    "direction",
    "decision_time_utc",
    "barrier_side",
    "barrier_price_in_symbol_ticks",
)
SCC_CONTROL_FIELDS = (
    "symbol",
    "timeframe",
    "pivot_side",
    "pivot_index",
    "pivot_confirm_time_utc",
    "break_time_utc",
    "direction",
)
SCC_CHALLENGER_FIELDS = SCC_CONTROL_FIELDS + (
    "hold_time_utc",
    "retest_time_utc",
    "passage_lag",
)
SCC_ALLOWED_FIELDS = frozenset(
    set(SCC_CHALLENGER_FIELDS) | {"pivot_price", "tick_size"}
)
FULL_LEDGER_MANIFEST_FIELDS = frozenset(
    {
        "source",
        "producer",
        "population_kind",
        "complete_population",
        "sampled_casebook",
        "contract_sha256",
        "record_count",
        "news_calendar_source",
        "fatal_gate_kind",
    }
)
FATAL_GATE_KINDS = frozenset({"NONE", "D7_ECRS_PRIMARY"})
D7_FATAL_POPULATION_KINDS = frozenset(
    {
        "D7",
        "ECRS",
        "D7_ECRS",
        "D7_ECRS_V1_EXACT",
        "D7_ECRS_V1",
        "ECRS_V1_EXACT",
    }
)

OUTCOME_FIELD_TOKENS = (
    "pnl",
    "profit",
    "loss",
    "win_rate",
    "winrate",
    "pf",
    "expectancy",
    "drawdown",
    "mfe",
    "mae",
    "excursion",
    "return",
    "r_multiple",
    "payoff",
    "balance",
    "equity",
    "outcome",
    "trade_result",
    "target_result",
    "stop_result",
)


class IdentityContractError(ValueError):
    """Raised when an outcome-blind identity contract is violated."""


@dataclass(frozen=True)
class EcrsBar:
    time_utc: datetime
    open: float
    high: float
    low: float
    close: float
    tick_volume: float
    spread: float


@dataclass(frozen=True)
class NewsCalendar:
    event_times_utc: tuple[datetime, ...]
    source: str
    coverage_start_utc: datetime
    coverage_end_utc: datetime
    csv_sha256: str | None = None
    manifest_sha256: str | None = None
    synthetic_only: bool = False


@dataclass(frozen=True)
class EcrsGateTrace:
    signal_index: int
    G1: bool
    G2: bool
    G3: bool
    G4: bool
    G5: bool
    G6: bool
    G7: bool
    G8: bool
    direction: Side | None

    @property
    def final(self) -> bool:
        return all((self.G1, self.G2, self.G3, self.G4, self.G5, self.G6, self.G7, self.G8))


@dataclass(frozen=True)
class ComparisonResult:
    left_count: int
    right_count: int
    intersection_count: int
    union_count: int
    jaccard: float
    intersection_keys: tuple[tuple[Any, ...], ...]


def sha256_file(path: str | Path) -> str:
    h = sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def verify_sha256(path: str | Path, expected_sha256: str) -> str:
    actual = sha256_file(path)
    if actual != expected_sha256.upper():
        raise IdentityContractError(
            f"SHA256 mismatch for {path}: expected={expected_sha256.upper()} actual={actual}"
        )
    return actual


def verify_contract_file(path: str | Path = CONTRACT_PATH) -> str:
    return verify_sha256(path, CONTRACT_SHA256)


def load_contract(path: str | Path = CONTRACT_PATH) -> dict[str, Any]:
    verify_contract_file(path)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def verify_contract_bindings(
    contract: Mapping[str, Any],
    *,
    root: str | Path = ".",
    binding_names: Iterable[str] | None = None,
) -> dict[str, str]:
    root_path = Path(root)
    bindings = contract.get("bindings", {})
    names = list(binding_names) if binding_names is not None else list(bindings)
    verified: dict[str, str] = {}
    for name in names:
        binding = bindings[name]
        path = root_path / binding["path"]
        verified[name] = verify_sha256(path, binding["sha256"])
    return verified


def load_bound_news_calendar(
    contract: Mapping[str, Any] | None = None,
    *,
    root: str | Path = ".",
) -> NewsCalendar:
    contract = load_contract() if contract is None else contract
    root_path = Path(root)
    csv_binding = contract["bindings"]["ecrs_news_csv"]
    manifest_binding = contract["bindings"]["ecrs_news_manifest"]
    csv_path = root_path / csv_binding["path"]
    manifest_path = root_path / manifest_binding["path"]
    csv_sha = verify_sha256(csv_path, csv_binding["sha256"])
    manifest_sha = verify_sha256(manifest_path, manifest_binding["sha256"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("symbol_scope") != "EURUSD":
        raise IdentityContractError("bound news manifest is not EURUSD-scoped")
    coverage = manifest.get("local_event_date_coverage", {})
    if coverage.get("from") != "2019-01-01" or coverage.get("to") != "2022-12-31":
        raise IdentityContractError("bound news manifest coverage is not 2019-2022")
    if manifest.get("normalized_csv", {}).get("sha256") != csv_sha:
        raise IdentityContractError("bound news manifest normalized CSV SHA does not match CSV")

    event_times: list[datetime] = []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if "event_time_utc" not in (reader.fieldnames or []):
            raise IdentityContractError("bound news CSV missing event_time_utc")
        for row in reader:
            event_times.append(normalize_utc(row["event_time_utc"]))
    if not event_times:
        raise IdentityContractError("bound news calendar is empty")
    return NewsCalendar(
        event_times_utc=tuple(sorted(event_times)),
        source=BOUND_ECRS_NEWS_SOURCE,
        coverage_start_utc=BOUND_ECRS_NEWS_COVERAGE_START_UTC,
        coverage_end_utc=BOUND_ECRS_NEWS_COVERAGE_END_UTC,
        csv_sha256=csv_sha,
        manifest_sha256=manifest_sha,
        synthetic_only=False,
    )


def synthetic_news_calendar(
    event_times_utc: Sequence[datetime | str],
    *,
    coverage_start_utc: datetime | str = "2019-01-01T00:00:00Z",
    coverage_end_utc: datetime | str = "2022-12-31T23:59:59Z",
) -> NewsCalendar:
    return NewsCalendar(
        event_times_utc=tuple(sorted(normalize_utc(value) for value in event_times_utc)),
        source="synthetic_only",
        coverage_start_utc=normalize_utc(coverage_start_utc),
        coverage_end_utc=normalize_utc(coverage_end_utc),
        synthetic_only=True,
    )


def _field_names(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        return {str(k) for k in value}
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name for field in fields(value)}
    return set()


def reject_unknown_fields(value: Any, allowed: Iterable[str], schema_name: str) -> None:
    names = _field_names(value)
    unknown = sorted(names - set(allowed))
    if unknown:
        raise IdentityContractError(f"{schema_name} contains unknown field(s): {unknown}")


def reject_outcome_fields(value: Any, *, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            lowered = key_text.lower()
            if any(token in lowered for token in OUTCOME_FIELD_TOKENS):
                raise IdentityContractError(f"outcome field is forbidden: {path}.{key_text}")
            reject_outcome_fields(item, path=f"{path}.{key_text}")
        return
    if is_dataclass(value) and not isinstance(value, type):
        for field in fields(value):
            key_text = field.name
            lowered = key_text.lower()
            if any(token in lowered for token in OUTCOME_FIELD_TOKENS):
                raise IdentityContractError(f"outcome field is forbidden: {path}.{key_text}")
            reject_outcome_fields(getattr(value, key_text), path=f"{path}.{key_text}")
        return
    if isinstance(value, (list, tuple, set, frozenset)):
        for index, item in enumerate(value):
            reject_outcome_fields(item, path=f"{path}[{index}]")


def normalize_utc(value: datetime | str) -> datetime:
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        value = datetime.fromisoformat(text)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def utc_key(value: datetime | str) -> str:
    return normalize_utc(value).isoformat().replace("+00:00", "Z")


def price_to_ticks(price: float, tick_size: float) -> int:
    if tick_size <= 0 or not isfinite(tick_size) or not isfinite(price):
        raise IdentityContractError("invalid tick normalization input")
    return int(round(price / tick_size))


def canonical_key(record: Mapping[str, Any], fields_: Sequence[str]) -> tuple[Any, ...]:
    reject_outcome_fields(record)
    missing = [field for field in fields_ if field not in record]
    if missing:
        raise IdentityContractError(f"identity missing required fields: {missing}")
    values: list[Any] = []
    for field in fields_:
        value = record[field]
        if field.endswith("_time_utc"):
            values.append(utc_key(value))
        else:
            values.append(value)
    return tuple(values)


def _ensure_unique(
    records: Sequence[Mapping[str, Any]],
    fields_: Sequence[str],
    side: str,
    *,
    allowed_fields: Iterable[str] | None = None,
) -> set[tuple[Any, ...]]:
    keys: list[tuple[Any, ...]] = []
    for record in records:
        if allowed_fields is not None:
            reject_unknown_fields(record, allowed_fields, f"{side} identity")
        keys.append(canonical_key(record, fields_))
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    if duplicates:
        raise IdentityContractError(f"duplicate {side} identity key(s): {duplicates}")
    return set(keys)


def compare_identities(
    left: Sequence[Mapping[str, Any]],
    right: Sequence[Mapping[str, Any]],
    *,
    key_fields: Sequence[str],
    allowed_fields: Iterable[str] | None = None,
) -> ComparisonResult:
    left_keys = _ensure_unique(left, key_fields, "left", allowed_fields=allowed_fields)
    right_keys = _ensure_unique(right, key_fields, "right", allowed_fields=allowed_fields)
    if not left_keys and not right_keys:
        raise IdentityContractError("empty/empty comparison is INVALID")
    intersection = left_keys & right_keys
    union = left_keys | right_keys
    return ComparisonResult(
        left_count=len(left_keys),
        right_count=len(right_keys),
        intersection_count=len(intersection),
        union_count=len(union),
        jaccard=len(intersection) / len(union),
        intersection_keys=tuple(sorted(intersection)),
    )


def assert_full_ledger_manifest(manifest: Mapping[str, Any], expected_count: int | None = None) -> None:
    reject_outcome_fields(manifest)
    reject_unknown_fields(manifest, FULL_LEDGER_MANIFEST_FIELDS, "ledger manifest")
    actual_keys = set(manifest)
    if actual_keys != FULL_LEDGER_MANIFEST_FIELDS:
        missing = sorted(FULL_LEDGER_MANIFEST_FIELDS - actual_keys)
        extra = sorted(actual_keys - FULL_LEDGER_MANIFEST_FIELDS)
        raise IdentityContractError(f"ledger manifest exact fields required missing={missing} extra={extra}")
    for key in ("source", "producer", "population_kind", "news_calendar_source", "fatal_gate_kind"):
        if not isinstance(manifest[key], str) or not manifest[key]:
            raise IdentityContractError(f"ledger manifest {key} must be a non-empty string")
    if manifest.get("complete_population") is not True:
        raise IdentityContractError("full-ledger manifest must set complete_population=true")
    if manifest.get("sampled_casebook") is not False:
        raise IdentityContractError("sampled_casebook must be false for Jaccard")
    descriptor = " ".join(str(manifest.get(k, "")) for k in ("source", "producer", "population_kind")).lower()
    if "casebook" in descriptor or "sample" in descriptor:
        raise IdentityContractError("sampled/casebook ledger descriptors are forbidden")
    if manifest.get("contract_sha256") != CONTRACT_SHA256:
        raise IdentityContractError("ledger manifest contract SHA does not match V2")
    if type(manifest.get("record_count")) is not int or manifest["record_count"] < 0:
        raise IdentityContractError("ledger manifest record_count must be a non-negative integer")
    if manifest["fatal_gate_kind"] not in FATAL_GATE_KINDS:
        raise IdentityContractError("ledger manifest fatal_gate_kind is not recognized")
    population_kind_upper = manifest["population_kind"].upper()
    is_d7_population = population_kind_upper in D7_FATAL_POPULATION_KINDS
    if is_d7_population and manifest["fatal_gate_kind"] != "D7_ECRS_PRIMARY":
        raise IdentityContractError("D7/ECRS ledger manifest requires fatal_gate_kind=D7_ECRS_PRIMARY")
    if manifest["fatal_gate_kind"] == "D7_ECRS_PRIMARY":
        if not is_d7_population:
            raise IdentityContractError("D7_ECRS_PRIMARY fatal gate requires a D7/ECRS population_kind")
        if manifest["news_calendar_source"] != "bound_v2_forexfactory_eurusd_high_impact":
            raise IdentityContractError("synthetic or unbound news calendar is forbidden for full-ledger D7")
    elif manifest["news_calendar_source"] not in {"not_applicable", "bound_v2_forexfactory_eurusd_high_impact"}:
        raise IdentityContractError("non-D7 ledger manifest news_calendar_source must be not_applicable or bound")
    if expected_count is not None and manifest["record_count"] != expected_count:
        raise IdentityContractError("ledger manifest record_count does not match ledger")


def compare_full_ledgers(
    left: Sequence[Mapping[str, Any]],
    right: Sequence[Mapping[str, Any]],
    *,
    key_fields: Sequence[str],
    left_manifest: Mapping[str, Any],
    right_manifest: Mapping[str, Any],
    allowed_fields: Iterable[str] | None = None,
) -> ComparisonResult:
    assert_full_ledger_manifest(left_manifest, len(left))
    assert_full_ledger_manifest(right_manifest, len(right))
    return compare_identities(left, right, key_fields=key_fields, allowed_fields=allowed_fields)


def _true_ranges(bars: Sequence[EcrsBar]) -> list[float]:
    out: list[float] = []
    for i, bar in enumerate(bars):
        if i == 0:
            out.append(bar.high - bar.low)
        else:
            prev_close = bars[i - 1].close
            out.append(max(bar.high - bar.low, abs(bar.high - prev_close), abs(bar.low - prev_close)))
    return out


def _rolling_mean(values: Sequence[float | None], period: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    for i in range(period - 1, len(values)):
        window = values[i - period + 1 : i + 1]
        if all(v is not None and isfinite(v) for v in window):
            out[i] = sum(float(v) for v in window) / period
    return out


def _ema(values: Sequence[float], period: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if not values:
        return out
    alpha = 2.0 / (period + 1.0)
    current = float(values[0])
    out[0] = current
    for i in range(1, len(values)):
        current = alpha * float(values[i]) + (1.0 - alpha) * current
        out[i] = current
    return out


def _efficiency_ratio(closes: Sequence[float], period: int = 10) -> list[float | None]:
    out: list[float | None] = [None] * len(closes)
    for i in range(period, len(closes)):
        denom = sum(abs(closes[j] - closes[j - 1]) for j in range(i - period + 1, i + 1))
        out[i] = None if denom <= 0 else abs(closes[i] - closes[i - period]) / denom
    return out


def ecrs_er_cross(er_previous: float | None, er_current: float | None) -> bool:
    return er_previous is not None and er_current is not None and er_previous < 0.28 and er_current >= 0.38


def _session_ok(entry_time: datetime) -> bool:
    t = normalize_utc(entry_time).time()
    return time(7, 0) <= t < time(16, 30)


def _require_news_calendar(
    calendar: Any,
    *,
    allow_synthetic_calendar: bool,
) -> NewsCalendar:
    if not isinstance(calendar, NewsCalendar):
        raise IdentityContractError("ECRS exact mirror requires a NewsCalendar object")
    if calendar.synthetic_only and not allow_synthetic_calendar:
        raise IdentityContractError("synthetic news calendar is forbidden for primary ECRS execution")
    if not calendar.synthetic_only:
        if (
            calendar.source != BOUND_ECRS_NEWS_SOURCE
            or calendar.coverage_start_utc != BOUND_ECRS_NEWS_COVERAGE_START_UTC
            or calendar.coverage_end_utc != BOUND_ECRS_NEWS_COVERAGE_END_UTC
            or calendar.csv_sha256 != BOUND_ECRS_NEWS_CSV_SHA256
            or calendar.manifest_sha256 != BOUND_ECRS_NEWS_MANIFEST_SHA256
            or not calendar.event_times_utc
        ):
            raise IdentityContractError("bound news calendar is incomplete for ECRS V2")
    return calendar


def _news_pass(entry_time: datetime, calendar: NewsCalendar) -> bool:
    entry = normalize_utc(entry_time)
    for event_time in calendar.event_times_utc:
        if abs(normalize_utc(event_time) - entry) <= timedelta(minutes=45):
            return False
    return True


def _scope_ok(symbol: str, timeframe: str, entry_time: datetime, *, allow_formula_generalization: bool) -> bool:
    if timeframe != "M5":
        return False
    if symbol != "EURUSD" and not allow_formula_generalization:
        return False
    if symbol == "EURUSD":
        entry = normalize_utc(entry_time)
        return datetime(2019, 1, 1, tzinfo=timezone.utc) <= entry <= datetime(
            2022, 12, 31, 23, 59, 59, tzinfo=timezone.utc
        )
    return allow_formula_generalization


def _as_ecrs_bar(row: EcrsBar | Mapping[str, Any]) -> EcrsBar:
    if isinstance(row, EcrsBar):
        reject_outcome_fields(row)
        return row
    reject_outcome_fields(row)
    reject_unknown_fields(row, ECRS_ALLOWED_BAR_FIELDS, "ECRS bar")
    return EcrsBar(
        time_utc=normalize_utc(row["time_utc"]),
        open=float(row["open"]),
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
        tick_volume=float(row["tick_volume"]),
        spread=float(row["spread"]),
    )


def _ecrs_state(rows: Sequence[EcrsBar | Mapping[str, Any]]) -> dict[str, Any]:
    bars = [_as_ecrs_bar(row) for row in rows]
    closes = [bar.close for bar in bars]
    return {
        "bars": bars,
        "closes": closes,
        "highs": [bar.high for bar in bars],
        "lows": [bar.low for bar in bars],
        "volumes": [bar.tick_volume for bar in bars],
        "atr14": _rolling_mean(_true_ranges(bars), 14),
        "ema20": _ema(closes, 20),
        "er": _efficiency_ratio(closes, 10),
    }


def ecrs_v1_gate_trace(
    rows: Sequence[EcrsBar | Mapping[str, Any]],
    signal_index: int,
    *,
    symbol: str,
    news_calendar: NewsCalendar | None,
    timeframe: str = "M5",
    allow_formula_generalization: bool = False,
    allow_synthetic_calendar: bool = False,
) -> EcrsGateTrace:
    calendar = _require_news_calendar(news_calendar, allow_synthetic_calendar=allow_synthetic_calendar)
    state = _ecrs_state(rows)
    bars: list[EcrsBar] = state["bars"]
    if signal_index <= 0 or signal_index >= len(bars) - 1:
        return EcrsGateTrace(signal_index, False, False, False, False, False, False, False, False, None)

    closes: list[float] = state["closes"]
    highs: list[float] = state["highs"]
    lows: list[float] = state["lows"]
    volumes: list[float] = state["volumes"]
    atr14: list[float | None] = state["atr14"]
    atr_sma20 = _rolling_mean(atr14, 20)
    ema20: list[float | None] = state["ema20"]
    tv_sma20 = _rolling_mean(volumes, 20)
    er: list[float | None] = state["er"]
    i = signal_index

    g1 = ecrs_er_cross(er[i - 1], er[i])
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
    g5_long = ema_now is not None and ema_lag is not None and closes[i] > float(ema_now) and float(ema_now) > float(ema_lag)
    g5_short = ema_now is not None and ema_lag is not None and closes[i] < float(ema_now) and float(ema_now) < float(ema_lag)
    direction: Side | None = None
    if g3_long and g5_long:
        direction = "LONG"
    elif g3_short and g5_short:
        direction = "SHORT"
    entry = bars[i + 1]
    g6 = _session_ok(entry.time_utc)
    g7 = _news_pass(entry.time_utc, calendar)
    spread_pips = entry.spread / 10.0
    g8 = isfinite(spread_pips) and 0.0 < spread_pips <= 0.8
    if not _scope_ok(symbol, timeframe, entry.time_utc, allow_formula_generalization=allow_formula_generalization):
        g6 = False
    return EcrsGateTrace(i, g1, g2, g3, g4, bool(direction), g6, g7, g8, direction)


def emit_ecrs_v1_identities(
    rows: Sequence[EcrsBar | Mapping[str, Any]],
    *,
    symbol: str,
    news_calendar: NewsCalendar | None,
    timeframe: str = "M5",
    allow_formula_generalization: bool = False,
    allow_synthetic_calendar: bool = False,
) -> list[dict[str, Any]]:
    """Emit V2 ECRS v1 full-trigger identities from completed synthetic M5 bars."""
    calendar = _require_news_calendar(news_calendar, allow_synthetic_calendar=allow_synthetic_calendar)
    bars = [_as_ecrs_bar(row) for row in rows]
    events: list[dict[str, Any]] = []
    for i in range(1, len(bars) - 1):
        trace = ecrs_v1_gate_trace(
            bars,
            i,
            symbol=symbol,
            timeframe=timeframe,
            news_calendar=calendar,
            allow_formula_generalization=allow_formula_generalization,
            allow_synthetic_calendar=allow_synthetic_calendar,
        )
        if not trace.final or trace.direction is None:
            continue
        event = {
            "namespace": "D7_ECRS_V1_EXACT",
            "symbol": symbol,
            "timeframe": timeframe,
            "signal_time_utc": utc_key(bars[i].time_utc),
            "entry_time_utc": utc_key(bars[i + 1].time_utc),
            "direction": trace.direction,
        }
        event["event_key"] = "|".join(str(x) for x in canonical_key(event, ECRS_IDENTITY_FIELDS))
        events.append(event)
    allowed = set(ECRS_IDENTITY_FIELDS) | {"namespace", "event_key"}
    _ensure_unique(events, ECRS_IDENTITY_FIELDS, "ECRS", allowed_fields=allowed)
    return events


def scc_control_identity(record: Mapping[str, Any]) -> dict[str, Any]:
    reject_outcome_fields(record)
    reject_unknown_fields(record, SCC_ALLOWED_FIELDS, "SCC record")
    event = {
        "namespace": "D8_SCC_CONTROL_BREAK",
        "symbol": record["symbol"],
        "timeframe": record.get("timeframe", "M5"),
        "pivot_side": record["pivot_side"],
        "pivot_index": int(record["pivot_index"]),
        "pivot_confirm_time_utc": utc_key(record["pivot_confirm_time_utc"]),
        "break_time_utc": utc_key(record["break_time_utc"]),
        "direction": record["direction"],
        "decision_time_utc": utc_key(record["break_time_utc"]),
        "barrier_side": record["pivot_side"],
        "barrier_price_in_symbol_ticks": price_to_ticks(float(record["pivot_price"]), float(record["tick_size"])),
    }
    return event


def scc_challenger_identity(record: Mapping[str, Any]) -> dict[str, Any]:
    event = scc_control_identity(record)
    event["namespace"] = "D8_SCC_CHALLENGER_RETEST"
    event["hold_time_utc"] = utc_key(record["hold_time_utc"])
    event["retest_time_utc"] = utc_key(record["retest_time_utc"])
    event["passage_lag"] = int(record["passage_lag"])
    event["decision_time_utc"] = event["retest_time_utc"]
    return event


def emit_scc_control_identities(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    events = [scc_control_identity(record) for record in records]
    _ensure_unique(events, SCC_CONTROL_FIELDS, "SCC control", allowed_fields=set(events[0]) if events else None)
    return events


def emit_scc_challenger_identities(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    events = [scc_challenger_identity(record) for record in records]
    _ensure_unique(events, SCC_CHALLENGER_FIELDS, "SCC challenger", allowed_fields=set(events[0]) if events else None)
    return events


def _pbp_audit_boundary() -> tuple[type, str]:
    module = importlib.import_module("t2_grammar_reference")
    event_type = getattr(module, "PbpAuditEvent", None)
    producer_sha = getattr(module, "PRODUCER_SPEC_SHA256", None)
    if event_type is None or producer_sha is None:
        raise IdentityContractError("PbpAuditEvent boundary is unavailable")
    if producer_sha != P2_PRODUCER_SPEC_SHA256:
        raise IdentityContractError("PbpAuditEvent producer spec SHA mismatch")
    return event_type, producer_sha


def _normalize_barrier_side(side: Any) -> str:
    if side == "LONG":
        return "HIGH"
    if side == "SHORT":
        return "LOW"
    if side in {"HIGH", "LOW"}:
        return str(side)
    raise IdentityContractError(f"invalid barrier side: {side}")


def _require_pbp_provenance(audit: Any) -> None:
    base_fields = (
        "symbol",
        "timeframe",
        "side",
        "decision_index",
        "decision_utc",
        "trigger_index",
        "trigger_utc",
        "k_index",
        "barrier_side",
        "barrier_price",
        "barrier_price_ticks",
        "barrier_id",
        "lock_utc",
    )
    missing = [name for name in base_fields if getattr(audit, name) is None]
    if missing:
        raise IdentityContractError(f"PbpAuditEvent missing provenance field(s): {missing}")
    if audit.event_type == "PBP_BREAK_WINDOW":
        required = ("break_index", "break_utc")
    elif audit.event_type == "PBP_TOMBSTONE_CONTACT":
        required = ("contact_index", "contact_utc", "consumed_index", "consumed_utc")
    else:
        raise IdentityContractError(f"unknown PBP event type: {audit.event_type}")
    missing = [name for name in required if getattr(audit, name) is None]
    if missing:
        raise IdentityContractError(f"PbpAuditEvent missing {audit.event_type} field(s): {missing}")
    if audit.event_type == "PBP_BREAK_WINDOW" and (
        audit.decision_index != audit.break_index or utc_key(audit.decision_utc) != utc_key(audit.break_utc)
    ):
        raise IdentityContractError("PBP_BREAK_WINDOW decision must be the actual break")
    if audit.event_type == "PBP_TOMBSTONE_CONTACT" and (
        audit.decision_index != audit.contact_index or utc_key(audit.decision_utc) != utc_key(audit.contact_utc)
    ):
        raise IdentityContractError("PBP_TOMBSTONE_CONTACT decision must be the actual contact")


def emit_t2_pbp_like_identities(
    audit_events: Sequence[Any],
) -> list[dict[str, Any]]:
    event_type, producer_sha = _pbp_audit_boundary()
    events: list[dict[str, Any]] = []
    for audit in audit_events:
        reject_outcome_fields(audit)
        if not isinstance(audit, event_type):
            raise IdentityContractError("D8 requires exact PbpAuditEvent instances")
        if audit.producer_spec_sha256 != producer_sha:
            raise IdentityContractError("PbpAuditEvent producer spec SHA mismatch")
        _require_pbp_provenance(audit)
        event = {
            "namespace": f"D8_T2_{audit.event_type}",
            "subset": audit.event_type,
            "economic_authority": "NONE",
            "producer_spec_sha256": audit.producer_spec_sha256,
            "source_barrier_id": audit.barrier_id,
            "lock_time_utc": utc_key(audit.lock_utc),
            "symbol": audit.symbol,
            "timeframe": audit.timeframe,
            "direction": audit.side,
            "decision_time_utc": utc_key(audit.decision_utc),
            "barrier_side": _normalize_barrier_side(audit.barrier_side),
            "barrier_price_in_symbol_ticks": int(audit.barrier_price_ticks),
        }
        if audit.event_type == "PBP_BREAK_WINDOW":
            event["break_time_utc"] = utc_key(audit.break_utc)
        else:
            event["contact_time_utc"] = utc_key(audit.contact_utc)
            event["consumed_time_utc"] = utc_key(audit.consumed_utc)
        event["event_key"] = "|".join(str(x) for x in canonical_key(event, NORMALIZED_OVERLAP_FIELDS))
        events.append(event)
    allowed = set(NORMALIZED_OVERLAP_FIELDS) | {
        "namespace",
        "subset",
        "economic_authority",
        "producer_spec_sha256",
        "source_barrier_id",
        "lock_time_utc",
        "break_time_utc",
        "contact_time_utc",
        "consumed_time_utc",
        "event_key",
    }
    _ensure_unique(events, ("namespace",) + NORMALIZED_OVERLAP_FIELDS, "T2 PBP", allowed_fields=allowed)
    return events
