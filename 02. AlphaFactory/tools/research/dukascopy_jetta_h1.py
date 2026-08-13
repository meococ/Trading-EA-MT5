"""Download hash-bound Dukascopy Jetta H1 BID/ASK bars for MTS005.

This tool is source-only.  It downloads the same official Jetta history used
by Dukascopy's current Historical Data Export widget, decodes its delta JSON,
pairs BID and ASK H1 bars, and writes a compact ``AFRATE1`` binary for MT5.
It never computes strategy returns or authorizes an economic verdict.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import struct
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path


AUTHORITY = "SOURCE_DATA_ONLY_NO_PERFORMANCE"
BASE_URL = "https://jetta.dukascopy.com/v1"
SCHEMA = "alphafactory_dukascopy_jetta_h1_source_contract.v1"
RECEIPT_SCHEMA = "alphafactory_dukascopy_jetta_h1_month.v1"
AFRATE_MAGIC = 0x4146524154453100
AFRATE_HEADER = struct.Struct("<QQ")
AFRATE_RECORD = struct.Struct("<qddddqiq")
MIN_REQUEST_INTERVAL_SECONDS = 0.75


class JettaH1Error(RuntimeError):
    pass


@dataclass(frozen=True)
class H1Bar:
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(frozen=True)
class PairedRate:
    time: int
    open: float
    high: float
    low: float
    close: float
    tick_volume: int
    spread: int
    real_volume: int = 0


class HostRateLimiter:
    def __init__(self, interval_seconds: float = MIN_REQUEST_INTERVAL_SECONDS) -> None:
        if not math.isfinite(interval_seconds) or interval_seconds <= 0.0:
            raise ValueError("request interval must be positive")
        self.interval_seconds = interval_seconds
        self._next_start = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        delay = self._next_start - now
        if delay > 0.0:
            time.sleep(delay)
        self._next_start = time.monotonic() + self.interval_seconds

    def penalize(self, seconds: float) -> None:
        self._next_start = max(self._next_start, time.monotonic() + seconds)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    with partial.open("wb") as target:
        target.write(payload)
        target.flush()
        os.fsync(target.fileno())
    partial.replace(path)


def write_json_atomic(path: Path, payload: object) -> None:
    atomic_write(
        path,
        (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )


def load_json_bytes(payload: bytes, label: str) -> dict[str, object]:
    try:
        parsed = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise JettaH1Error(f"invalid JSON for {label}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise JettaH1Error(f"expected JSON object for {label}")
    return parsed


def load_json(path: Path) -> dict[str, object]:
    return load_json_bytes(path.read_bytes(), str(path))


def require_sha256(path: Path, expected: str, label: str) -> str:
    actual = sha256_file(path)
    if not re.fullmatch(r"[A-Fa-f0-9]{64}", expected) or actual != expected.upper():
        raise JettaH1Error(f"{label} SHA256 mismatch: {actual}/{expected}")
    return actual


def month_iter(from_day: date, to_exclusive: date):
    current = date(from_day.year, from_day.month, 1)
    while current < to_exclusive:
        yield current.year, current.month
        current = (
            date(current.year + 1, 1, 1)
            if current.month == 12
            else date(current.year, current.month + 1, 1)
        )


def month_url(
    code: str,
    side: str,
    year: int,
    month: int,
    *,
    partial_from_msc: int | None = None,
) -> str:
    if not re.fullmatch(r"[A-Z0-9]+-[A-Z0-9]+", code):
        raise JettaH1Error(f"invalid Jetta instrument code: {code}")
    if side not in {"BID", "ASK"} or year < 2000 or not 1 <= month <= 12:
        raise JettaH1Error("invalid Jetta H1 URL fields")
    if partial_from_msc is not None:
        if partial_from_msc <= 0:
            raise JettaH1Error("partial-month from timestamp must be positive")
        return f"{BASE_URL}/candles/trade/hour/{code}/{side}?from={partial_from_msc}"
    return f"{BASE_URL}/candles/trade/hour/{code}/{side}/{year}/{month}"


def _finite_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise JettaH1Error(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise JettaH1Error(f"{label} must be finite")
    return result


def _number_array(payload: dict[str, object], name: str) -> list[float]:
    row = payload.get(name)
    if not isinstance(row, list):
        raise JettaH1Error(f"missing Jetta array: {name}")
    return [_finite_number(value, name) for value in row]


def decode_h1(
    payload: bytes,
    label: str,
    *,
    point: float | None = None,
    max_geometry_correction_points: int = 1,
    normalization_stats: dict[str, int] | None = None,
) -> list[H1Bar]:
    row = load_json_bytes(payload, label)
    arrays = {
        name: _number_array(row, name)
        for name in ("times", "opens", "highs", "lows", "closes", "volumes")
    }
    lengths = {len(values) for values in arrays.values()}
    if len(lengths) != 1:
        raise JettaH1Error(f"inconsistent Jetta arrays for {label}")
    count = lengths.pop()
    timestamp = int(_finite_number(row.get("timestamp"), "timestamp"))
    multiplier = _finite_number(row.get("multiplier", 1.0), "multiplier")
    shift = int(_finite_number(row.get("shift", 1.0), "shift"))
    open_value = _finite_number(row.get("open"), "open")
    high_value = _finite_number(row.get("high"), "high")
    low_value = _finite_number(row.get("low"), "low")
    close_value = _finite_number(row.get("close"), "close")
    if timestamp <= 0 or multiplier <= 0.0 or shift <= 0:
        raise JettaH1Error(f"invalid Jetta delta metadata for {label}")
    if point is not None and (not math.isfinite(point) or point <= 0.0):
        raise JettaH1Error("decoder point must be positive")
    if max_geometry_correction_points < 0:
        raise JettaH1Error("maximum geometry correction points cannot be negative")
    bars: list[H1Bar] = []
    previous = -1
    for index in range(count):
        timestamp += shift * int(arrays["times"][index])
        open_value += multiplier * arrays["opens"][index]
        high_value += multiplier * arrays["highs"][index]
        low_value += multiplier * arrays["lows"][index]
        close_value += multiplier * arrays["closes"][index]
        volume = max(1, int(round(arrays["volumes"][index] * 1_000_000.0)))
        bar_open = open_value
        bar_high = high_value
        bar_low = low_value
        bar_close = close_value
        if point is not None:
            bar_open = round(bar_open / point) * point
            bar_high = round(bar_high / point) * point
            bar_low = round(bar_low / point) * point
            bar_close = round(bar_close / point) * point
        values = (bar_open, bar_high, bar_low, bar_close)
        tolerance = (point if point is not None else 1e-12) / 1000.0
        high_deficit = max(bar_open, bar_close) - bar_high
        low_excess = bar_low - min(bar_open, bar_close)
        max_allowed_geometry_correction = (
            max_geometry_correction_points * point if point is not None else 0.0
        )
        if (
            high_deficit > tolerance or low_excess > tolerance
        ) and (
            point is None
            or high_deficit > max_allowed_geometry_correction + tolerance
            or low_excess > max_allowed_geometry_correction + tolerance
        ):
            limit_label = (
                "one point"
                if max_geometry_correction_points == 1
                else f"{max_geometry_correction_points} points"
            )
            raise JettaH1Error(
                f"H1 OHLC geometry correction exceeds {limit_label} at bar {index} for {label}"
            )
        if high_deficit > tolerance or low_excess > tolerance:
            bar_high = max(bar_high, bar_open, bar_close)
            bar_low = min(bar_low, bar_open, bar_close)
            if normalization_stats is not None:
                normalization_stats["one_point_envelope_corrections"] = (
                    normalization_stats.get("one_point_envelope_corrections", 0) + 1
                )
        if (
            timestamp <= previous
            or timestamp % 3_600_000 != 0
            or any(not math.isfinite(value) or value <= 0.0 for value in values)
            or bar_high + tolerance < max(bar_open, bar_close)
            or bar_low - tolerance > min(bar_open, bar_close)
        ):
            raise JettaH1Error(f"invalid H1 bar {index} for {label}")
        bars.append(
            H1Bar(
                timestamp // 1000,
                bar_open,
                bar_high,
                bar_low,
                bar_close,
                volume,
            )
        )
        previous = timestamp
    return bars


def geometry_policy(row: dict[str, object], year: int, month: int) -> tuple[int, float | None]:
    max_points = int(row.get("max_geometry_correction_points", 1))
    max_fraction: float | None = None
    exceptions = row.get("geometry_exception_months", {})
    if not isinstance(exceptions, dict):
        raise JettaH1Error("geometry_exception_months must be an object")
    override = exceptions.get(f"{year:04d}-{month:02d}")
    if override is not None:
        if not isinstance(override, dict):
            raise JettaH1Error("geometry exception month must be an object")
        max_points = int(override.get("max_correction_points", max_points))
        if "max_corrected_bar_fraction_per_side" in override:
            max_fraction = float(override["max_corrected_bar_fraction_per_side"])
    if max_points < 0 or (max_fraction is not None and not 0.0 <= max_fraction <= 1.0):
        raise JettaH1Error("invalid frozen geometry policy")
    return max_points, max_fraction


def validate_geometry_fraction(
    *,
    label: str,
    bars: list[H1Bar],
    stats: dict[str, int],
    max_fraction: float | None,
) -> None:
    if max_fraction is None:
        return
    corrected = stats.get("one_point_envelope_corrections", 0)
    fraction = corrected / max(1, len(bars))
    if fraction > max_fraction + 1e-12:
        raise JettaH1Error(
            f"H1 OHLC corrected-bar fraction {fraction:.9f} exceeds "
            f"{max_fraction:.9f} for {label}"
        )


def pair_rates(
    bid: list[H1Bar],
    ask: list[H1Bar],
    point: float,
    start: int,
    end: int,
    *,
    strategy_active_from: int | None = None,
    allow_crossed_open_before_activation: bool = False,
    inactive_crossed_open_spread_points: int = 1,
    pairing_stats: dict[str, int] | None = None,
) -> list[PairedRate]:
    if not math.isfinite(point) or point <= 0.0:
        raise JettaH1Error("point must be positive")
    if inactive_crossed_open_spread_points < 1:
        raise JettaH1Error("inactive crossed-open spread must be at least one point")
    bid_by_time = {bar.time: bar for bar in bid if start <= bar.time < end}
    ask_by_time = {bar.time: bar for bar in ask if start <= bar.time < end}
    if set(bid_by_time) != set(ask_by_time):
        raise JettaH1Error("BID/ASK H1 timestamps do not match")
    paired: list[PairedRate] = []
    for timestamp in sorted(bid_by_time):
        bid_bar = bid_by_time[timestamp]
        ask_bar = ask_by_time[timestamp]
        # H1 ASK/BID highs and lows occur at independently timed extrema.  An
        # ASK low may therefore be below the BID low even though every
        # contemporaneous quote is uncrossed.  Only the bar-open pair is used
        # by this contract to construct spread and can be compared directly.
        crossed = ask_bar.open + point / 1000.0 < bid_bar.open
        if crossed:
            if (
                not allow_crossed_open_before_activation
                or strategy_active_from is None
                or timestamp >= strategy_active_from
            ):
                raise JettaH1Error(f"ASK open below BID open at {timestamp}")
            deficit_points = int(
                math.ceil((bid_bar.open - ask_bar.open) / point - 1e-8)
            )
            spread = inactive_crossed_open_spread_points
            if pairing_stats is not None:
                pairing_stats["preactivation_crossed_open_count"] = (
                    pairing_stats.get("preactivation_crossed_open_count", 0) + 1
                )
                pairing_stats["maximum_preactivation_crossed_open_deficit_points"] = max(
                    pairing_stats.get(
                        "maximum_preactivation_crossed_open_deficit_points", 0
                    ),
                    deficit_points,
                )
        else:
            raw_points = (ask_bar.open - bid_bar.open) / point
            spread = max(1, int(math.ceil(raw_points - 1e-8)))
        paired.append(
            PairedRate(
                timestamp,
                bid_bar.open,
                bid_bar.high,
                bid_bar.low,
                bid_bar.close,
                bid_bar.volume,
                spread,
            )
        )
    if not paired:
        raise JettaH1Error("month contains no paired H1 bars in contract range")
    return paired


def encode_rates(rates: list[PairedRate]) -> bytes:
    payload = bytearray(AFRATE_HEADER.pack(AFRATE_MAGIC, len(rates)))
    previous = -1
    for rate in rates:
        if rate.time <= previous or rate.spread < 1:
            raise JettaH1Error("rate order/spread invariant failed")
        payload.extend(
            AFRATE_RECORD.pack(
                rate.time,
                rate.open,
                rate.high,
                rate.low,
                rate.close,
                rate.tick_volume,
                rate.spread,
                rate.real_volume,
            )
        )
        previous = rate.time
    return bytes(payload)


def fetch_with_retry(
    url: str, timeout: int, retries: int, limiter: HostRateLimiter
) -> tuple[bytes, dict[str, str]]:
    last_error = "unknown"
    for attempt in range(1, retries + 1):
        limiter.wait()
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "AlphaFactory-MTS005-source-research/1.0",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = response.read()
                return payload, {key.lower(): value for key, value in response.headers.items()}
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code}"
            if exc.code in {429, 503}:
                limiter.penalize(min(60.0, 15.0 * attempt))
            elif 400 <= exc.code < 500:
                raise JettaH1Error(f"non-retryable {last_error}: {url}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = str(exc)
        if attempt < retries:
            time.sleep(min(10.0, float(attempt)))
    raise JettaH1Error(f"download failed after {retries} attempts: {url}: {last_error}")


def _month_bounds(year: int, month: int) -> tuple[int, int]:
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end = (
        datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        if month == 12
        else datetime(year, month + 1, 1, tzinfo=timezone.utc)
    )
    return int(start.timestamp()), int(end.timestamp())


def acquire_month(
    *,
    row: dict[str, object],
    year: int,
    month: int,
    contract_sha: str,
    output_root: Path,
    timeout: int,
    retries: int,
    limiter: HostRateLimiter,
    superseded_contract_shas: set[str] | None = None,
) -> dict[str, object]:
    symbol = str(row["source_symbol"])
    code = str(row["jetta_code"])
    digits = int(row["digits"])
    point = 10.0 ** (-digits)
    contract_start = int(
        datetime.fromisoformat(str(row["history_from"])).replace(tzinfo=timezone.utc).timestamp()
    )
    contract_end = int(
        datetime.fromisoformat(str(row["history_to_exclusive"])).replace(tzinfo=timezone.utc).timestamp()
    )
    strategy_active_from = int(
        datetime.fromisoformat(str(row["strategy_active_from"]).replace("Z", "+00:00"))
        .astimezone(timezone.utc)
        .timestamp()
    )
    allow_crossed_open_before_activation = bool(
        row.get("allow_crossed_open_before_strategy_activation", False)
    )
    inactive_crossed_open_spread_points = int(
        row.get("inactive_crossed_open_spread_points", 1)
    )
    month_start, month_end = _month_bounds(year, month)
    start, end = max(month_start, contract_start), min(month_end, contract_end)
    partial_from_msc = month_start * 1000 if contract_end < month_end else None
    stem = Path(symbol) / f"{year:04d}" / f"{month:02d}"
    receipt_path = output_root / "receipts" / stem.with_suffix(".json")
    binary_path = output_root / "decoded" / stem.with_suffix(".afrates")
    raw_paths = {
        side: output_root / "raw" / stem.with_name(f"{month:02d}_{side.lower()}.json")
        for side in ("BID", "ASK")
    }
    raw_payloads: dict[str, bytes] = {}
    headers: dict[str, dict[str, str]] = {}
    normalization_by_side: dict[str, dict[str, int]] = {}
    max_geometry_points, max_geometry_fraction = geometry_policy(row, year, month)
    rebound_from_contract_sha: str | None = None
    if receipt_path.is_file() and binary_path.is_file() and all(path.is_file() for path in raw_paths.values()):
        old = load_json(receipt_path)
        binary = old.get("binary")
        raw = old.get("raw")
        binding = old.get("source_contract")
        retained_valid = (
            old.get("schema_version") == RECEIPT_SCHEMA
            and old.get("status") == "PASS"
            and isinstance(binary, dict)
            and isinstance(raw, dict)
            and isinstance(binding, dict)
            and sha256_file(binary_path) == binary.get("sha256")
            and all(
                isinstance(raw.get(side), dict)
                and sha256_file(raw_paths[side]) == raw[side].get("sha256")
                for side in ("BID", "ASK")
            )
        )
        if not retained_valid:
            raise JettaH1Error(f"existing month receipt failed verification: {receipt_path}")
        old_contract_sha = str(binding.get("sha256", "")).upper()
        if old_contract_sha == contract_sha:
            return old
        allowed = {value.upper() for value in (superseded_contract_shas or set())}
        if old_contract_sha not in allowed:
            raise JettaH1Error(
                f"existing month receipt has unauthorized contract identity: {receipt_path}"
            )
        rebound_from_contract_sha = old_contract_sha
        for side in ("BID", "ASK"):
            payload = raw_paths[side].read_bytes()
            normalization_by_side[side] = {}
            decoded = decode_h1(
                payload,
                f"{symbol} {year}-{month:02d} {side}",
                point=point,
                max_geometry_correction_points=max_geometry_points,
                normalization_stats=normalization_by_side[side],
            )
            validate_geometry_fraction(
                label=f"{symbol} {year}-{month:02d} {side}",
                bars=decoded,
                stats=normalization_by_side[side],
                max_fraction=max_geometry_fraction,
            )
            raw_payloads[side] = payload
            old_side = raw.get(side)
            headers[side] = {
                "content-type": str(old_side.get("content_type", ""))
                if isinstance(old_side, dict)
                else ""
            }
    elif all(path.is_file() for path in raw_paths.values()):
        for side in ("BID", "ASK"):
            payload = raw_paths[side].read_bytes()
            normalization_by_side[side] = {}
            decoded = decode_h1(
                payload,
                f"{symbol} {year}-{month:02d} {side}",
                point=point,
                max_geometry_correction_points=max_geometry_points,
                normalization_stats=normalization_by_side[side],
            )
            validate_geometry_fraction(
                label=f"{symbol} {year}-{month:02d} {side}",
                bars=decoded,
                stats=normalization_by_side[side],
                max_fraction=max_geometry_fraction,
            )
            raw_payloads[side] = payload
            headers[side] = {"content-type": "application/json"}
    else:
        for side in ("BID", "ASK"):
            url = month_url(
                code,
                side,
                year,
                month,
                partial_from_msc=partial_from_msc,
            )
            payload, response_headers = fetch_with_retry(
                url, timeout, retries, limiter
            )
            normalization_by_side[side] = {}
            decoded = decode_h1(
                payload,
                f"{symbol} {year}-{month:02d} {side}",
                point=point,
                max_geometry_correction_points=max_geometry_points,
                normalization_stats=normalization_by_side[side],
            )
            validate_geometry_fraction(
                label=f"{symbol} {year}-{month:02d} {side}",
                bars=decoded,
                stats=normalization_by_side[side],
                max_fraction=max_geometry_fraction,
            )
            atomic_write(raw_paths[side], payload)
            raw_payloads[side] = payload
            headers[side] = response_headers
    pairing_stats: dict[str, int] = {}
    rates = pair_rates(
        decode_h1(
            raw_payloads["BID"],
            "BID",
            point=point,
            max_geometry_correction_points=max_geometry_points,
        ),
        decode_h1(
            raw_payloads["ASK"],
            "ASK",
            point=point,
            max_geometry_correction_points=max_geometry_points,
        ),
        point,
        start,
        end,
        strategy_active_from=strategy_active_from,
        allow_crossed_open_before_activation=allow_crossed_open_before_activation,
        inactive_crossed_open_spread_points=inactive_crossed_open_spread_points,
        pairing_stats=pairing_stats,
    )
    binary_payload = encode_rates(rates)
    atomic_write(binary_path, binary_payload)
    spreads = [rate.spread for rate in rates]
    receipt: dict[str, object] = {
        "schema_version": RECEIPT_SCHEMA,
        "authority": AUTHORITY,
        "economics_authorized": False,
        "performance_metrics_authorized": False,
        "status": "PASS",
        "hypothesis_id": "HYP-MULTI-TSMOM-D1-005",
        "symbol": symbol,
        "jetta_code": code,
        "year_month_utc": f"{year:04d}-{month:02d}",
        "range_from_epoch": start,
        "range_to_exclusive_epoch": end,
        "source_contract": {"sha256": contract_sha},
        "raw": {
            side: {
                "url": month_url(
                    code,
                    side,
                    year,
                    month,
                    partial_from_msc=partial_from_msc,
                ),
                "path": raw_paths[side].as_posix(),
                "sha256": sha256_bytes(raw_payloads[side]),
                "bytes": len(raw_payloads[side]),
                "content_type": headers[side].get("content-type", ""),
            }
            for side in ("BID", "ASK")
        },
        "binary": {
            "schema": "AFRATE1 <QQ header, <qddddqiq records",
            "path": binary_path.as_posix(),
            "sha256": sha256_bytes(binary_payload),
            "bytes": len(binary_payload),
            "count": len(rates),
            "first_epoch": rates[0].time,
            "last_epoch": rates[-1].time,
        },
        "spread_points": {
            "construction": "max(1,ceil((ASK_open-BID_open)/source_point))",
            "minimum": min(spreads),
            "maximum": max(spreads),
            "mean": sum(spreads) / len(spreads),
            "zero_count": 0,
        },
        "bid_ask_open_source_containment": {
            "policy": "Crossed ASK/BID opens fail except when the symbol row explicitly allows source-only containment strictly before strategy activation; inactive contained bars receive the frozen minimum spread for MT5 rate validity.",
            "strategy_active_from_epoch": strategy_active_from,
            "preactivation_crossed_open_count": pairing_stats.get(
                "preactivation_crossed_open_count", 0
            ),
            "maximum_preactivation_crossed_open_deficit_points": pairing_stats.get(
                "maximum_preactivation_crossed_open_deficit_points", 0
            ),
            "contained_spread_points": inactive_crossed_open_spread_points,
            "crossed_open_on_or_after_activation_count": 0,
        },
        "source_geometry_normalization": {
            "policy": "Round prices to source point, then expand high/low within the frozen symbol/month cap to contain open/close; fail larger or over-frequency corrections.",
            "maximum_allowed_envelope_correction_points": max_geometry_points,
            "maximum_corrected_bar_fraction_per_side": max_geometry_fraction,
            "bid_one_point_envelope_corrections": normalization_by_side["BID"].get(
                "one_point_envelope_corrections", 0
            ),
            "ask_one_point_envelope_corrections": normalization_by_side["ASK"].get(
                "one_point_envelope_corrections", 0
            ),
        },
    }
    if rebound_from_contract_sha is not None:
        receipt["rebound_from_contract_sha256"] = rebound_from_contract_sha
    write_json_atomic(receipt_path, receipt)
    return receipt


def validate_contract(path: Path, expected_sha: str) -> tuple[dict[str, object], str]:
    actual = require_sha256(path, expected_sha, "source contract")
    contract = load_json(path)
    if (
        contract.get("schema_version") != SCHEMA
        or contract.get("hypothesis_id") != "HYP-MULTI-TSMOM-D1-005"
        or contract.get("authority") != AUTHORITY
        or contract.get("economics_authorized") is not False
        or contract.get("performance_metrics_authorized") is not False
    ):
        raise JettaH1Error("source contract authority/schema mismatch")
    download = contract.get("download")
    rows = contract.get("symbols")
    if not isinstance(download, dict) or not isinstance(rows, list) or len(rows) != 9:
        raise JettaH1Error("source contract is incomplete")
    if (
        int(download.get("workers", -1)) != 1
        or float(download.get("minimum_request_interval_seconds", -1.0))
        != MIN_REQUEST_INTERVAL_SECONDS
    ):
        raise JettaH1Error("source contract request policy mismatch")
    superseded = contract.get("supersedes_contract_sha256s", [])
    if not isinstance(superseded, list) or any(
        not isinstance(value, str) or not re.fullmatch(r"[A-Fa-f0-9]{64}", value)
        for value in superseded
    ):
        raise JettaH1Error("source contract supersession list is invalid")
    return contract, actual


def contract_superseded_shas(contract: dict[str, object]) -> set[str]:
    values = contract.get("supersedes_contract_sha256s", [])
    if not isinstance(values, list):
        raise JettaH1Error("source contract supersession list is invalid")
    return {str(value).upper() for value in values}


def download_contract(args: argparse.Namespace) -> int:
    contract, contract_sha = validate_contract(args.contract, args.contract_sha256)
    download = contract["download"]
    if not isinstance(download, dict):
        raise JettaH1Error("invalid download contract")
    timeout = int(download["timeout_seconds"])
    retries = int(download["retries"])
    limiter = HostRateLimiter(MIN_REQUEST_INTERVAL_SECONDS)
    rows = contract["symbols"]
    superseded_contract_shas = contract_superseded_shas(contract)
    assert isinstance(rows, list)
    for raw_row in rows:
        if not isinstance(raw_row, dict):
            raise JettaH1Error("invalid symbol contract row")
        from_day = date.fromisoformat(str(raw_row["history_from"]))
        to_exclusive = date.fromisoformat(str(raw_row["history_to_exclusive"]))
        for year, month in month_iter(from_day, to_exclusive):
            receipt = acquire_month(
                row=raw_row,
                year=year,
                month=month,
                contract_sha=contract_sha,
                output_root=args.output_root.resolve(),
                timeout=timeout,
                retries=retries,
                limiter=limiter,
                superseded_contract_shas=superseded_contract_shas,
            )
            print(
                f"PASS {raw_row['source_symbol']} {year:04d}-{month:02d} "
                f"h1={receipt['binary']['count']} sha256={receipt['binary']['sha256']}",
                flush=True,
            )
    return 0


def probe_month(args: argparse.Namespace) -> int:
    contract, contract_sha = validate_contract(args.contract, args.contract_sha256)
    download = contract["download"]
    rows = contract["symbols"]
    assert isinstance(download, dict) and isinstance(rows, list)
    selected = [
        row
        for row in rows
        if isinstance(row, dict) and row.get("source_symbol") == args.symbol.upper()
    ]
    if len(selected) != 1:
        raise JettaH1Error(f"expected one contract row for {args.symbol}")
    row = selected[0]
    superseded_contract_shas = contract_superseded_shas(contract)
    valid_months = set(
        month_iter(
            date.fromisoformat(str(row["history_from"])),
            date.fromisoformat(str(row["history_to_exclusive"])),
        )
    )
    if (args.year, args.month) not in valid_months:
        raise JettaH1Error("probe month is outside the frozen source range")
    receipt = acquire_month(
        row=row,
        year=args.year,
        month=args.month,
        contract_sha=contract_sha,
        output_root=args.output_root.resolve(),
        timeout=int(download["timeout_seconds"]),
        retries=int(download["retries"]),
        limiter=HostRateLimiter(MIN_REQUEST_INTERVAL_SECONDS),
        superseded_contract_shas=superseded_contract_shas,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True), flush=True)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dukascopy Jetta H1 source acquisition")
    subparsers = parser.add_subparsers(dest="command", required=True)
    command = subparsers.add_parser("download-contract")
    command.add_argument("--contract", type=Path, required=True)
    command.add_argument("--contract-sha256", required=True)
    command.add_argument("--output-root", type=Path, required=True)
    command.set_defaults(func=download_contract)
    probe = subparsers.add_parser("probe-month")
    probe.add_argument("--contract", type=Path, required=True)
    probe.add_argument("--contract-sha256", required=True)
    probe.add_argument("--output-root", type=Path, required=True)
    probe.add_argument("--symbol", required=True)
    probe.add_argument("--year", type=int, required=True)
    probe.add_argument("--month", type=int, required=True)
    probe.set_defaults(func=probe_month)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except JettaH1Error as exc:
        print(f"FATAL {exc}", flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
