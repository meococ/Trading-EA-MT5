#!/usr/bin/env python3
"""One-shot source-only builder for the official DOL UI seasonal residual.

Default execution is inert. The only network-enabled path requires both the
exact attempt id and a hash-bound reviewed run packet. No market-price source is
referenced anywhere in this module.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable, Mapping
from zoneinfo import ZoneInfo

from pypdf import PdfReader


HYPOTHESIS_ID = "HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001"
EA_NAME = "EA_DOLUISeasonalResidual"
ATTEMPT_ID = "DOLUI001-SOURCE-001"
FAMILY = "official-dol-ui-unadjusted-seasonal-residual"
ARCHIVE_FORM_URL = "https://oui.doleta.gov/unemploy/archive.asp"
CURRENT_RELEASE_URL = "https://www.dol.gov/ui/data.pdf"
ARCHIVE_CUTOFF = date(2026, 8, 6)
EXPECTED_YEAR_COUNTS = {
    2018: 52,
    2019: 51,
    2020: 53,
    2021: 52,
    2022: 52,
    2023: 52,
    2024: 52,
    2025: 46,
    2026: 31,
}
EXPECTED_STAGE_COUNTS = {
    "TRAIN_SOURCE": 260,
    "INTERNAL_VALIDATION_SOURCE": 104,
    "SEALED_HOLDOUT_SOURCE_ONLY": 77,
}
PLAN_REL = (
    "03. EA Developer/EA_DOLUISeasonalResidual/research/"
    "HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001_SOURCE_FEASIBILITY_PLAN.md"
)
SCRIPT_REL = (
    "03. EA Developer/EA_DOLUISeasonalResidual/research/build_dol_ui_source.py"
)
TEST_REL = (
    "03. EA Developer/EA_DOLUISeasonalResidual/research/tests/"
    "test_build_dol_ui_source.py"
)
REVIEW_REL = (
    "03. EA Developer/EA_DOLUISeasonalResidual/research/"
    "HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001_PRE_SOURCE_REVIEW.md"
)
PACKET_REL = (
    "03. EA Developer/EA_DOLUISeasonalResidual/research/"
    "HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001_SOURCE_RUN_PACKET.json"
)
EVIDENCE_REL = (
    "03. EA Developer/EA_DOLUISeasonalResidual/research/evidence/"
    f"{HYPOTHESIS_ID}/{ATTEMPT_ID}"
)
RAW_REL = f"02. AlphaFactory/external/dol_ui/{HYPOTHESIS_ID}/raw/{ATTEMPT_ID}"
DATA_REL = f"02. AlphaFactory/data/dol_ui/{HYPOTHESIS_ID}"
USER_AGENT = "AlphaFactory-DOLUI-SourceProbe/1.0"
NY = ZoneInfo("America/New_York")
UTC = timezone.utc

ARCHIVE_LINK_RE = re.compile(
    r'href=["\'](?P<href>/press/(?P<year>\d{4})/(?P<stamp>\d{6})\.pdf)["\']',
    re.IGNORECASE,
)
HEADER_RE = re.compile(
    r"(?:EMBARGOED\s+UNTIL|RELEASED\s+AT)\s*8:30\s*A\.?\s*M\.?\s*"
    r"\(Eastern\)\s*(?:Monday|Tuesday|Wednesday|Thursday|Friday)\s*,?\s*"
    r"(?P<date>[A-Za-z]+\s+\d{1,2},\s+\d{4})",
    re.IGNORECASE,
)
SA_RE = re.compile(
    r"advance figure for seasonally adjusted initial claims was\s+(?P<level>[\d,]+),\s*"
    r"(?:(?P<kind>an? increase|a decrease) of\s+(?P<change>[\d,]+)|"
    r"(?P<unchanged>unchanged))\s+from the previous week's\s+"
    r"(?P<status>revised|unrevised)\s+(?:level|figure)",
    re.IGNORECASE,
)
NSA_RE = re.compile(
    r"advance\s+(?:unadjusted\s+)?number of actual initial claims under state programs,\s*"
    r"unadjusted,\s*total(?:ed)?\s+(?P<total>[\d,]+)\s+in the week ending\s+"
    r"(?P<week>[A-Za-z]+\s+\d{1,2}),\s*"
    r"(?:(?P<kind>an? increase|a decrease) of\s+(?P<change>[\d,]+)|"
    r"(?P<unchanged>unchanged))",
    re.IGNORECASE,
)
EXPECTED_RE = re.compile(
    r"seasonal factors had expected\s+"
    r"(?:(?P<kind>an? increase|a decrease) of\s+(?P<change>[\d,]+)|"
    r"(?P<zero>no change))",
    re.IGNORECASE,
)
REVISION_RE = re.compile(
    r"previous week's (?:level|figure) was revised\s+(?P<kind>up|down)\s+by\s+"
    r"(?P<delta>[\d,]+)\s+from\s+(?P<old>[\d,]+)\s+to\s+(?P<new>[\d,]+)",
    re.IGNORECASE,
)


class ContractError(RuntimeError):
    """Fail-closed source contract violation."""


@dataclass(frozen=True)
class DownloadedPdf:
    url: str
    payload: bytes
    sha256: str
    byte_count: int
    network_used: bool


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\u2013", "-").replace("\u2212", "-")).strip()


def archive_request_body(year: int) -> bytes:
    if year not in EXPECTED_YEAR_COUNTS:
        raise ContractError(f"year outside frozen archive range: {year}")
    return urllib.parse.urlencode(
        {"report": "press", "year": str(year), "submit": "Submit"}
    ).encode("ascii")


def release_date_from_url(url: str) -> date:
    match = re.search(r"/press/(?P<year>\d{4})/(?P<stamp>\d{6})\.pdf$", url, re.I)
    if not match:
        raise ContractError(f"invalid official archive PDF URL: {url}")
    year = int(match.group("year"))
    stamp = match.group("stamp")
    try:
        return date(year, int(stamp[:2]), int(stamp[2:4]))
    except ValueError as exc:
        raise ContractError(f"invalid archive date components: {url}") from exc


def filename_year_suffix_matches_path(url: str) -> bool:
    match = re.search(r"/press/(?P<year>\d{4})/(?P<stamp>\d{6})\.pdf$", url, re.I)
    if not match:
        raise ContractError(f"invalid official archive PDF URL: {url}")
    return int(match.group("stamp")[4:]) == int(match.group("year")) % 100


def discover_archive_urls(year: int, fetch: Callable[[urllib.request.Request], bytes]) -> list[str]:
    request = urllib.request.Request(
        ARCHIVE_FORM_URL,
        data=archive_request_body(year),
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    payload = fetch(request)
    try:
        html = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        html = payload.decode("windows-1252", errors="strict")
    urls: set[str] = set()
    for match in ARCHIVE_LINK_RE.finditer(html):
        if int(match.group("year")) != year:
            continue
        url = "https://oui.doleta.gov" + match.group("href")
        if release_date_from_url(url) <= ARCHIVE_CUTOFF:
            urls.add(url)
    return sorted(urls, key=release_date_from_url)


def _signed(kind: str | None, raw_value: str | None, unchanged: str | None = None) -> int:
    if unchanged:
        return 0
    if not kind or not raw_value:
        raise ContractError("missing signed-change components")
    value = int(raw_value.replace(",", ""))
    lowered = kind.lower()
    if "increase" in lowered or lowered == "up":
        return value
    if "decrease" in lowered or lowered == "down":
        return -value
    raise ContractError(f"unknown signed-change kind: {kind}")


def _claims_week_date(month_day: str, release_date: date) -> date:
    candidate = datetime.strptime(f"{month_day}, {release_date.year}", "%B %d, %Y").date()
    if candidate > release_date:
        candidate = candidate.replace(year=candidate.year - 1)
    lag = (release_date - candidate).days
    if lag < 0 or lag > 14:
        raise ContractError(f"claims week/release lag outside 0..14 days: {lag}")
    return candidate


def extract_pdf_text(payload: bytes) -> tuple[str, int]:
    if not payload.startswith(b"%PDF-"):
        raise ContractError("source payload is not a PDF")
    reader = PdfReader(io.BytesIO(payload))
    if not reader.pages:
        raise ContractError("PDF has zero pages")
    text = " ".join((page.extract_text() or "") for page in reader.pages[:3])
    text = normalize_text(text)
    if not text:
        raise ContractError("PDF text extraction returned empty text")
    return text, len(reader.pages)


def stage_for_release(release_date: date) -> str:
    if release_date.year <= 2022:
        return "TRAIN_SOURCE"
    if release_date.year <= 2024:
        return "INTERNAL_VALIDATION_SOURCE"
    return "SEALED_HOLDOUT_SOURCE_ONLY"


def parse_release_text(text: str, *, url: str, pdf_sha256: str, byte_count: int, pages: int) -> dict[str, object]:
    normalized = normalize_text(text)
    url_date = release_date_from_url(url)
    header = HEADER_RE.search(normalized)
    sa = SA_RE.search(normalized)
    nsa = NSA_RE.search(normalized)
    expected = EXPECTED_RE.search(normalized)
    if not all((header, sa, nsa, expected)):
        missing = [
            name
            for name, value in (("header", header), ("sa", sa), ("nsa", nsa), ("expected", expected))
            if value is None
        ]
        raise ContractError(f"missing core PDF fields: {','.join(missing)}")

    parsed_release = datetime.strptime(header.group("date"), "%B %d, %Y").date()
    if parsed_release != url_date:
        raise ContractError(f"PDF/URL release-date mismatch: {parsed_release} != {url_date}")
    local_dt = datetime.combine(parsed_release, datetime.min.time(), tzinfo=NY).replace(
        hour=8, minute=30
    )
    release_utc = local_dt.astimezone(UTC)
    claims_week = _claims_week_date(nsa.group("week"), parsed_release)

    sa_change = _signed(sa.group("kind"), sa.group("change"), sa.group("unchanged"))
    nsa_change = _signed(nsa.group("kind"), nsa.group("change"), nsa.group("unchanged"))
    expected_change = _signed(
        expected.group("kind"), expected.group("change"), expected.group("zero")
    )
    residual = nsa_change - expected_change
    direction = "BUY_EURUSD" if residual > 0 else "SELL_EURUSD" if residual < 0 else "FLAT"

    revision = REVISION_RE.search(normalized)
    revision_delta = 0
    revision_old = None
    revision_new = None
    if revision:
        revision_delta = _signed(revision.group("kind"), revision.group("delta"))
        revision_old = int(revision.group("old").replace(",", ""))
        revision_new = int(revision.group("new").replace(",", ""))
        if revision_new - revision_old != revision_delta:
            raise ContractError("stated revision delta conflicts with old/new levels")
    if sa.group("status").lower() == "revised" and revision is None:
        raise ContractError("revised prior level lacks explicit revision lineage")

    return {
        "schema_version": "alphafactory.dol_ui_seasonal_residual_source.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "stage": stage_for_release(parsed_release),
        "source_url": url,
        "source_sha256": pdf_sha256,
        "source_bytes": byte_count,
        "source_pages": pages,
        "filename_year_suffix_matches_path": filename_year_suffix_matches_path(url),
        "release_date": parsed_release.isoformat(),
        "release_time_local": local_dt.isoformat(),
        "release_timezone": local_dt.tzname(),
        "release_utc": release_utc.isoformat().replace("+00:00", "Z"),
        "claims_week_ending": claims_week.isoformat(),
        "sa_initial_claims_first_public": int(sa.group("level").replace(",", "")),
        "sa_initial_claims_change": sa_change,
        "prior_level_status": sa.group("status").lower(),
        "prior_revision_delta": revision_delta,
        "prior_revision_old": revision_old,
        "prior_revision_new": revision_new,
        "nsa_initial_claims_first_public": int(nsa.group("total").replace(",", "")),
        "nsa_actual_change": nsa_change,
        "seasonal_expected_change": expected_change,
        "seasonal_residual": residual,
        "direction": direction,
    }


def _urlopen_bytes(request: urllib.request.Request, timeout: int = 45) -> bytes:
    last_error: Exception | None = None
    for _ in range(3):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except Exception as exc:  # transport retry is bounded inside one attempt
            last_error = exc
    raise ContractError(f"network request failed after 3 tries: {request.full_url}: {last_error}")


def _download_pdf(url: str, cache_path: Path) -> DownloadedPdf:
    if cache_path.exists():
        raise ContractError(f"unbound raw cache exists before download: {cache_path}")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    payload = _urlopen_bytes(request)
    if not payload.startswith(b"%PDF-"):
        raise ContractError(f"downloaded payload is not PDF: {url}")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = cache_path.with_suffix(".pdf.partial")
    temp_path.write_bytes(payload)
    os.replace(temp_path, cache_path)
    return DownloadedPdf(url, payload, sha256_bytes(payload), len(payload), True)


def evaluate_source_gates(rows: list[dict[str, object]], year_counts: Mapping[int, int]) -> dict[str, bool]:
    stage_counts = {stage: sum(row["stage"] == stage for row in rows) for stage in EXPECTED_STAGE_COUNTS}
    train = [row for row in rows if row["stage"] == "TRAIN_SOURCE"]
    nonzero_train = [row for row in train if row["direction"] != "FLAT"]
    nonzero_all = [row for row in rows if row["direction"] != "FLAT"]
    buy_share = (
        sum(row["direction"] == "BUY_EURUSD" for row in nonzero_train) / len(nonzero_train)
        if nonzero_train
        else 0.0
    )
    sell_share = (
        sum(row["direction"] == "SELL_EURUSD" for row in nonzero_train) / len(nonzero_train)
        if nonzero_train
        else 0.0
    )
    train_year_counts = {
        year: sum(str(row["release_date"]).startswith(str(year)) for row in train)
        for year in range(2018, 2023)
    }
    max_year_share = max(train_year_counts.values(), default=0) / len(train) if train else 1.0
    return {
        "archive_counts_exact": dict(year_counts) == EXPECTED_YEAR_COUNTS,
        "total_rows_exact_441": len(rows) == 441,
        "unique_source_urls": len({row["source_url"] for row in rows}) == len(rows),
        "unique_release_utc": len({row["release_utc"] for row in rows}) == len(rows),
        "unique_claims_week": len({row["claims_week_ending"] for row in rows}) == len(rows),
        "stage_counts_exact": stage_counts == EXPECTED_STAGE_COUNTS,
        "nonzero_residual_coverage_ge_95pct": len(nonzero_all) / len(rows) >= 0.95 if rows else False,
        "train_buy_share_ge_20pct": buy_share >= 0.20,
        "train_sell_share_ge_20pct": sell_share >= 0.20,
        "train_max_year_share_le_22pct": max_year_share <= 0.22,
        "zero_target_outcome_reads": True,
        "zero_paid_requests": True,
    }


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(value) + b"\n")


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as stream:
        for row in rows:
            stream.write(canonical_json(dict(row)) + b"\n")


CSV_FIELDS = [
    "release_utc",
    "release_time_local",
    "release_timezone",
    "release_date",
    "claims_week_ending",
    "sa_initial_claims_first_public",
    "sa_initial_claims_change",
    "prior_level_status",
    "prior_revision_delta",
    "nsa_initial_claims_first_public",
    "nsa_actual_change",
    "seasonal_expected_change",
    "seasonal_residual",
    "direction",
    "stage",
    "source_url",
    "source_sha256",
]


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[3]


def validate_run_packet(root: Path, packet_path: Path) -> dict[str, object]:
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    required = {
        "schema_version": "alphafactory.dol_ui_source_run_packet.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "source_run_authorized": True,
        "network_authorized": True,
        "paid_requests_authorized": False,
        "outcome_prices_authorized": False,
        "economics_authorized": False,
        "mql5_authorized": False,
        "mt5_authorized": False,
    }
    for key, expected in required.items():
        if packet.get(key) != expected:
            raise ContractError(f"run packet field mismatch: {key}")
    bindings = packet.get("bindings")
    if not isinstance(bindings, dict):
        raise ContractError("run packet bindings missing")
    for rel in (PLAN_REL, SCRIPT_REL, TEST_REL, REVIEW_REL):
        expected_hash = bindings.get(rel)
        if not isinstance(expected_hash, str) or expected_hash != sha256_path(root / rel):
            raise ContractError(f"run packet hash mismatch: {rel}")
    return packet


def execute_source_attempt(root: Path, packet_path: Path, workers: int) -> dict[str, object]:
    validate_run_packet(root, packet_path)
    evidence_root = root / EVIDENCE_REL
    if evidence_root.exists():
        raise ContractError(f"attempt already claimed: {evidence_root}")
    evidence_root.mkdir(parents=True)
    started = {
        "schema_version": "alphafactory.source_attempt_started.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "started_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "authority": "SOURCE_FEASIBILITY_ONLY",
        "archive_cutoff": ARCHIVE_CUTOFF.isoformat(),
        "outcome_prices_authorized": False,
        "paid_requests_authorized": False,
    }
    _write_json(evidence_root / "attempt_started.json", started)

    try:
        urls: list[str] = []
        year_counts: dict[int, int] = {}
        for year in EXPECTED_YEAR_COUNTS:
            found = discover_archive_urls(year, _urlopen_bytes)
            year_counts[year] = len(found)
            urls.extend(found)
        if len(urls) != len(set(urls)):
            raise ContractError("archive returned duplicate PDF URLs")

        raw_root = root / RAW_REL
        if raw_root.exists():
            raise ContractError(f"attempt raw root already exists and is unbound: {raw_root}")
        downloads: list[DownloadedPdf] = []
        with ThreadPoolExecutor(max_workers=max(1, min(workers, 12))) as pool:
            futures = {
                pool.submit(
                    _download_pdf,
                    url,
                    raw_root / str(release_date_from_url(url).year) / url.rsplit("/", 1)[-1],
                ): url
                for url in urls
            }
            for future in as_completed(futures):
                downloads.append(future.result())

        rows: list[dict[str, object]] = []
        for item in downloads:
            text, pages = extract_pdf_text(item.payload)
            rows.append(
                parse_release_text(
                    text,
                    url=item.url,
                    pdf_sha256=item.sha256,
                    byte_count=item.byte_count,
                    pages=pages,
                )
            )
        rows.sort(key=lambda row: str(row["release_utc"]))

        gates = evaluate_source_gates(rows, year_counts)
        gates["all_pdfs_downloaded_in_attempt"] = (
            len(downloads) == len(urls) and all(item.network_used for item in downloads)
        )
        stage_counts = {stage: sum(row["stage"] == stage for row in rows) for stage in EXPECTED_STAGE_COUNTS}
        direction_counts = {
            direction: sum(row["direction"] == direction for row in rows)
            for direction in ("BUY_EURUSD", "SELL_EURUSD", "FLAT")
        }
        verdict = "PASS_SOURCE_FEASIBILITY" if all(gates.values()) else "SOURCE_FAIL_NO_ECONOMICS_AUTHORITY"

        ledger_path = evidence_root / "dol_ui_source_ledger.jsonl"
        report_path = evidence_root / "source_report.json"
        receipt_path = evidence_root / "source_feasibility_receipt.json"
        csv_path = root / DATA_REL / "dol_ui_seasonal_residual_2018_20260806.csv"
        manifest_path = root / DATA_REL / "manifest.json"
        _write_jsonl(ledger_path, rows)
        _write_csv(csv_path, rows)

        report = {
            "schema_version": "alphafactory.dol_ui_source_report.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "verdict": verdict,
            "archive_cutoff": ARCHIVE_CUTOFF.isoformat(),
            "source_cost_usd": 0.0,
            "year_counts": year_counts,
            "stage_counts": stage_counts,
            "direction_counts": direction_counts,
            "rows": len(rows),
            "network_pdf_downloads": sum(item.network_used for item in downloads),
            "cached_pdf_reads": sum(not item.network_used for item in downloads),
            "archive_post_requests": len(EXPECTED_YEAR_COUNTS),
            "gates": gates,
            "forbidden_counters": {
                "target_price_rows_read": 0,
                "returns_computed": 0,
                "trades_simulated": 0,
                "performance_trials": 0,
                "mql5_files_created": 0,
                "mt5_launches": 0,
                "paid_requests": 0,
            },
        }
        _write_json(report_path, report)

        manifest = {
            "schema_version": "alphafactory.dol_ui_static_source_manifest.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "archive_cutoff": ARCHIVE_CUTOFF.isoformat(),
            "official_archive_form": "https://oui.doleta.gov/unemploy/claims_arch.asp",
            "official_archive_post": ARCHIVE_FORM_URL,
            "official_current_release": CURRENT_RELEASE_URL,
            "row_count": len(rows),
            "csv_path": csv_path.relative_to(root).as_posix(),
            "csv_sha256": sha256_path(csv_path),
            "ledger_path": ledger_path.relative_to(root).as_posix(),
            "ledger_sha256": sha256_path(ledger_path),
            "raw_cache_path": raw_root.relative_to(root).as_posix(),
            "raw_pdf_count": len(downloads),
            "raw_pdf_total_bytes": sum(item.byte_count for item in downloads),
            "raw_pdf_hashes_sha256": sha256_bytes(
                canonical_json(sorted((item.url, item.sha256, item.byte_count) for item in downloads))
            ),
            "source_only": True,
            "economic_valid": False,
            "promotion_eligible": False,
        }
        _write_json(manifest_path, manifest)

        receipt = {
            "schema_version": "alphafactory.dol_ui_source_receipt.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "verdict": verdict,
            "packet_path": packet_path.relative_to(root).as_posix(),
            "packet_sha256": sha256_path(packet_path),
            "report_path": report_path.relative_to(root).as_posix(),
            "report_sha256": sha256_path(report_path),
            "ledger_path": ledger_path.relative_to(root).as_posix(),
            "ledger_sha256": sha256_path(ledger_path),
            "manifest_path": manifest_path.relative_to(root).as_posix(),
            "manifest_sha256": sha256_path(manifest_path),
            "csv_path": csv_path.relative_to(root).as_posix(),
            "csv_sha256": sha256_path(csv_path),
            "all_source_gates_passed": all(gates.values()),
            "economic_edge_evaluated": False,
            "economic_valid": False,
            "promotion_eligible": False,
        }
        _write_json(receipt_path, receipt)
        terminal = {
            "schema_version": "alphafactory.source_attempt_terminal.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "status": "COMPLETED",
            "verdict": verdict,
            "completed_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "receipt_path": receipt_path.relative_to(root).as_posix(),
            "receipt_sha256": sha256_path(receipt_path),
        }
        _write_json(evidence_root / "attempt_terminal.json", terminal)
        return report
    except Exception as exc:
        terminal = {
            "schema_version": "alphafactory.source_attempt_terminal.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "status": "FAILED",
            "verdict": "SOURCE_ATTEMPT_FAILED_NO_ECONOMICS_AUTHORITY",
            "completed_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        _write_json(evidence_root / "attempt_terminal.json", terminal)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-source-attempt", action="store_true")
    parser.add_argument("--attempt-id")
    parser.add_argument("--packet", default=PACKET_REL)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args(argv)
    if not args.execute_source_attempt:
        parser.print_help()
        return 0
    if args.attempt_id != ATTEMPT_ID:
        raise ContractError("exact attempt id required")
    root = _workspace_root()
    packet_path = (root / args.packet).resolve()
    if root.resolve() not in packet_path.parents:
        raise ContractError("packet path escapes workspace")
    report = execute_source_attempt(root, packet_path, args.workers)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["verdict"] == "PASS_SOURCE_FEASIBILITY" else 2


if __name__ == "__main__":
    sys.exit(main())
