"""Outcome-blind T2/P3 V2 de-duplication mirrors.

The module implements only identity mirrors from the frozen V2 contract.  It
does not read market datasets, MT5 artifacts, reports, charts, registry
outcomes, or PnL.
"""

from __future__ import annotations

from bisect import bisect_left
from collections import Counter
from dataclasses import dataclass, fields, is_dataclass, replace
import csv
from datetime import datetime, time, timedelta, timezone
from hashlib import sha256
import importlib
import json
from math import isfinite
from pathlib import Path
import re
from typing import Any, Iterable, Literal, Mapping, Sequence


Side = Literal["LONG", "SHORT"]

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = (
    REPO_ROOT
    / "04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_P3_DEDUP_CONTRACT_V2.json"
)
CONTRACT_SHA256 = "30DD1EBC7DFD722A5F6C2765E1577845FB012983EB943E5C0E4A6CAD5B6C0290"
P2_PRODUCER_SPEC_SHA256 = "CB1DDA2B678D2F450BB2DDE05327D2734E2A430BBBC4809BB08C71110FA0BA7D"
BOUND_ECRS_NEWS_SOURCE = "bound_v2_forexfactory_eurusd_high_impact"
BOUND_ECRS_NEWS_COVERAGE_START_UTC = datetime(2019, 1, 1, tzinfo=timezone.utc)
BOUND_ECRS_NEWS_COVERAGE_END_UTC = datetime(2022, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
BOUND_ECRS_NEWS_CSV_SHA256 = "80B9DE46517B42F8B1D9A3ACCEFA6CC6D3DCB4DD06CAE357F16DE46228C64307"
BOUND_ECRS_NEWS_MANIFEST_SHA256 = "79C40AE0C7DFF7CF44539D00FD108E6D038648694EABD7AA44E234ACC00EF5B1"
BOUND_D7_STAGE0_BARS_SHA256 = "A2DDF0D423D188B7BA708ECF4386180853867982123C38418D43A2CE89053532"
BOUND_D7_STAGE0_RECORD_COUNT = 596141
BOUND_D7_STAGE0_FIRST_UTC = "2015-01-02T07:00:00Z"
BOUND_D7_STAGE0_LAST_UTC = "2022-12-30T21:55:00Z"

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
        "ledger_sha256",
        "source_sha256",
        "producer_sha256",
        "source_record_count",
        "source_first_utc",
        "source_last_utc",
        "identity_first_utc",
        "identity_last_utc",
        "generation_mode",
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
class SccPathBar:
    time_utc: datetime
    high: float
    low: float
    close: float
    complete: bool = True


@dataclass(frozen=True)
class SccPathIndex:
    bars: tuple[SccPathBar, ...]
    by_time: Mapping[datetime, SccPathBar]
    position_by_time: Mapping[datetime, int]
    last_pivot_high_index: tuple[int | None, ...]
    last_pivot_low_index: tuple[int | None, ...]


@dataclass(frozen=True)
class NewsCalendar:
    event_times_utc: tuple[datetime, ...]
    source: str
    coverage_start_utc: datetime
    coverage_end_utc: datetime
    csv_sha256: str | None = None
    manifest_sha256: str | None = None
    synthetic_only: bool = False
    csv_path: str | None = None
    manifest_path: str | None = None


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
    left_only_keys: tuple[tuple[Any, ...], ...]
    right_only_keys: tuple[tuple[Any, ...], ...]
    unmatched_reason_codes: tuple[tuple[str, tuple[Any, ...], str], ...]


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


def verify_execution_bindings(binding_names: Iterable[str]) -> dict[str, str]:
    contract = load_contract()
    return verify_contract_bindings(
        contract,
        root=REPO_ROOT,
        binding_names=tuple(binding_names),
    )


def load_bound_news_calendar(
    contract: Mapping[str, Any] | None = None,
    *,
    root: str | Path = REPO_ROOT,
) -> NewsCalendar:
    verified_contract = load_contract()
    if contract is not None and contract != verified_contract:
        raise IdentityContractError("caller contract does not match the frozen P3 V2 contract")
    contract = verified_contract
    verify_contract_bindings(
        contract,
        root=root,
        binding_names=(
            "p2_formal_spec",
            "ecrs_v1_reference",
            "indicator_reference",
            "ecrs_news_csv",
            "ecrs_news_manifest",
        ),
    )
    root_path = Path(root)
    csv_binding = contract["bindings"]["ecrs_news_csv"]
    manifest_binding = contract["bindings"]["ecrs_news_manifest"]
    csv_path = root_path / csv_binding["path"]
    manifest_path = root_path / manifest_binding["path"]
    csv_sha, manifest_sha, event_times = _read_bound_news_files(
        csv_path,
        manifest_path,
        expected_csv_sha=csv_binding["sha256"],
        expected_manifest_sha=manifest_binding["sha256"],
    )
    return NewsCalendar(
        event_times_utc=event_times,
        source=BOUND_ECRS_NEWS_SOURCE,
        coverage_start_utc=BOUND_ECRS_NEWS_COVERAGE_START_UTC,
        coverage_end_utc=BOUND_ECRS_NEWS_COVERAGE_END_UTC,
        csv_sha256=csv_sha,
        manifest_sha256=manifest_sha,
        synthetic_only=False,
        csv_path=str(csv_path.resolve()),
        manifest_path=str(manifest_path.resolve()),
    )


def _read_bound_news_files(
    csv_path: str | Path,
    manifest_path: str | Path,
    *,
    expected_csv_sha: str,
    expected_manifest_sha: str,
) -> tuple[str, str, tuple[datetime, ...]]:
    csv_path = Path(csv_path)
    manifest_path = Path(manifest_path)
    csv_sha = verify_sha256(csv_path, expected_csv_sha)
    manifest_sha = verify_sha256(manifest_path, expected_manifest_sha)
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
    normalized = tuple(sorted(event_times))
    if any(
        value < BOUND_ECRS_NEWS_COVERAGE_START_UTC
        or value > BOUND_ECRS_NEWS_COVERAGE_END_UTC
        for value in normalized
    ):
        raise IdentityContractError("bound news CSV contains an event outside 2019-2022")
    return csv_sha, manifest_sha, normalized


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


def identity_ledger_sha256(records: Sequence[Mapping[str, Any]]) -> str:
    payload = "".join(
        json.dumps(
            _canonical_json_value(record),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        + "\n"
        for record in records
    )
    return sha256(payload.encode("utf-8")).hexdigest().upper()


def identity_time_range(
    records: Sequence[Mapping[str, Any]],
) -> tuple[str | None, str | None]:
    values: list[str] = []
    priority = (
        "entry_time_utc",
        "decision_time_utc",
        "retest_time_utc",
        "break_time_utc",
        "signal_time_utc",
    )
    for record in records:
        field = next((name for name in priority if name in record), None)
        if field is None:
            raise IdentityContractError("identity record has no canonical decision timestamp")
        values.append(utc_key(record[field]))
    return (min(values), max(values)) if values else (None, None)


def _canonical_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _canonical_json_value(item) for key, item in value.items()}
    if isinstance(value, datetime):
        return utc_key(value)
    if isinstance(value, (list, tuple)):
        return [_canonical_json_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted(_canonical_json_value(item) for item in value)
    if isinstance(value, float) and not isfinite(value):
        raise IdentityContractError("identity ledger contains a nonfinite float")
    return value


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
    duplicates = sorted(key for key, count in Counter(keys).items() if count > 1)
    if duplicates:
        raise IdentityContractError(f"duplicate {side} identity key(s): {duplicates}")
    return set(keys)


def compare_identities(
    left: Sequence[Mapping[str, Any]],
    right: Sequence[Mapping[str, Any]],
    *,
    key_fields: Sequence[str],
    allowed_fields: Iterable[str] | None = None,
    left_only_reason_code: str = "LEFT_ONLY_CAUSAL_IDENTITY",
    right_only_reason_code: str = "RIGHT_ONLY_CAUSAL_IDENTITY",
) -> ComparisonResult:
    left_keys = _ensure_unique(left, key_fields, "left", allowed_fields=allowed_fields)
    right_keys = _ensure_unique(right, key_fields, "right", allowed_fields=allowed_fields)
    if not left_keys and not right_keys:
        raise IdentityContractError("empty/empty comparison is INVALID")
    intersection = left_keys & right_keys
    union = left_keys | right_keys
    left_only = left_keys - right_keys
    right_only = right_keys - left_keys
    unmatched = tuple(
        [("LEFT_ONLY", key, left_only_reason_code) for key in sorted(left_only)]
        + [("RIGHT_ONLY", key, right_only_reason_code) for key in sorted(right_only)]
    )
    return ComparisonResult(
        left_count=len(left_keys),
        right_count=len(right_keys),
        intersection_count=len(intersection),
        union_count=len(union),
        jaccard=len(intersection) / len(union),
        intersection_keys=tuple(sorted(intersection)),
        left_only_keys=tuple(sorted(left_only)),
        right_only_keys=tuple(sorted(right_only)),
        unmatched_reason_codes=unmatched,
    )


def assert_full_ledger_manifest(
    manifest: Mapping[str, Any],
    expected_count: int | None = None,
    *,
    records: Sequence[Mapping[str, Any]] | None = None,
) -> None:
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
    for key in ("ledger_sha256", "source_sha256", "producer_sha256"):
        if not isinstance(manifest[key], str) or not re.fullmatch(r"[0-9A-F]{64}", manifest[key]):
            raise IdentityContractError(f"ledger manifest {key} must be uppercase SHA256")
    if type(manifest["source_record_count"]) is not int or manifest["source_record_count"] < manifest["record_count"]:
        raise IdentityContractError("ledger manifest source_record_count is invalid")
    if manifest["generation_mode"] != "BOUND_FULL_REPLAY":
        raise IdentityContractError("full ledger requires generation_mode=BOUND_FULL_REPLAY")
    if manifest["source_record_count"] == 0:
        if manifest["source_first_utc"] is not None or manifest["source_last_utc"] is not None:
            raise IdentityContractError("empty source must have null source UTC bounds")
    else:
        source_first = utc_key(manifest["source_first_utc"])
        source_last = utc_key(manifest["source_last_utc"])
        if source_first > source_last:
            raise IdentityContractError("ledger manifest source UTC bounds are reversed")
    if records is not None:
        expected_count = len(records)
        if manifest["ledger_sha256"] != identity_ledger_sha256(records):
            raise IdentityContractError("ledger manifest content SHA does not match ledger")
        first, last = identity_time_range(records)
        if manifest["identity_first_utc"] != first or manifest["identity_last_utc"] != last:
            raise IdentityContractError("ledger manifest identity UTC range does not match ledger")
    elif manifest["record_count"] == 0:
        if manifest["identity_first_utc"] is not None or manifest["identity_last_utc"] is not None:
            raise IdentityContractError("empty ledger must have null identity UTC bounds")
    else:
        if not manifest["identity_first_utc"] or not manifest["identity_last_utc"]:
            raise IdentityContractError("nonempty ledger requires identity UTC bounds")
        if utc_key(manifest["identity_first_utc"]) > utc_key(manifest["identity_last_utc"]):
            raise IdentityContractError("ledger manifest identity UTC bounds are reversed")
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
    left_only_reason_code: str = "LEFT_ONLY_CAUSAL_IDENTITY",
    right_only_reason_code: str = "RIGHT_ONLY_CAUSAL_IDENTITY",
) -> ComparisonResult:
    verify_contract_file()
    assert_full_ledger_manifest(left_manifest, records=left)
    assert_full_ledger_manifest(right_manifest, records=right)
    return compare_identities(
        left,
        right,
        key_fields=key_fields,
        allowed_fields=allowed_fields,
        left_only_reason_code=left_only_reason_code,
        right_only_reason_code=right_only_reason_code,
    )


T2_D7_ALLOWED_FIELDS = frozenset(
    set(ECRS_IDENTITY_FIELDS)
    | {
        "namespace",
        "arms",
        "barrier_ids",
        "producer_spec_sha256",
        "event_key",
    }
)
ECRS_EVENT_ALLOWED_FIELDS = frozenset(
    set(ECRS_IDENTITY_FIELDS) | {"namespace", "event_key"}
)
T2_STRUCTURAL_ARMS = frozenset(
    {
        "A0_LOCKED_BARRIER_BREAK",
        "A1_PATTERN_BREAK",
        "A2_PATTERN_BREAK_COMBI",
        "A3_PULLBACK_REVERSAL",
    }
)


def compare_d7_primary_full_ledgers(
    left: Sequence[Mapping[str, Any]],
    right: Sequence[Mapping[str, Any]],
    *,
    left_manifest: Mapping[str, Any],
    right_manifest: Mapping[str, Any],
) -> ComparisonResult:
    """Compare exactly one complete T2 structural ledger with one ECRS ledger."""
    verify_execution_bindings(
        ("p2_formal_spec", "ecrs_v1_reference", "indicator_reference")
    )
    assert_full_ledger_manifest(left_manifest, records=left)
    assert_full_ledger_manifest(right_manifest, records=right)
    pairs = ((left, left_manifest), (right, right_manifest))
    ecrs_pairs = [pair for pair in pairs if pair[1]["fatal_gate_kind"] == "D7_ECRS_PRIMARY"]
    if len(ecrs_pairs) != 1:
        raise IdentityContractError("D7 primary comparison requires exactly one ECRS fatal-gate ledger")
    t2_pairs = [pair for pair in pairs if pair not in ecrs_pairs]
    if len(t2_pairs) != 1 or "T2" not in t2_pairs[0][1]["population_kind"].upper() or "STRUCTURAL" not in t2_pairs[0][1]["population_kind"].upper():
        raise IdentityContractError("D7 primary comparison requires one T2 structural population")
    t2_rows = t2_pairs[0][0]
    ecrs_rows = ecrs_pairs[0][0]
    t2_manifest = t2_pairs[0][1]
    ecrs_manifest = ecrs_pairs[0][1]
    for manifest in (t2_manifest, ecrs_manifest):
        if (
            manifest["source_sha256"] != BOUND_D7_STAGE0_BARS_SHA256
            or manifest["source_record_count"] != BOUND_D7_STAGE0_RECORD_COUNT
            or utc_key(manifest["source_first_utc"]) != BOUND_D7_STAGE0_FIRST_UTC
            or utc_key(manifest["source_last_utc"]) != BOUND_D7_STAGE0_LAST_UTC
        ):
            raise IdentityContractError("D7 primary ledger is not bound to the complete stage0 source")
    grammar_path = (
        REPO_ROOT
        / "03. EA Developer/EA_VolmanCausalGrammar/research/t2_grammar_reference.py"
    )
    if t2_manifest["producer_sha256"] != sha256_file(grammar_path):
        raise IdentityContractError("T2 D7 manifest producer SHA mismatch")
    if ecrs_manifest["producer_sha256"] != sha256_file(Path(__file__)):
        raise IdentityContractError("ECRS D7 manifest producer SHA mismatch")
    for row in t2_rows:
        reject_unknown_fields(row, T2_D7_ALLOWED_FIELDS, "T2 D7 structural identity")
        if row.get("namespace") != "T2_STRUCTURAL_A0_A3":
            raise IdentityContractError("T2 D7 namespace mismatch")
        if row.get("producer_spec_sha256") != P2_PRODUCER_SPEC_SHA256:
            raise IdentityContractError("T2 D7 producer spec SHA mismatch")
        _require_d7_primary_identity_scope(row)
        arms = row.get("arms")
        if (
            not isinstance(arms, (list, tuple))
            or not arms
            or list(arms) != sorted(set(arms))
            or any(arm not in T2_STRUCTURAL_ARMS for arm in arms)
        ):
            raise IdentityContractError("T2 D7 arms must be a sorted unique A0-A3 population")
        barrier_ids = row.get("barrier_ids")
        if (
            not isinstance(barrier_ids, (list, tuple))
            or list(barrier_ids) != sorted(set(barrier_ids))
            or any(not isinstance(value, str) or not value for value in barrier_ids)
        ):
            raise IdentityContractError("T2 D7 barrier_ids must be sorted unique strings")
        has_locked_barrier_arm = any(arm != "A3_PULLBACK_REVERSAL" for arm in arms)
        if has_locked_barrier_arm and not barrier_ids:
            raise IdentityContractError("T2 D7 locked-barrier arm is missing barrier provenance")
        if not has_locked_barrier_arm and barrier_ids:
            raise IdentityContractError("T2 D7 A3-only identity cannot claim a trigger barrier")
    for row in ecrs_rows:
        reject_unknown_fields(row, ECRS_EVENT_ALLOWED_FIELDS, "ECRS D7 identity")
        if row.get("namespace") != "D7_ECRS_V1_EXACT":
            raise IdentityContractError("ECRS D7 namespace mismatch")
        _require_d7_primary_identity_scope(row)
    result = compare_identities(
        left,
        right,
        key_fields=ECRS_IDENTITY_FIELDS,
        allowed_fields=T2_D7_ALLOWED_FIELDS | ECRS_EVENT_ALLOWED_FIELDS,
    )
    t2_by_key = {
        canonical_key(row, ECRS_IDENTITY_FIELDS): row
        for row in t2_rows
    }
    unmatched: list[tuple[str, tuple[Any, ...], str]] = []
    for side_name, keys in (
        ("LEFT_ONLY", result.left_only_keys),
        ("RIGHT_ONLY", result.right_only_keys),
    ):
        for key in keys:
            reason = (
                _t2_d7_causal_reason(t2_by_key[key])
                if key in t2_by_key
                else "ECRS_COMPRESSION_VOLUME_EMA_SESSION_ONLY"
            )
            unmatched.append((side_name, key, reason))
    return replace(result, unmatched_reason_codes=tuple(unmatched))


def _t2_d7_causal_reason(row: Mapping[str, Any]) -> str:
    arms = set(row["arms"])
    has_a3 = "A3_PULLBACK_REVERSAL" in arms
    has_locked_barrier = any(arm != "A3_PULLBACK_REVERSAL" for arm in arms)
    if has_a3 and has_locked_barrier:
        return "T2_LOCKED_BARRIER_AND_CORRECTION_PATH_ONLY"
    if has_locked_barrier:
        return "T2_LOCKED_BARRIER_CAUSAL_PATH_ONLY"
    return "T2_PRESSURE_CORRECTION_EVENT_ORDER_ONLY"


def _require_d7_primary_identity_scope(row: Mapping[str, Any]) -> None:
    if row.get("symbol") != "EURUSD" or row.get("timeframe") != "M5":
        raise IdentityContractError("D7 primary identity must be EURUSD/M5")
    signal = normalize_utc(row["signal_time_utc"])
    entry = normalize_utc(row["entry_time_utc"])
    if entry - signal != timedelta(minutes=5):
        raise IdentityContractError("D7 primary identity requires the immediate next M5 entry")
    if row.get("direction") not in {"LONG", "SHORT"}:
        raise IdentityContractError("D7 primary identity direction is invalid")
    if not BOUND_ECRS_NEWS_COVERAGE_START_UTC <= entry <= BOUND_ECRS_NEWS_COVERAGE_END_UTC:
        raise IdentityContractError("D7 primary identity is outside the frozen 2019-2022 window")
    expected_key = "|".join(str(value) for value in canonical_key(row, ECRS_IDENTITY_FIELDS))
    if row.get("event_key") != expected_key:
        raise IdentityContractError("D7 primary identity event_key mismatch")


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
    normalized_events = tuple(normalize_utc(value) for value in calendar.event_times_utc)
    if normalized_events != tuple(sorted(normalized_events)):
        raise IdentityContractError("NewsCalendar events must be sorted UTC timestamps")
    if calendar.synthetic_only and not allow_synthetic_calendar:
        raise IdentityContractError("synthetic news calendar is forbidden for primary ECRS execution")
    if calendar.synthetic_only:
        if (
            calendar.source != "synthetic_only"
            or calendar.csv_sha256 is not None
            or calendar.manifest_sha256 is not None
            or calendar.csv_path is not None
            or calendar.manifest_path is not None
        ):
            raise IdentityContractError("synthetic NewsCalendar cannot claim bound provenance")
        return calendar
    if (
        calendar.source != BOUND_ECRS_NEWS_SOURCE
        or normalize_utc(calendar.coverage_start_utc) != BOUND_ECRS_NEWS_COVERAGE_START_UTC
        or normalize_utc(calendar.coverage_end_utc) != BOUND_ECRS_NEWS_COVERAGE_END_UTC
        or calendar.csv_sha256 != BOUND_ECRS_NEWS_CSV_SHA256
        or calendar.manifest_sha256 != BOUND_ECRS_NEWS_MANIFEST_SHA256
        or not calendar.csv_path
        or not calendar.manifest_path
        or not calendar.event_times_utc
    ):
        raise IdentityContractError("bound news calendar is incomplete for ECRS V2")
    verify_contract_file()
    contract = load_contract()
    verify_contract_bindings(
        contract,
        root=REPO_ROOT,
        binding_names=("p2_formal_spec", "ecrs_v1_reference", "indicator_reference"),
    )
    csv_sha, manifest_sha, source_events = _read_bound_news_files(
        calendar.csv_path,
        calendar.manifest_path,
        expected_csv_sha=BOUND_ECRS_NEWS_CSV_SHA256,
        expected_manifest_sha=BOUND_ECRS_NEWS_MANIFEST_SHA256,
    )
    if csv_sha != calendar.csv_sha256 or manifest_sha != calendar.manifest_sha256:
        raise IdentityContractError("bound news calendar SHA provenance changed")
    if source_events != normalized_events:
        raise IdentityContractError("bound news calendar events do not match the verified CSV")
    return calendar


def _news_pass(entry_time: datetime, calendar: NewsCalendar) -> bool:
    entry = normalize_utc(entry_time)
    events = calendar.event_times_utc
    index = bisect_left(events, entry)
    window = timedelta(minutes=45)
    return not (
        (index < len(events) and abs(events[index] - entry) <= window)
        or (index > 0 and abs(entry - events[index - 1]) <= window)
    )


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
    return _ecrs_v1_gate_trace_from_state(
        state,
        signal_index,
        symbol=symbol,
        timeframe=timeframe,
        news_calendar=calendar,
        allow_formula_generalization=allow_formula_generalization,
    )


def _ecrs_v1_gate_trace_from_state(
    state: Mapping[str, Any],
    signal_index: int,
    *,
    symbol: str,
    timeframe: str,
    news_calendar: NewsCalendar,
    allow_formula_generalization: bool,
) -> EcrsGateTrace:
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
    g6 = (
        entry.time_utc - bars[i].time_utc == timedelta(minutes=5)
        and _session_ok(entry.time_utc)
    )
    g7 = _news_pass(entry.time_utc, news_calendar)
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
    state = _ecrs_state(rows)
    bars: list[EcrsBar] = state["bars"]
    events: list[dict[str, Any]] = []
    for i in range(1, len(bars) - 1):
        trace = _ecrs_v1_gate_trace_from_state(
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
    _validate_scc_record(record, challenger=False)
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
    _validate_scc_record(record, challenger=True)
    event = scc_control_identity(record)
    event["namespace"] = "D8_SCC_CHALLENGER_RETEST"
    event["hold_time_utc"] = utc_key(record["hold_time_utc"])
    event["retest_time_utc"] = utc_key(record["retest_time_utc"])
    event["passage_lag"] = int(record["passage_lag"])
    event["decision_time_utc"] = event["retest_time_utc"]
    return event


def _validate_scc_record(record: Mapping[str, Any], *, challenger: bool) -> None:
    required = set(SCC_CONTROL_FIELDS) | {"pivot_price", "tick_size"}
    if challenger:
        required |= {"hold_time_utc", "retest_time_utc", "passage_lag"}
    missing = sorted(required - set(record))
    if missing:
        raise IdentityContractError(f"SCC record missing required fields: {missing}")
    if record["symbol"] != "EURUSD" or record["timeframe"] != "M5":
        raise IdentityContractError("SCC primary mirror requires exact EURUSD/M5 scope")
    expected_direction = {"HIGH": "LONG", "LOW": "SHORT"}
    if record["pivot_side"] not in expected_direction:
        raise IdentityContractError("SCC pivot_side must be HIGH or LOW")
    if record["direction"] != expected_direction[record["pivot_side"]]:
        raise IdentityContractError("SCC pivot_side/direction relation is invalid")
    if type(record["pivot_index"]) is not int or record["pivot_index"] < 0:
        raise IdentityContractError("SCC pivot_index must be a non-negative integer")
    confirm = normalize_utc(record["pivot_confirm_time_utc"])
    break_time = normalize_utc(record["break_time_utc"])
    if not confirm < break_time:
        raise IdentityContractError("SCC requires pivot confirmation before break")
    if not challenger:
        return
    if type(record["passage_lag"]) is not int or not 1 <= record["passage_lag"] <= 12:
        raise IdentityContractError("SCC passage_lag must be an integer in 1..12")
    hold = normalize_utc(record["hold_time_utc"])
    retest = normalize_utc(record["retest_time_utc"])
    if not (break_time.date() == hold.date() == retest.date()):
        raise IdentityContractError("SCC BREAK/HOLD/RETEST must remain on one UTC date")
    if hold - break_time != timedelta(minutes=5):
        raise IdentityContractError("SCC HOLD must be the immediate next retained M5 bar")
    if retest - hold != timedelta(minutes=5 * record["passage_lag"]):
        raise IdentityContractError("SCC retest time does not match first-passage lag")


def emit_scc_control_identities(
    records: Sequence[Mapping[str, Any]],
    *,
    source_bars: Sequence[SccPathBar | Mapping[str, Any]],
) -> list[dict[str, Any]]:
    verify_execution_bindings(("scc_reference", "scc_probe_plan"))
    path_index = _scc_path_index(source_bars)
    _validate_scc_record_set(records)
    for record in records:
        _verify_scc_control_path(record, path_index)
    events = [scc_control_identity(record) for record in records]
    _ensure_unique(events, SCC_CONTROL_FIELDS, "SCC control", allowed_fields=set(events[0]) if events else None)
    return events


def emit_scc_challenger_identities(
    records: Sequence[Mapping[str, Any]],
    *,
    source_bars: Sequence[SccPathBar | Mapping[str, Any]],
) -> list[dict[str, Any]]:
    verify_execution_bindings(("scc_reference", "scc_probe_plan"))
    path_index = _scc_path_index(source_bars)
    _validate_scc_record_set(records)
    for record in records:
        _verify_scc_first_passage(record, path_index)
    events = [scc_challenger_identity(record) for record in records]
    _ensure_unique(events, SCC_CHALLENGER_FIELDS, "SCC challenger", allowed_fields=set(events[0]) if events else None)
    return events


def _scc_path_index(
    source_bars: Sequence[SccPathBar | Mapping[str, Any]],
) -> SccPathIndex:
    normalized_bars = tuple(bar for bar in _normalize_scc_path_bars(source_bars) if bar.complete)
    by_time = {bar.time_utc: bar for bar in normalized_bars}
    if len(by_time) != len(normalized_bars):
        raise IdentityContractError("SCC path replay contains duplicate timestamps")
    position_by_time = {bar.time_utc: index for index, bar in enumerate(normalized_bars)}
    n = len(normalized_bars)
    is_high = [False] * n
    is_low = [False] * n
    for pivot in range(2, n - 2):
        is_high[pivot] = normalized_bars[pivot].high > max(
            normalized_bars[pivot - 2].high,
            normalized_bars[pivot - 1].high,
            normalized_bars[pivot + 1].high,
            normalized_bars[pivot + 2].high,
        )
        is_low[pivot] = normalized_bars[pivot].low < min(
            normalized_bars[pivot - 2].low,
            normalized_bars[pivot - 1].low,
            normalized_bars[pivot + 1].low,
            normalized_bars[pivot + 2].low,
        )
    last_high: list[int | None] = []
    last_low: list[int | None] = []
    high_index: int | None = None
    low_index: int | None = None
    for scan in range(n):
        exposed = scan - 3
        if exposed >= 2:
            if is_high[exposed]:
                high_index = exposed
            if is_low[exposed]:
                low_index = exposed
        last_high.append(high_index)
        last_low.append(low_index)
    return SccPathIndex(
        normalized_bars,
        by_time,
        position_by_time,
        tuple(last_high),
        tuple(last_low),
    )


def _validate_scc_record_set(records: Sequence[Mapping[str, Any]]) -> None:
    pivot_keys: set[tuple[Any, Any]] = set()
    attempt_dates: set[Any] = set()
    prior_break: datetime | None = None
    for record in records:
        _validate_scc_record(record, challenger="hold_time_utc" in record)
        pivot_key = (record["pivot_side"], record["pivot_index"])
        if pivot_key in pivot_keys:
            raise IdentityContractError("SCC record set reuses a consumed pivot")
        pivot_keys.add(pivot_key)
        break_time = normalize_utc(record["break_time_utc"])
        if prior_break is not None and break_time <= prior_break:
            raise IdentityContractError("SCC record set must preserve source break order")
        prior_break = break_time
        attempt_date = break_time.date()
        if attempt_date in attempt_dates:
            raise IdentityContractError("SCC record set violates the one-attempt-per-UTC-date cap")
        attempt_dates.add(attempt_date)


def _normalize_scc_path_bars(
    rows: Sequence[SccPathBar | Mapping[str, Any]],
) -> tuple[SccPathBar, ...]:
    normalized: list[SccPathBar] = []
    required = {"time_utc", "high", "low", "close"}
    allowed = required | {"complete"}
    for row in rows:
        reject_outcome_fields(row)
        if isinstance(row, SccPathBar):
            bar = row
        else:
            reject_unknown_fields(row, allowed, "SCC path bar")
            if not required <= set(row) or set(row) - allowed:
                raise IdentityContractError("SCC path bar requires exact OHLC path fields")
            bar = SccPathBar(
                normalize_utc(row["time_utc"]),
                float(row["high"]),
                float(row["low"]),
                float(row["close"]),
                bool(row.get("complete", True)),
            )
        if type(bar.complete) is not bool:
            raise IdentityContractError("SCC path bar complete flag must be boolean")
        if not all(isfinite(value) for value in (bar.high, bar.low, bar.close)):
            raise IdentityContractError("SCC path bar contains nonfinite price")
        if bar.high < bar.close or bar.low > bar.close or bar.high < bar.low:
            raise IdentityContractError("SCC path bar has invalid OHLC envelope")
        normalized.append(
            SccPathBar(
                normalize_utc(bar.time_utc),
                bar.high,
                bar.low,
                bar.close,
                bar.complete,
            )
        )
    if any(
        normalized[index].time_utc <= normalized[index - 1].time_utc
        for index in range(1, len(normalized))
    ):
        raise IdentityContractError("SCC path bars must be strictly increasing")
    return tuple(normalized)


def _verify_scc_first_passage(
    record: Mapping[str, Any],
    path_index: SccPathIndex,
) -> None:
    _validate_scc_record(record, challenger=True)
    _verify_scc_control_path(record, path_index)
    by_time = path_index.by_time
    break_time = normalize_utc(record["break_time_utc"])
    hold_time = normalize_utc(record["hold_time_utc"])
    retest_time = normalize_utc(record["retest_time_utc"])
    required_times = [
        break_time,
        *(
            hold_time + timedelta(minutes=5 * lag)
            for lag in range(0, int(record["passage_lag"]) + 1)
        ),
    ]
    missing = [utc_key(value) for value in required_times if value not in by_time]
    if missing:
        raise IdentityContractError(f"SCC first-passage replay is missing bar(s): {missing}")
    tick_size = float(record["tick_size"])
    pivot = price_to_ticks(float(record["pivot_price"]), tick_size)
    side = record["direction"]
    hold = by_time[hold_time]
    hold_close = price_to_ticks(hold.close, tick_size)
    if (side == "LONG" and hold_close <= pivot) or (side == "SHORT" and hold_close >= pivot):
        raise IdentityContractError("SCC HOLD does not remain beyond the pivot")
    for lag in range(1, int(record["passage_lag"])):
        bar = by_time[hold_time + timedelta(minutes=5 * lag)]
        close_ticks = price_to_ticks(bar.close, tick_size)
        low_ticks = price_to_ticks(bar.low, tick_size)
        high_ticks = price_to_ticks(bar.high, tick_size)
        if side == "LONG" and (close_ticks <= pivot or low_ticks <= pivot):
            raise IdentityContractError("SCC claimed retest is not the first passage")
        if side == "SHORT" and (close_ticks >= pivot or high_ticks >= pivot):
            raise IdentityContractError("SCC claimed retest is not the first passage")
    retest = by_time[retest_time]
    retest_close = price_to_ticks(retest.close, tick_size)
    retest_low = price_to_ticks(retest.low, tick_size)
    retest_high = price_to_ticks(retest.high, tick_size)
    valid_retest = (
        retest_low <= pivot and retest_close > pivot
        if side == "LONG"
        else retest_high >= pivot and retest_close < pivot
    )
    if not valid_retest:
        raise IdentityContractError("SCC terminal bar is not a valid first-passage retest")


def _verify_scc_control_path(
    record: Mapping[str, Any],
    path_index: SccPathIndex,
) -> None:
    _validate_scc_record(record, challenger="hold_time_utc" in record)
    bars = path_index.bars
    by_time = path_index.by_time
    tick_size = float(record["tick_size"])
    pivot_ticks = price_to_ticks(float(record["pivot_price"]), tick_size)
    confirm_time = normalize_utc(record["pivot_confirm_time_utc"])
    if confirm_time not in path_index.position_by_time:
        raise IdentityContractError("SCC pivot confirmation is absent from the complete-M5 source")
    confirm_index = path_index.position_by_time[confirm_time]
    pivot_index = int(record["pivot_index"])
    if confirm_index != pivot_index + 2 or not 2 <= pivot_index < len(bars) - 2:
        raise IdentityContractError("SCC pivot index/confirmation relation does not match N=2 source semantics")
    pivot_bar = bars[pivot_index]
    if record["pivot_side"] == "HIGH":
        pivot_price_ticks = price_to_ticks(pivot_bar.high, tick_size)
        neighbors = [
            price_to_ticks(bars[index].high, tick_size)
            for index in (pivot_index - 2, pivot_index - 1, pivot_index + 1, pivot_index + 2)
        ]
        strict_pivot = all(pivot_price_ticks > value for value in neighbors)
    else:
        pivot_price_ticks = price_to_ticks(pivot_bar.low, tick_size)
        neighbors = [
            price_to_ticks(bars[index].low, tick_size)
            for index in (pivot_index - 2, pivot_index - 1, pivot_index + 1, pivot_index + 2)
        ]
        strict_pivot = all(pivot_price_ticks < value for value in neighbors)
    if pivot_price_ticks != pivot_ticks or not strict_pivot:
        raise IdentityContractError("SCC source path does not contain the claimed strict N=2 pivot")

    break_time = normalize_utc(record["break_time_utc"])
    if break_time not in path_index.position_by_time:
        raise IdentityContractError("SCC break is absent from the complete-M5 source")
    break_index = path_index.position_by_time[break_time]
    if break_index <= 0:
        raise IdentityContractError("SCC break has no previous retained M5 bar")
    prior_bar = bars[break_index - 1]
    break_bar = bars[break_index]
    if break_bar.time_utc - prior_bar.time_utc != timedelta(minutes=5):
        raise IdentityContractError("SCC break replay is missing the break or previous M5 bar")
    expected_pivot_index = (
        path_index.last_pivot_high_index[break_index]
        if record["pivot_side"] == "HIGH"
        else path_index.last_pivot_low_index[break_index]
    )
    if expected_pivot_index != pivot_index:
        raise IdentityContractError("SCC break does not reference the last confirmed N=2 pivot")
    prior_close = price_to_ticks(prior_bar.close, tick_size)
    break_close = price_to_ticks(break_bar.close, tick_size)
    if record["direction"] == "LONG":
        valid_break = prior_close <= pivot_ticks and break_close > pivot_ticks
    else:
        valid_break = prior_close >= pivot_ticks and break_close < pivot_ticks
    if not valid_break:
        raise IdentityContractError("SCC source path does not contain the claimed close break")

    for scan_index in range(pivot_index + 3, break_index):
        if bars[scan_index].time_utc.date() != break_time.date():
            continue
        if record["pivot_side"] == "HIGH":
            same_pivot = path_index.last_pivot_high_index[scan_index] == pivot_index
        else:
            same_pivot = path_index.last_pivot_low_index[scan_index] == pivot_index
        if not same_pivot or bars[scan_index].time_utc - bars[scan_index - 1].time_utc != timedelta(minutes=5):
            continue
        previous_close = price_to_ticks(bars[scan_index - 1].close, tick_size)
        current_close = price_to_ticks(bars[scan_index].close, tick_size)
        earlier_break = (
            previous_close <= pivot_ticks and current_close > pivot_ticks
            if record["direction"] == "LONG"
            else previous_close >= pivot_ticks and current_close < pivot_ticks
        )
        if earlier_break:
            raise IdentityContractError("SCC claimed break is not the first completed close break")


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
        "tick_size",
        "barrier_id",
        "lock_utc",
    )
    missing = [name for name in base_fields if getattr(audit, name) is None]
    if missing:
        raise IdentityContractError(f"PbpAuditEvent missing provenance field(s): {missing}")
    expected_ticks = price_to_ticks(float(audit.barrier_price), float(audit.tick_size))
    if int(audit.barrier_price_ticks) != expected_ticks:
        raise IdentityContractError(
            "PbpAuditEvent barrier_price_ticks does not match barrier_price/tick_size"
        )
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
    if audit.event_type == "PBP_BREAK_WINDOW" and not (
        audit.k_index - 7 <= audit.break_index <= audit.trigger_index - 1
    ):
        raise IdentityContractError("PBP_BREAK_WINDOW break is outside k-7..trigger-1")
    if audit.event_type == "PBP_TOMBSTONE_CONTACT" and (
        audit.decision_index != audit.contact_index or utc_key(audit.decision_utc) != utc_key(audit.contact_utc)
    ):
        raise IdentityContractError("PBP_TOMBSTONE_CONTACT decision must be the actual contact")
    if audit.event_type == "PBP_TOMBSTONE_CONTACT":
        if not audit.k_index + 1 <= audit.contact_index <= audit.trigger_index - 1:
            raise IdentityContractError("PBP_TOMBSTONE_CONTACT contact is outside correction window")
        if not audit.consumed_index <= audit.contact_index:
            raise IdentityContractError("PBP tombstone must be consumed before contact")
        if audit.contact_index - audit.consumed_index > 48:
            raise IdentityContractError("PBP tombstone contact exceeds 48-bar validity")


def emit_t2_pbp_like_identities(
    audit_events: Sequence[Any],
) -> list[dict[str, Any]]:
    verify_execution_bindings(("p2_formal_spec", "scc_reference", "scc_probe_plan"))
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
