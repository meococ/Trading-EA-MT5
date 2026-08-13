from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

import pytest


SOURCE = Path(__file__).resolve().parents[1] / "build_dol_ui_source.py"
SPEC = importlib.util.spec_from_file_location("build_dol_ui_source", SOURCE)
assert SPEC and SPEC.loader
sut = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sut
SPEC.loader.exec_module(sut)


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def sample_text(
    *,
    release: str = "December 6, 2018",
    week: str = "December 1",
    sa_level: str = "231,000",
    sa_kind: str = "a decrease",
    sa_change: str = "4,000",
    status: str = "revised",
    nsa_total: str = "315,852",
    nsa_kind: str = "an increase",
    nsa_change: str = "97,194",
    expected_kind: str = "an increase",
    expected_change: str = "102,401",
    revision: str = (
        "The previous week's level was revised up by 1,000 from 234,000 to 235,000."
    ),
) -> str:
    return f"""
    TRANSMISSION OF MATERIALS IN THIS RELEASE IS EMBARGOED UNTIL
    8:30 A.M. (Eastern) Thursday, {release}
    UNEMPLOYMENT INSURANCE WEEKLY CLAIMS
    SEASONALLY ADJUSTED DATA
    In the week ending {week}, the advance figure for seasonally adjusted initial claims was
    {sa_level}, {sa_kind} of {sa_change} from the previous week's {status} level.
    {revision}
    UNADJUSTED DATA
    The advance number of actual initial claims under state programs, unadjusted, totaled
    {nsa_total} in the week ending {week}, {nsa_kind} of {nsa_change} from the previous week.
    The seasonal factors had expected {expected_kind} of {expected_change} from the previous week.
    """


def test_archive_request_is_exact_and_year_bounded() -> None:
    assert sut.archive_request_body(2018) == b"report=press&year=2018&submit=Submit"
    with pytest.raises(sut.ContractError, match="outside frozen"):
        sut.archive_request_body(2017)


def test_official_filename_suffix_anomaly_uses_path_year_and_records_mismatch() -> None:
    url = "https://oui.doleta.gov/press/2019/010318.pdf"
    assert sut.release_date_from_url(url).isoformat() == "2019-01-03"
    assert not sut.filename_year_suffix_matches_path(url)


def test_discover_archive_urls_uses_only_returned_official_links_and_cutoff() -> None:
    html = b"""
    <a href='/press/2026/080626.pdf'>6</a>
    <a href='/press/2026/080626.pdf'>duplicate</a>
    <a href='/press/2026/081326.pdf'>after cutoff</a>
    <a href='/press/2025/080725.pdf'>wrong year</a>
    <a href='https://evil.example/press/2026/080626.pdf'>external</a>
    """
    urls = sut.discover_archive_urls(2026, lambda request: html)
    assert urls == ["https://oui.doleta.gov/press/2026/080626.pdf"]


def test_download_rejects_preexisting_unbound_raw_cache(tmp_path: Path) -> None:
    cache_path = tmp_path / "2019" / "010318.pdf"
    cache_path.parent.mkdir(parents=True)
    cache_path.write_bytes(b"%PDF-unbound")
    with pytest.raises(sut.ContractError, match="unbound raw cache"):
        sut._download_pdf(
            "https://oui.doleta.gov/press/2019/010318.pdf",
            cache_path,
        )


def test_parse_release_freezes_residual_direction_and_dst_clock() -> None:
    payload = sample_text()
    row = sut.parse_release_text(
        payload,
        url="https://oui.doleta.gov/press/2018/120618.pdf",
        pdf_sha256=sha(payload.encode()),
        byte_count=123,
        pages=9,
    )
    assert row["release_utc"] == "2018-12-06T13:30:00Z"
    assert row["filename_year_suffix_matches_path"]
    assert row["release_timezone"] == "EST"
    assert row["claims_week_ending"] == "2018-12-01"
    assert row["sa_initial_claims_change"] == -4000
    assert row["nsa_actual_change"] == 97194
    assert row["seasonal_expected_change"] == 102401
    assert row["seasonal_residual"] == -5207
    assert row["direction"] == "SELL_EURUSD"
    assert row["prior_revision_delta"] == 1000

    summer = sample_text(
        release="July 5, 2018",
        week="June 30",
        nsa_kind="an increase",
        nsa_change="20,000",
        expected_kind="an increase",
        expected_change="10,000",
    )
    summer_row = sut.parse_release_text(
        summer,
        url="https://oui.doleta.gov/press/2018/070518.pdf",
        pdf_sha256=sha(summer.encode()),
        byte_count=456,
        pages=9,
    )
    assert summer_row["release_utc"] == "2018-07-05T12:30:00Z"
    assert summer_row["release_timezone"] == "EDT"
    assert summer_row["seasonal_residual"] == 10000
    assert summer_row["direction"] == "BUY_EURUSD"


def test_parse_zero_expected_and_unrevised_without_revision() -> None:
    text = sample_text(
        status="unrevised",
        revision="",
        nsa_kind="a decrease",
        nsa_change="2,000",
        expected_kind="no change",
        expected_change="",
    ).replace("no change of  from", "no change from")
    row = sut.parse_release_text(
        text,
        url="https://oui.doleta.gov/press/2018/120618.pdf",
        pdf_sha256=sha(text.encode()),
        byte_count=1,
        pages=1,
    )
    assert row["seasonal_expected_change"] == 0
    assert row["seasonal_residual"] == -2000
    assert row["prior_revision_delta"] == 0


def test_parse_fails_closed_on_date_conflict_and_missing_revision_lineage() -> None:
    with pytest.raises(sut.ContractError, match="PDF/URL"):
        sut.parse_release_text(
            sample_text(),
            url="https://oui.doleta.gov/press/2018/120718.pdf",
            pdf_sha256="A" * 64,
            byte_count=1,
            pages=1,
        )
    with pytest.raises(sut.ContractError, match="revision lineage"):
        sut.parse_release_text(
            sample_text(revision=""),
            url="https://oui.doleta.gov/press/2018/120618.pdf",
            pdf_sha256="A" * 64,
            byte_count=1,
            pages=1,
        )


def synthetic_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for year, count in sut.EXPECTED_YEAR_COUNTS.items():
        for index in range(count):
            direction = "BUY_EURUSD" if index % 2 == 0 else "SELL_EURUSD"
            stage = (
                "TRAIN_SOURCE"
                if year <= 2022
                else "INTERNAL_VALIDATION_SOURCE"
                if year <= 2024
                else "SEALED_HOLDOUT_SOURCE_ONLY"
            )
            rows.append(
                {
                    "stage": stage,
                    "direction": direction,
                    "release_date": f"{year}-01-{index + 1:02d}",
                    "release_utc": f"{year}-01-{index + 1:02d}T13:30:00Z",
                    "claims_week_ending": f"{year}-01-{index + 1:02d}",
                    "source_url": f"https://oui.doleta.gov/press/{year}/{index:06d}.pdf",
                }
            )
    return rows


def test_source_gates_pass_balanced_exact_population_and_fail_duplicates() -> None:
    rows = synthetic_rows()
    gates = sut.evaluate_source_gates(rows, sut.EXPECTED_YEAR_COUNTS)
    assert len(rows) == 441
    assert all(gates.values())
    rows[-1]["release_utc"] = rows[-2]["release_utc"]
    assert not sut.evaluate_source_gates(rows, sut.EXPECTED_YEAR_COUNTS)["unique_release_utc"]


def test_default_cli_is_inert_and_no_market_price_surface_exists(capsys: pytest.CaptureFixture[str]) -> None:
    assert sut.main([]) == 0
    output = capsys.readouterr().out
    assert "--execute-source-attempt" in output
    source_text = SOURCE.read_text(encoding="utf-8")
    forbidden = ("EURUSD_H1", "close_price", "profit_factor", "OrderSend", "MetaTrader")
    assert all(token not in source_text for token in forbidden)
