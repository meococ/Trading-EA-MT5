"""Outcome-blind source validation for MTS005 Jetta H1 bars."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import struct
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOWNLOADER = ROOT / "tools" / "research" / "dukascopy_jetta_h1.py"
spec = importlib.util.spec_from_file_location("mts005_jetta", DOWNLOADER)
if not spec or not spec.loader:
    raise RuntimeError(f"cannot load Jetta source tool: {DOWNLOADER}")
source = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = source
spec.loader.exec_module(source)


AFRATE_HEADER = struct.Struct("<QQ")
AFRATE_RECORD = struct.Struct("<qddddqiq")
AFRATE_MAGIC = 0x4146524154453100
AUTHORITY = "SOURCE_DATA_ONLY_NO_PERFORMANCE"


class SourceValidationError(RuntimeError):
    pass


def load_rates(path: Path) -> list[source.H1Bar]:
    bars: list[source.H1Bar] = []
    with path.open("rb") as handle:
        magic, count = AFRATE_HEADER.unpack(handle.read(AFRATE_HEADER.size))
        if magic != AFRATE_MAGIC:
            raise SourceValidationError(f"AFRATE1 magic mismatch: {path}")
        for index in range(count):
            payload = handle.read(AFRATE_RECORD.size)
            if len(payload) != AFRATE_RECORD.size:
                raise SourceValidationError(f"AFRATE1 truncated row {index}: {path}")
            epoch, open_, high, low, close, volume, _spread, _real = AFRATE_RECORD.unpack(payload)
            bars.append(source.H1Bar(epoch, open_, high, low, close, volume))
        if handle.read(1):
            raise SourceValidationError(f"AFRATE1 trailing data: {path}")
    return bars


def annual_d1_url(code: str, year: int, *, partial: bool) -> str:
    if partial:
        epoch_msc = int(datetime(year, 1, 1, tzinfo=timezone.utc).timestamp()) * 1000
        return f"{source.BASE_URL}/candles/trade/day/{code}/BID?from={epoch_msc}"
    return f"{source.BASE_URL}/candles/trade/day/{code}/BID/{year}"


def fetch_json(url: str, limiter: source.HostRateLimiter, timeout: int = 45) -> bytes:
    last = "unknown"
    for attempt in range(1, 5):
        limiter.wait()
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "AlphaFactory-MTS005-source-validation/1.0",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            last = f"HTTP {exc.code}"
            if exc.code in {429, 503}:
                limiter.penalize(min(60.0, 15.0 * attempt))
            elif 400 <= exc.code < 500:
                raise SourceValidationError(f"non-retryable {last}: {url}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = str(exc)
        time.sleep(min(10.0, float(attempt)))
    raise SourceValidationError(f"D1 download failed: {url}: {last}")


def aggregate_session(rows: list[source.H1Bar]) -> tuple[float, float, float, float]:
    if not rows:
        raise SourceValidationError("cannot aggregate an empty D1 session")
    return (
        rows[0].open,
        max(row.high for row in rows),
        min(row.low for row in rows),
        rows[-1].close,
    )


def compare_sessions(
    h1: list[source.H1Bar],
    d1: list[source.H1Bar],
    point: float,
    contract_start: int,
    contract_end: int,
) -> dict[str, object]:
    if len(d1) < 2:
        raise SourceValidationError("official D1 series has fewer than two boundaries")
    h1_index = 0
    common = 0
    within_one_point = 0
    exact = 0
    missing_sessions = 0
    maximum_error_points = 0.0
    mismatch_samples: list[dict[str, object]] = []
    for index in range(len(d1) - 1):
        start = d1[index].time
        end = d1[index + 1].time
        if start < contract_start or end > contract_end or end <= start:
            continue
        while h1_index < len(h1) and h1[h1_index].time < start:
            h1_index += 1
        cursor = h1_index
        session: list[source.H1Bar] = []
        while cursor < len(h1) and h1[cursor].time < end:
            session.append(h1[cursor])
            cursor += 1
        if not session:
            missing_sessions += 1
            continue
        h1_index = cursor
        observed = aggregate_session(session)
        expected = (d1[index].open, d1[index].high, d1[index].low, d1[index].close)
        errors = [abs(left - right) / point for left, right in zip(observed, expected)]
        max_error = max(errors)
        maximum_error_points = max(maximum_error_points, max_error)
        common += 1
        if max_error <= 1e-6:
            exact += 1
        if max_error <= 1.0 + 1e-6:
            within_one_point += 1
        elif len(mismatch_samples) < 20:
            mismatch_samples.append(
                {
                    "session_start_epoch": start,
                    "session_end_epoch": end,
                    "observed_h1_ohlc": observed,
                    "official_d1_ohlc": expected,
                    "errors_points": errors,
                }
            )
    if common < 1:
        raise SourceValidationError("no common official D1 sessions")
    match_rate = within_one_point / common
    return {
        "common_sessions": common,
        "missing_official_sessions_without_h1": missing_sessions,
        "exact_ohlc_sessions": exact,
        "within_one_point_sessions": within_one_point,
        "within_one_point_rate": match_rate,
        "maximum_error_points": maximum_error_points,
        "mismatch_samples": mismatch_samples,
        "status": "PASS" if match_rate >= 0.995 else "FAIL",
    }


def load_symbol_h1(data_root: Path, symbol: str, contract_sha: str) -> list[source.H1Bar]:
    receipts = sorted((data_root / "receipts" / symbol).glob("*/*.json"))
    if not receipts:
        raise SourceValidationError(f"no source receipts for {symbol}")
    result: list[source.H1Bar] = []
    previous = 0
    for receipt_path in receipts:
        receipt = source.load_json(receipt_path)
        binary = receipt.get("binary")
        binding = receipt.get("source_contract")
        if (
            receipt.get("status") != "PASS"
            or receipt.get("symbol") != symbol
            or not isinstance(binary, dict)
            or not isinstance(binding, dict)
            or binding.get("sha256") != contract_sha
        ):
            raise SourceValidationError(f"receipt identity mismatch: {receipt_path}")
        binary_path = Path(str(binary["path"]))
        if not binary_path.is_file() or source.sha256_file(binary_path) != binary.get("sha256"):
            raise SourceValidationError(f"binary hash mismatch: {receipt_path}")
        rows = load_rates(binary_path)
        if rows[0].time <= previous:
            raise SourceValidationError(f"source month order overlap: {receipt_path}")
        result.extend(rows)
        previous = rows[-1].time
    return result


def validate(args: argparse.Namespace) -> int:
    contract, contract_sha = source.validate_contract(args.contract, args.contract_sha256)
    rows = contract["symbols"]
    assert isinstance(rows, list)
    limiter = source.HostRateLimiter(source.MIN_REQUEST_INTERVAL_SECONDS)
    output_root = args.output.resolve()
    symbol_results: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise SourceValidationError("invalid symbol contract row")
        symbol = str(row["source_symbol"])
        code = str(row["jetta_code"])
        point = 10.0 ** (-int(row["digits"]))
        start_day = date.fromisoformat(str(row["history_from"]))
        end_day = date.fromisoformat(str(row["history_to_exclusive"]))
        contract_start = int(datetime.combine(start_day, datetime.min.time(), tzinfo=timezone.utc).timestamp())
        contract_end = int(datetime.combine(end_day, datetime.min.time(), tzinfo=timezone.utc).timestamp())
        h1 = load_symbol_h1(args.data_root.resolve(), symbol, contract_sha)
        d1_rows: list[source.H1Bar] = []
        raw_bindings: list[dict[str, object]] = []
        for year in range(start_day.year, end_day.year + 1):
            partial = year == end_day.year and end_day < date(year + 1, 1, 1)
            url = annual_d1_url(code, year, partial=partial)
            payload = fetch_json(url, limiter)
            raw_path = output_root / "raw_d1" / symbol / f"{year}.json"
            source.atomic_write(raw_path, payload)
            stats: dict[str, int] = {}
            decoded = source.decode_h1(
                payload,
                f"{symbol} D1 {year}",
                point=point,
                normalization_stats=stats,
            )
            d1_rows.extend(decoded)
            raw_bindings.append(
                {
                    "year": year,
                    "url": url,
                    "path": raw_path.as_posix(),
                    "sha256": source.sha256_bytes(payload),
                    "bytes": len(payload),
                    "one_point_envelope_corrections": stats.get(
                        "one_point_envelope_corrections", 0
                    ),
                }
            )
        unique_d1 = {row.time: row for row in d1_rows}
        comparison = compare_sessions(
            h1,
            [unique_d1[key] for key in sorted(unique_d1)],
            point,
            contract_start,
            contract_end,
        )
        symbol_results.append(
            {
                "symbol": symbol,
                "h1_bar_count": len(h1),
                "official_d1_raw": raw_bindings,
                "comparison": comparison,
            }
        )
        print(
            f"{comparison['status']} {symbol} common={comparison['common_sessions']} "
            f"match_rate={comparison['within_one_point_rate']:.6f}",
            flush=True,
        )
    passed = all(row["comparison"]["status"] == "PASS" for row in symbol_results)
    payload = {
        "schema_version": "mts005_jetta_h1_source_validation.v1",
        "hypothesis_id": "HYP-MULTI-TSMOM-D1-005",
        "authority": AUTHORITY,
        "status": "PASS" if passed else "FAIL",
        "source_contract_sha256": contract_sha,
        "acceptance_threshold": 0.995,
        "comparison_clock": "provider session-anchored D1 boundaries, not UTC signal days",
        "symbols": symbol_results,
        "economics_authorized": False,
        "performance_metrics_authorized": False,
    }
    result_path = output_root / "HYP-MULTI-TSMOM-D1-005_SOURCE_VALIDATION.json"
    source.write_json_atomic(result_path, payload)
    print(f"RESULT {result_path} sha256={source.sha256_file(result_path)}", flush=True)
    return 0 if passed else 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate MTS005 Jetta H1 source")
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-sha256", required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        return validate(build_parser().parse_args(argv))
    except (SourceValidationError, source.JettaH1Error) as exc:
        print(f"FATAL {exc}", flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
