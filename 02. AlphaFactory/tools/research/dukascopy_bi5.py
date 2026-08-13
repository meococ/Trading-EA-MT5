"""Deterministic Dukascopy BI5 tick acquisition for MT5 custom symbols.

This module is source-data infrastructure only.  It never computes a signal,
places an order, or authorizes a performance claim.  Dukascopy tick chunks are
hourly LZMA streams of big-endian ``>3I2f`` records:

``millisecond_offset, ask_scaled, bid_scaled, ask_volume, bid_volume``.

The downloader keeps the compressed hourly payloads, emits one compact
``AFDTICK1`` daily binary, and writes a hash-bound daily receipt only after all
24 hours have passed structural validation.  Existing receipts form the
resume boundary and are re-verified before they are trusted.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import lzma
import math
import os
import struct
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable, NamedTuple


BASE_URL = "https://datafeed.dukascopy.com/datafeed"
BI5_RECORD = struct.Struct(">3I2f")
AFD_HEADER = struct.Struct("<QQ")
AFD_RECORD = struct.Struct("<qdd")
AFD_MAGIC = 0x4146445449434B31  # ASCII AFDTICK1
USER_AGENT = "AlphaFactory-Dukascopy-Research/2.0"
ALLOWED_AUTHORITY = "SOURCE_DATA_ONLY_NO_PERFORMANCE"
MIN_LIVE_REQUEST_INTERVAL_SECONDS = 0.25


class HostRateLimiter:
    """Serialize live host requests and share 429/503 cooldown across workers."""

    def __init__(
        self,
        minimum_interval_seconds: float,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if minimum_interval_seconds < 0.0:
            raise ValueError("minimum interval must be non-negative")
        self.minimum_interval_seconds = minimum_interval_seconds
        self.clock = clock
        self.sleeper = sleeper
        self.lock = threading.Lock()
        self.next_request = 0.0

    def wait(self) -> None:
        with self.lock:
            now = self.clock()
            delay = max(0.0, self.next_request - now)
            if delay > 0.0:
                self.sleeper(delay)
                now = self.clock()
            self.next_request = max(now, self.next_request) + self.minimum_interval_seconds

    def penalize(self, seconds: float) -> None:
        if seconds <= 0.0:
            return
        with self.lock:
            self.next_request = max(self.next_request, self.clock() + seconds)


LIVE_HOST_LIMITER = HostRateLimiter(MIN_LIVE_REQUEST_INTERVAL_SECONDS)


class Bi5ValidationError(ValueError):
    """A source payload or receipt violates the frozen data contract."""


@dataclass(frozen=True)
class SymbolGeometry:
    divider: int
    digits: int
    provenance: str

    @property
    def point(self) -> float:
        return 1.0 / float(self.divider)


class Tick(NamedTuple):
    time_msc: int
    bid: float
    ask: float
    bid_volume_raw: float
    ask_volume_raw: float


class DecodeResult(NamedTuple):
    ticks: tuple[Tick, ...]
    count: int
    same_millisecond_pairs: int
    zero_spread_quotes: int
    first_time_msc: int | None
    last_time_msc: int | None


SYMBOL_GEOMETRY: dict[str, SymbolGeometry] = {
    "EURUSD": SymbolGeometry(100_000, 5, "Dukascopy FX BI5 convention"),
    "GBPUSD": SymbolGeometry(100_000, 5, "Dukascopy FX BI5 convention"),
    "AUDUSD": SymbolGeometry(100_000, 5, "Dukascopy FX BI5 convention"),
    "NZDUSD": SymbolGeometry(100_000, 5, "Dukascopy FX BI5 convention"),
    "USDJPY": SymbolGeometry(1_000, 3, "Dukascopy JPY BI5 convention"),
    "USDCAD": SymbolGeometry(100_000, 5, "Dukascopy FX BI5 convention"),
    "USDCHF": SymbolGeometry(100_000, 5, "Dukascopy FX BI5 convention"),
    "XAUUSD": SymbolGeometry(1_000, 3, "Dukascopy XAU/USD BI5 convention"),
    "BTCUSD": SymbolGeometry(10, 1, "Dukascopy BTC/USD BI5 scale probe"),
}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    with partial.open("wb") as target:
        target.write(payload)
        target.flush()
        os.fsync(target.fileno())
    partial.replace(path)


def write_json_atomic(path: Path, payload: object) -> None:
    encoded = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    _atomic_write(path, encoded)


def load_strict_json(path: Path) -> dict[str, object]:
    def reject_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise Bi5ValidationError(f"duplicate JSON key {key!r} in {path}")
            result[key] = value
        return result

    try:
        parsed = json.loads(
            path.read_text(encoding="utf-8-sig"),
            parse_constant=lambda token: (_ for _ in ()).throw(
                Bi5ValidationError(f"non-finite JSON token {token} in {path}")
            ),
            object_pairs_hook=reject_pairs,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Bi5ValidationError(f"invalid JSON {path}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise Bi5ValidationError(f"JSON root must be an object: {path}")
    return parsed


def parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid ISO date: {value}") from exc


def parse_hour(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid ISO hour: {value}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("hour must contain an explicit UTC offset")
    parsed = parsed.astimezone(timezone.utc)
    if parsed.minute or parsed.second or parsed.microsecond:
        raise argparse.ArgumentTypeError("hour must be aligned to HH:00:00 UTC")
    return parsed


def chunk_url(symbol: str, hour_start: datetime) -> str:
    symbol = symbol.upper()
    if symbol not in SYMBOL_GEOMETRY:
        raise Bi5ValidationError(f"unsupported symbol: {symbol}")
    if hour_start.tzinfo is None or hour_start.utcoffset() is None:
        raise Bi5ValidationError("hour_start must be timezone-aware")
    hour = hour_start.astimezone(timezone.utc)
    return (
        f"{BASE_URL}/{symbol}/{hour.year:04d}/{hour.month - 1:02d}/"
        f"{hour.day:02d}/{hour.hour:02d}h_ticks.bi5"
    )


def decode_bi5(payload: bytes, *, symbol: str, hour_start: datetime) -> DecodeResult:
    symbol = symbol.upper()
    geometry = SYMBOL_GEOMETRY.get(symbol)
    if geometry is None:
        raise Bi5ValidationError(f"unsupported symbol: {symbol}")
    if hour_start.tzinfo is None or hour_start.utcoffset() is None:
        raise Bi5ValidationError("hour_start must be timezone-aware")
    hour = hour_start.astimezone(timezone.utc)
    if hour.minute or hour.second or hour.microsecond:
        raise Bi5ValidationError("hour_start must be aligned to a UTC hour")
    try:
        decoded = lzma.decompress(payload, format=lzma.FORMAT_AUTO)
    except lzma.LZMAError as exc:
        raise Bi5ValidationError(f"LZMA decode failed: {exc}") from exc
    if len(decoded) % BI5_RECORD.size:
        raise Bi5ValidationError(
            f"decompressed payload length must be a multiple of 20; got {len(decoded)}"
        )

    base_msc = int(hour.timestamp()) * 1000
    ticks: list[Tick] = []
    previous_offset: int | None = None
    same_millisecond_pairs = 0
    zero_spread_quotes = 0
    for offset in range(0, len(decoded), BI5_RECORD.size):
        ms, ask_raw, bid_raw, ask_volume, bid_volume = BI5_RECORD.unpack_from(decoded, offset)
        if ms >= 3_600_000:
            raise Bi5ValidationError(f"millisecond offset outside hour: {ms}")
        if previous_offset is not None:
            if ms < previous_offset:
                raise Bi5ValidationError(
                    f"tick time regressed: previous={previous_offset} current={ms}"
                )
            if ms == previous_offset:
                same_millisecond_pairs += 1
        previous_offset = ms
        if ask_raw <= 0 or bid_raw <= 0:
            raise Bi5ValidationError("nonpositive bid/ask raw price")
        if ask_raw < bid_raw:
            raise Bi5ValidationError(f"crossed quote: ask={ask_raw} bid={bid_raw}")
        if not math.isfinite(ask_volume) or not math.isfinite(bid_volume):
            raise Bi5ValidationError("non-finite quote volume")
        if ask_volume < 0.0 or bid_volume < 0.0:
            raise Bi5ValidationError("negative quote volume")
        if ask_raw == bid_raw:
            zero_spread_quotes += 1
        ticks.append(
            Tick(
                base_msc + ms,
                bid_raw / geometry.divider,
                ask_raw / geometry.divider,
                float(bid_volume),
                float(ask_volume),
            )
        )
    return DecodeResult(
        tuple(ticks),
        len(ticks),
        same_millisecond_pairs,
        zero_spread_quotes,
        ticks[0].time_msc if ticks else None,
        ticks[-1].time_msc if ticks else None,
    )


def write_day_binary(path: Path, ticks: Iterable[Tick]) -> dict[str, object]:
    ordered = tuple(ticks)
    previous = -1
    source_day: date | None = None
    for tick in ordered:
        if tick.time_msc < previous:
            raise Bi5ValidationError("day binary tick order regressed")
        previous = tick.time_msc
        tick_day = datetime.fromtimestamp(tick.time_msc / 1000, tz=timezone.utc).date()
        if source_day is None:
            source_day = tick_day
        elif tick_day != source_day:
            raise Bi5ValidationError("day binary contains more than one UTC day")
    payload = bytearray(AFD_HEADER.pack(AFD_MAGIC, len(ordered)))
    for tick in ordered:
        payload.extend(AFD_RECORD.pack(tick.time_msc, tick.bid, tick.ask))
    _atomic_write(path, bytes(payload))
    return {
        "schema_version": "alphafactory_afdticks.v1",
        "path": path.resolve().as_posix(),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "header_bytes": AFD_HEADER.size,
        "record_bytes": AFD_RECORD.size,
        "count": len(ordered),
        "first_time_msc": ordered[0].time_msc if ordered else 0,
        "last_time_msc": ordered[-1].time_msc if ordered else 0,
    }


def fetch_hour(url: str, *, timeout: int) -> tuple[int, bytes, dict[str, str]]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.status), response.read(), {
                "content_type": response.headers.get("Content-Type", ""),
                "etag": response.headers.get("ETag", ""),
                "last_modified": response.headers.get("Last-Modified", ""),
            }
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return 404, b"", {}
        raise


def _fetch_with_retry(
    url: str,
    *,
    timeout: int,
    retries: int,
    fetcher: Callable[..., tuple[int, bytes, dict[str, str]]] = fetch_hour,
) -> tuple[int, bytes, dict[str, str], int]:
    last_error: BaseException | None = None
    for attempt in range(1, retries + 2):
        try:
            if fetcher is fetch_hour:
                LIVE_HOST_LIMITER.wait()
            status, payload, headers = fetcher(url, timeout=timeout)
            if status not in {200, 404}:
                raise Bi5ValidationError(f"unexpected HTTP status {status} for {url}")
            return status, payload, headers, attempt
        except (OSError, TimeoutError, urllib.error.URLError, Bi5ValidationError) as exc:
            last_error = exc
            if (
                fetcher is fetch_hour
                and isinstance(exc, urllib.error.HTTPError)
                and exc.code in {429, 503}
            ):
                LIVE_HOST_LIMITER.penalize(min(60.0, 15.0 * attempt))
            if attempt <= retries:
                time.sleep(min(8.0, float(2 ** (attempt - 1))))
    raise Bi5ValidationError(
        f"download failed after {retries + 1} attempts: {url}: {last_error}"
    )


def _day_paths(root: Path, symbol: str, source_day: date) -> tuple[Path, Path, Path]:
    stem = Path(f"{source_day.year:04d}/{source_day.month:02d}")
    raw = root / symbol / "raw" / stem / f"{source_day.day:02d}"
    binary = root / symbol / "decoded" / stem / f"{source_day.isoformat()}.afdticks"
    receipt = root / symbol / "receipts" / stem / f"{source_day.isoformat()}.json"
    return raw, binary, receipt


def _verify_existing_day(
    receipt_path: Path,
    binary_path: Path,
    *,
    symbol: str,
    source_day: date,
    contract_sha256: str,
) -> dict[str, object] | None:
    if not receipt_path.is_file() or not binary_path.is_file():
        return None
    receipt = load_strict_json(receipt_path)
    binary = receipt.get("binary")
    binding = receipt.get("source_contract")
    if not isinstance(binary, dict) or not isinstance(binding, dict):
        raise Bi5ValidationError(f"invalid existing receipt shape: {receipt_path}")
    valid = (
        receipt.get("schema_version") == "alphafactory_dukascopy_bi5_day.v2"
        and receipt.get("authority") == ALLOWED_AUTHORITY
        and receipt.get("status") == "PASS"
        and receipt.get("symbol") == symbol
        and receipt.get("date_utc") == source_day.isoformat()
        and binding.get("sha256") == contract_sha256
        and binary.get("sha256") == sha256_file(binary_path)
        and binary.get("bytes") == binary_path.stat().st_size
    )
    if not valid:
        raise Bi5ValidationError(f"existing receipt/binary binding mismatch: {receipt_path}")
    receipt["acquisition"] = "VERIFIED_EXISTING_DAY"
    return receipt


def acquire_day(
    *,
    symbol: str,
    source_day: date,
    root: Path,
    timeout: int,
    retries: int,
    workers: int,
    contract_path: Path,
    contract_sha256: str,
    fetcher: Callable[..., tuple[int, bytes, dict[str, str]]] = fetch_hour,
) -> dict[str, object]:
    symbol = symbol.upper()
    if symbol not in SYMBOL_GEOMETRY:
        raise Bi5ValidationError(f"unsupported symbol: {symbol}")
    if not 1 <= workers <= 16 or not 0 <= retries <= 8:
        raise Bi5ValidationError("workers/retries outside allowed bounds")
    root = root.resolve()
    raw_root, binary_path, receipt_path = _day_paths(root, symbol, source_day)
    existing = _verify_existing_day(
        receipt_path,
        binary_path,
        symbol=symbol,
        source_day=source_day,
        contract_sha256=contract_sha256,
    )
    if existing is not None:
        return existing

    started = datetime.now(timezone.utc)

    def acquire_hour(hour: int) -> tuple[int, tuple[Tick, ...], dict[str, object]]:
        hour_start = datetime(
            source_day.year, source_day.month, source_day.day, hour, tzinfo=timezone.utc
        )
        url = chunk_url(symbol, hour_start)
        raw_path = raw_root / f"{hour:02d}h_ticks.bi5"
        empty_marker = raw_root / f"{hour:02d}h_ticks.empty.json"
        if raw_path.is_file():
            payload = raw_path.read_bytes()
            decoded = decode_bi5(payload, symbol=symbol, hour_start=hour_start)
            return hour, decoded.ticks, {
                "hour": hour,
                "hour_start_utc": hour_start.isoformat().replace("+00:00", "Z"),
                "url": url,
                "http_status": 200,
                "status": "PASS",
                "acquisition": "VERIFIED_EXISTING_HOUR",
                "request_attempts": 0,
                "tick_count": decoded.count,
                "same_millisecond_pairs": decoded.same_millisecond_pairs,
                "zero_spread_quotes": decoded.zero_spread_quotes,
                "first_time_msc": decoded.first_time_msc,
                "last_time_msc": decoded.last_time_msc,
                "headers": {},
                "raw": {
                    "path": raw_path.resolve().as_posix(),
                    "bytes": raw_path.stat().st_size,
                    "sha256": sha256_file(raw_path),
                },
            }
        if empty_marker.is_file():
            marker = load_strict_json(empty_marker)
            if marker.get("url") != url or marker.get("status") != "EMPTY_HOUR":
                raise Bi5ValidationError(f"empty-hour marker mismatch: {empty_marker}")
            return hour, (), {
                "hour": hour,
                "hour_start_utc": hour_start.isoformat().replace("+00:00", "Z"),
                "url": url,
                "http_status": int(marker.get("http_status", 0)),
                "status": "EMPTY_HOUR",
                "acquisition": "VERIFIED_EXISTING_EMPTY_HOUR",
                "request_attempts": 0,
                "tick_count": 0,
                "headers": marker.get("headers", {}),
                "raw": None,
            }
        status, payload, headers, attempts = _fetch_with_retry(
            url, timeout=timeout, retries=retries, fetcher=fetcher
        )
        if status == 404 or not payload:
            write_json_atomic(
                empty_marker,
                {
                    "schema_version": "alphafactory_dukascopy_empty_hour.v1",
                    "authority": ALLOWED_AUTHORITY,
                    "status": "EMPTY_HOUR",
                    "symbol": symbol,
                    "hour_start_utc": hour_start.isoformat().replace("+00:00", "Z"),
                    "url": url,
                    "http_status": status,
                    "headers": headers,
                },
            )
            return hour, (), {
                "hour": hour,
                "hour_start_utc": hour_start.isoformat().replace("+00:00", "Z"),
                "url": url,
                "http_status": status,
                "status": "EMPTY_HOUR",
                "request_attempts": attempts,
                "tick_count": 0,
                "headers": headers,
                "raw": None,
            }
        decoded = decode_bi5(payload, symbol=symbol, hour_start=hour_start)
        _atomic_write(raw_path, payload)
        return hour, decoded.ticks, {
            "hour": hour,
            "hour_start_utc": hour_start.isoformat().replace("+00:00", "Z"),
            "url": url,
            "http_status": status,
            "status": "PASS",
            "request_attempts": attempts,
            "tick_count": decoded.count,
            "same_millisecond_pairs": decoded.same_millisecond_pairs,
            "zero_spread_quotes": decoded.zero_spread_quotes,
            "first_time_msc": decoded.first_time_msc,
            "last_time_msc": decoded.last_time_msc,
            "headers": headers,
            "raw": {
                "path": raw_path.resolve().as_posix(),
                "bytes": raw_path.stat().st_size,
                "sha256": sha256_file(raw_path),
            },
        }

    collected: list[tuple[int, tuple[Tick, ...], dict[str, object]]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(acquire_hour, hour) for hour in range(24)]
        for future in concurrent.futures.as_completed(futures):
            collected.append(future.result())
    collected.sort(key=lambda item: item[0])
    all_ticks = tuple(tick for _, ticks, _ in collected for tick in ticks)
    binary = write_day_binary(binary_path, all_ticks)
    hours = [receipt for _, _, receipt in collected]
    receipt: dict[str, object] = {
        "schema_version": "alphafactory_dukascopy_bi5_day.v2",
        "authority": ALLOWED_AUTHORITY,
        "economics_authorized": False,
        "performance_metrics_authorized": False,
        "redistribution_authorized": False,
        "status": "PASS",
        "symbol": symbol,
        "date_utc": source_day.isoformat(),
        "started_utc": started.isoformat().replace("+00:00", "Z"),
        "ended_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "geometry": {
            "divider": SYMBOL_GEOMETRY[symbol].divider,
            "digits": SYMBOL_GEOMETRY[symbol].digits,
            "provenance": SYMBOL_GEOMETRY[symbol].provenance,
        },
        "source_contract": {
            "path": contract_path.resolve().as_posix(),
            "sha256": contract_sha256,
        },
        "empty_hour_count": sum(1 for item in hours if item["status"] == "EMPTY_HOUR"),
        "tick_count": len(all_ticks),
        "same_millisecond_pairs": sum(
            int(item.get("same_millisecond_pairs", 0)) for item in hours
        ),
        "zero_spread_quotes": sum(int(item.get("zero_spread_quotes", 0)) for item in hours),
        "binary": binary,
        "hours": hours,
    }
    write_json_atomic(receipt_path, receipt)
    return receipt


def _contract(path: Path, expected_sha256: str) -> tuple[dict[str, object], str]:
    actual = sha256_file(path)
    if actual != expected_sha256.upper():
        raise Bi5ValidationError(
            f"source contract SHA256 mismatch: expected={expected_sha256} actual={actual}"
        )
    contract = load_strict_json(path)
    if (
        contract.get("schema_version") != "alphafactory_dukascopy_source_contract.v2"
        or contract.get("authority") != ALLOWED_AUTHORITY
        or contract.get("use_class") != "personal-noncommercial"
        or contract.get("redistribution_authorized") is not False
    ):
        raise Bi5ValidationError("source contract authority/use-class mismatch")
    return contract, actual


def download_contract(args: argparse.Namespace) -> int:
    contract_path = args.contract.resolve()
    contract, contract_sha256 = _contract(contract_path, args.contract_sha256)
    download = contract.get("download")
    symbols = contract.get("symbols")
    if not isinstance(download, dict) or not isinstance(symbols, list):
        raise Bi5ValidationError("source contract download/symbols missing")
    workers = int(download.get("workers", -1))
    retries = int(download.get("retries", -1))
    timeout = int(download.get("timeout_seconds", -1))
    if (workers, retries, timeout) != (args.workers, args.retries, args.timeout):
        raise Bi5ValidationError("CLI worker/retry/timeout values differ from frozen contract")

    output_root = args.output_root.resolve()
    selected = [
        item
        for item in symbols
        if not args.symbol
        or (isinstance(item, dict) and item.get("source_symbol") == args.symbol)
    ]
    if args.symbol and not selected:
        raise Bi5ValidationError(f"requested symbol is absent from contract: {args.symbol}")
    for item in selected:
        if not isinstance(item, dict):
            raise Bi5ValidationError("symbol contract row must be an object")
        symbol = str(item.get("source_symbol", "")).upper()
        from_day = parse_iso_date(str(item.get("history_from", "")))
        to_day_exclusive = parse_iso_date(str(item.get("history_to_exclusive", "")))
        if symbol not in SYMBOL_GEOMETRY or from_day >= to_day_exclusive:
            raise Bi5ValidationError(f"invalid frozen range for {symbol}")
        day = from_day
        while day < to_day_exclusive:
            receipt = acquire_day(
                symbol=symbol,
                source_day=day,
                root=output_root,
                timeout=timeout,
                retries=retries,
                workers=workers,
                contract_path=contract_path,
                contract_sha256=contract_sha256,
            )
            print(
                f"PASS {symbol} {day.isoformat()} ticks={receipt['tick_count']} "
                f"binary={receipt['binary']['sha256']}",
                flush=True,
            )
            day += timedelta(days=1)
    return 0


def probe(args: argparse.Namespace) -> int:
    symbol = args.symbol.upper()
    url = chunk_url(symbol, args.hour)
    status, payload, headers, attempts = _fetch_with_retry(
        url, timeout=args.timeout, retries=args.retries
    )
    if status != 200 or not payload:
        raise Bi5ValidationError(f"probe source hour is empty: {url} status={status}")
    result = decode_bi5(payload, symbol=symbol, hour_start=args.hour)
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    raw_path = output / f"{args.hour:%Y%m%d_%H}h_ticks.bi5"
    binary_path = output / f"{args.hour:%Y-%m-%d}.afdticks"
    _atomic_write(raw_path, payload)
    binary = write_day_binary(binary_path, result.ticks)
    receipt = {
        "schema_version": "alphafactory_dukascopy_bi5_probe.v2",
        "authority": ALLOWED_AUTHORITY,
        "economics_authorized": False,
        "performance_metrics_authorized": False,
        "redistribution_authorized": False,
        "status": "PASS",
        "symbol": symbol,
        "hour_start_utc": args.hour.isoformat().replace("+00:00", "Z"),
        "url": url,
        "http_status": status,
        "request_attempts": attempts,
        "headers": headers,
        "raw": {
            "path": raw_path.as_posix(),
            "bytes": raw_path.stat().st_size,
            "sha256": sha256_file(raw_path),
        },
        "decode": {
            "count": result.count,
            "same_millisecond_pairs": result.same_millisecond_pairs,
            "zero_spread_quotes": result.zero_spread_quotes,
            "first_time_msc": result.first_time_msc,
            "last_time_msc": result.last_time_msc,
            "day_binary": binary,
        },
    }
    write_json_atomic(output / "probe_receipt.json", receipt)
    print(json.dumps(receipt, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    one = subparsers.add_parser("probe", help="download and validate one UTC hour")
    one.add_argument("--symbol", required=True, choices=tuple(SYMBOL_GEOMETRY))
    one.add_argument("--hour", required=True, type=parse_hour)
    one.add_argument("--output-dir", required=True, type=Path)
    one.add_argument("--timeout", type=int, default=30)
    one.add_argument("--retries", type=int, default=3)
    one.set_defaults(handler=probe)

    full = subparsers.add_parser("download-contract", help="download the frozen ranges")
    full.add_argument("--contract", required=True, type=Path)
    full.add_argument("--contract-sha256", required=True)
    full.add_argument("--output-root", required=True, type=Path)
    full.add_argument("--workers", required=True, type=int)
    full.add_argument("--retries", required=True, type=int)
    full.add_argument("--timeout", required=True, type=int)
    full.add_argument("--symbol", choices=tuple(SYMBOL_GEOMETRY))
    full.set_defaults(handler=download_contract)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    sys.exit(main())
