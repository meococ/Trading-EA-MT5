"""Source-only DOL UI census revision 002.

This wrapper preserves the hash-bound revision-001 builder and changes only the
outcome-blind parser contract documented in SOURCE_REVISION_002. Execution is
still inert unless the exact attempt id and reviewed run packet are supplied.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Mapping


CORE_REL = "03. EA Developer/EA_DOLUISeasonalResidual/research/build_dol_ui_source.py"
PLAN_REL = (
    "03. EA Developer/EA_DOLUISeasonalResidual/research/"
    "HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001_SOURCE_REVISION_002.md"
)
SCRIPT_REL = "03. EA Developer/EA_DOLUISeasonalResidual/research/build_dol_ui_source_v2.py"
TEST_REL = (
    "03. EA Developer/EA_DOLUISeasonalResidual/research/tests/"
    "test_build_dol_ui_source_v2.py"
)
REVIEW_REL = (
    "03. EA Developer/EA_DOLUISeasonalResidual/research/"
    "HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001_PRE_SOURCE_REVIEW_002.md"
)
PACKET_REL = (
    "03. EA Developer/EA_DOLUISeasonalResidual/research/"
    "HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001_SOURCE_RUN_PACKET_002.json"
)
ATTEMPT_ID = "DOLUI001-SOURCE-002"
MISSING_EXPECTED_URLS = frozenset(
    {
        "https://oui.doleta.gov/press/2020/090320.pdf",
        "https://oui.doleta.gov/press/2020/091020.pdf",
    }
)

core_path = Path(__file__).with_name("build_dol_ui_source.py")
spec = importlib.util.spec_from_file_location("dolui_source_v1_frozen", core_path)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load frozen source builder")
core = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = core
spec.loader.exec_module(core)

core.ATTEMPT_ID = ATTEMPT_ID
core.PLAN_REL = PLAN_REL
core.SCRIPT_REL = SCRIPT_REL
core.TEST_REL = TEST_REL
core.REVIEW_REL = REVIEW_REL
core.PACKET_REL = PACKET_REL
core.EVIDENCE_REL = (
    "03. EA Developer/EA_DOLUISeasonalResidual/research/evidence/"
    f"{core.HYPOTHESIS_ID}/{ATTEMPT_ID}"
)
core.RAW_REL = f"02. AlphaFactory/external/dol_ui/{core.HYPOTHESIS_ID}/raw/{ATTEMPT_ID}"
core.USER_AGENT = "AlphaFactory-DOLUI-SourceProbe/2.0"
original_normalize_text = core.normalize_text

SA_RE = re.compile(
    r"advance figure for seasonally adjusted initial claims was\s+(?P<level>[\d,]+),\s*"
    r"(?:(?P<kind>an? increase|a decrease) of\s+(?P<change>[\d,]+)|"
    r"(?P<unchanged>unchanged))\s+from (?:the )?previous week's\s+"
    r"(?:(?P<status>revised|unrevised)\s+)?(?:level|figure)",
    re.IGNORECASE,
)


def normalize_text(value: str) -> str:
    text = original_normalize_text(value)
    text = re.sub(r"\b(?:a\s+dvance|adv\s+ance)\b", "advance", text, flags=re.I)
    text = re.sub(r"\bpre\s+vious\b", "previous", text, flags=re.I)

    def join_grouped_integer(match: re.Match[str]) -> str:
        return re.sub(r"\s+", "", match.group(0))

    return re.sub(
        r"\b\d{1,3}(?:\s+\d{1,3})?,(?:\d{1,3}(?:\s+\d{1,3})*)\b",
        join_grouped_integer,
        text,
    )


def parse_release_text(
    text: str,
    *,
    url: str,
    pdf_sha256: str,
    byte_count: int,
    pages: int,
) -> dict[str, object]:
    normalized = normalize_text(text)
    url_date = core.release_date_from_url(url)
    header = core.HEADER_RE.search(normalized)
    sa = SA_RE.search(normalized)
    nsa = core.NSA_RE.search(normalized)
    expected = core.EXPECTED_RE.search(normalized)
    if not all((header, sa, nsa)):
        missing = [
            name
            for name, value in (("header", header), ("sa", sa), ("nsa", nsa))
            if value is None
        ]
        raise core.ContractError(f"missing core PDF fields: {','.join(missing)}")
    if expected is None and url not in MISSING_EXPECTED_URLS:
        raise core.ContractError("missing expected field outside frozen exception set")
    if expected is not None and url in MISSING_EXPECTED_URLS:
        raise core.ContractError("expected field appeared at frozen missing-source URL")

    parsed_release = datetime.strptime(header.group("date"), "%B %d, %Y").date()
    if parsed_release != url_date:
        raise core.ContractError(f"PDF/URL release-date mismatch: {parsed_release} != {url_date}")
    local_dt = datetime.combine(
        parsed_release, datetime.min.time(), tzinfo=core.NY
    ).replace(hour=8, minute=30)
    release_utc = local_dt.astimezone(core.UTC)
    claims_week = core._claims_week_date(nsa.group("week"), parsed_release)

    sa_change = core._signed(sa.group("kind"), sa.group("change"), sa.group("unchanged"))
    nsa_change = core._signed(nsa.group("kind"), nsa.group("change"), nsa.group("unchanged"))
    if expected is None:
        expected_change = None
        residual = None
        direction = "FLAT"
        availability = "EXPECTED_NOT_PUBLISHED"
    else:
        expected_change = core._signed(
            expected.group("kind"), expected.group("change"), expected.group("zero")
        )
        residual = nsa_change - expected_change
        direction = "BUY_EURUSD" if residual > 0 else "SELL_EURUSD" if residual < 0 else "FLAT"
        availability = "SIGNAL_USABLE"

    lineage_tail = normalized[sa.end() :]
    lineage_boundary = re.search(r"4\s*-?\s*week moving average", lineage_tail, re.I)
    if lineage_boundary is None:
        raise core.ContractError("initial-claims lineage paragraph has no 4-week boundary")
    lineage_window = lineage_tail[: lineage_boundary.start()]
    revision = core.REVISION_RE.search(lineage_window)
    revision_delta = 0
    revision_old = None
    revision_new = None
    if revision:
        revision_delta = core._signed(revision.group("kind"), revision.group("delta"))
        revision_old = int(revision.group("old").replace(",", ""))
        revision_new = int(revision.group("new").replace(",", ""))
        if revision_new - revision_old != revision_delta:
            raise core.ContractError("stated revision delta conflicts with old/new levels")
    prior_status = (sa.group("status") or "not_stated").lower()
    if prior_status == "revised" and revision is None:
        raise core.ContractError("revised prior level lacks explicit nearby revision lineage")

    return {
        "schema_version": "alphafactory.dol_ui_seasonal_residual_source.v2",
        "hypothesis_id": core.HYPOTHESIS_ID,
        "stage": core.stage_for_release(parsed_release),
        "source_availability": availability,
        "source_url": url,
        "source_sha256": pdf_sha256,
        "source_bytes": byte_count,
        "source_pages": pages,
        "filename_year_suffix_matches_path": core.filename_year_suffix_matches_path(url),
        "release_date": parsed_release.isoformat(),
        "release_time_local": local_dt.isoformat(),
        "release_timezone": local_dt.tzname(),
        "release_utc": release_utc.isoformat().replace("+00:00", "Z"),
        "claims_week_ending": claims_week.isoformat(),
        "sa_initial_claims_first_public": int(sa.group("level").replace(",", "")),
        "sa_initial_claims_change": sa_change,
        "prior_level_status": prior_status,
        "prior_revision_delta": revision_delta,
        "prior_revision_old": revision_old,
        "prior_revision_new": revision_new,
        "nsa_initial_claims_first_public": int(nsa.group("total").replace(",", "")),
        "nsa_actual_change": nsa_change,
        "seasonal_expected_change": expected_change,
        "seasonal_residual": residual,
        "direction": direction,
    }


original_evaluate_source_gates = core.evaluate_source_gates


def evaluate_source_gates(
    rows: list[dict[str, object]], year_counts: Mapping[int, int]
) -> dict[str, bool]:
    gates = original_evaluate_source_gates(rows, year_counts)
    unavailable = {
        str(row["source_url"])
        for row in rows
        if row.get("source_availability") == "EXPECTED_NOT_PUBLISHED"
    }
    usable = [row for row in rows if row.get("source_availability") == "SIGNAL_USABLE"]
    gates["usable_signal_rows_exact_439"] = (
        len(usable) == 439
        and all(row.get("seasonal_residual") is not None for row in usable)
    )
    gates["missing_expected_exact_frozen_2_flat"] = (
        unavailable == MISSING_EXPECTED_URLS
        and all(
            row.get("direction") == "FLAT" and row.get("seasonal_residual") is None
            for row in rows
            if str(row["source_url"]) in MISSING_EXPECTED_URLS
        )
    )
    return gates


def validate_run_packet(root: Path, packet_path: Path) -> dict[str, object]:
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    required = {
        "schema_version": "alphafactory.dol_ui_source_run_packet.v2",
        "hypothesis_id": core.HYPOTHESIS_ID,
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
            raise core.ContractError(f"run packet field mismatch: {key}")
    bindings = packet.get("bindings")
    if not isinstance(bindings, dict):
        raise core.ContractError("run packet bindings missing")
    for rel in (PLAN_REL, SCRIPT_REL, TEST_REL, REVIEW_REL, CORE_REL):
        expected_hash = bindings.get(rel)
        if not isinstance(expected_hash, str) or expected_hash != core.sha256_path(root / rel):
            raise core.ContractError(f"run packet hash mismatch: {rel}")
    return packet


core.normalize_text = normalize_text
core.parse_release_text = parse_release_text
core.evaluate_source_gates = evaluate_source_gates
core.validate_run_packet = validate_run_packet
core.CSV_FIELDS.insert(0, "source_availability")


if __name__ == "__main__":
    sys.exit(core.main())
