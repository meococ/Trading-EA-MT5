from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


SOURCE = Path(__file__).resolve().parents[1] / "build_dol_ui_source_v2.py"
SPEC = importlib.util.spec_from_file_location("build_dol_ui_source_v2", SOURCE)
assert SPEC and SPEC.loader
sut = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sut
SPEC.loader.exec_module(sut)


def release_text(*, release: str, week: str, expected: str, qualifier: str = "revised") -> str:
    qualifier_text = f"{qualifier} " if qualifier else ""
    revision = (
        "The previous week's level was revised up by 1,000 from 234,000 to 235,000."
        if qualifier == "revised"
        else ""
    )
    return f"""
    EMBARGOED UNTIL 8:30 A.M. (Eastern) Thursday, {release}
    The advance figure for seasonally adjusted initial claims was 231,000, a decrease
    of 4,000 from the previous week's {qualifier_text}level. {revision}
    The 4-week moving average was 220,000. The advance number for seasonally
    adjusted insured unemployment was 1,710,000. The previous week's level was
    revised down by 3,000 from 1,672,000 to 1,669,000.
    The advance number of actual initial claims under state programs, unadjusted,
    totaled 315,852 in the week ending {week}, an increase of 97,194 from the previous
    week. {expected}
    """


def parse(text: str, url: str) -> dict[str, object]:
    return sut.parse_release_text(
        text,
        url=url,
        pdf_sha256="A" * 64,
        byte_count=1,
        pages=1,
    )


def test_normalize_repairs_only_known_pdf_text_layer_shapes() -> None:
    repaired = sut.normalize_text(
        "the a dvance figure and adv ance number from the pre vious week "
        "were 2 45,482, 1 70,000 and 193,0 00"
    )
    assert "advance figure" in repaired
    assert "advance number" in repaired
    assert "previous week" in repaired
    assert "245,482" in repaired
    assert "170,000" in repaired
    assert "193,000" in repaired


@pytest.mark.parametrize(
    ("url", "release", "week"),
    [
        ("https://oui.doleta.gov/press/2020/090320.pdf", "September 3, 2020", "August 29"),
        ("https://oui.doleta.gov/press/2020/091020.pdf", "September 10, 2020", "September 5"),
    ],
)
def test_exact_missing_expected_urls_are_retained_flat(url: str, release: str, week: str) -> None:
    row = parse(release_text(release=release, week=week, expected=""), url)
    assert row["source_availability"] == "EXPECTED_NOT_PUBLISHED"
    assert row["seasonal_expected_change"] is None
    assert row["seasonal_residual"] is None
    assert row["direction"] == "FLAT"


def test_missing_expected_at_any_other_url_fails_closed() -> None:
    text = release_text(release="September 17, 2020", week="September 12", expected="")
    with pytest.raises(sut.core.ContractError, match="outside frozen exception"):
        parse(text, "https://oui.doleta.gov/press/2020/091720.pdf")


def test_expected_appearing_at_exception_url_fails_source_drift() -> None:
    text = release_text(
        release="September 3, 2020",
        week="August 29",
        expected="The seasonal factors had expected an increase of 102,401.",
    )
    with pytest.raises(sut.core.ContractError, match="appeared at frozen"):
        parse(text, "https://oui.doleta.gov/press/2020/090320.pdf")


def test_not_stated_prior_qualifier_is_recorded_not_inferred() -> None:
    text = release_text(
        release="November 20, 2025",
        week="November 15",
        expected="The seasonal factors had expected a decrease of 14,166.",
        qualifier="",
    )
    row = parse(text, "https://oui.doleta.gov/press/2025/112025.pdf")
    assert row["prior_level_status"] == "not_stated"
    assert row["seasonal_residual"] == 111360
    assert row["direction"] == "BUY_EURUSD"


def test_initial_claim_revision_does_not_leak_from_later_insured_unemployment() -> None:
    text = release_text(
        release="December 29, 2022",
        week="December 24",
        expected="The seasonal factors had expected an increase of 1,000.",
        qualifier="unrevised",
    )
    row = parse(text, "https://oui.doleta.gov/press/2022/122922.pdf")
    assert row["prior_level_status"] == "unrevised"
    assert row["prior_revision_delta"] == 0
    assert row["prior_revision_old"] is None


def test_revision_gates_require_exact_source_availability_population() -> None:
    rows = []
    for year, count in sut.core.EXPECTED_YEAR_COUNTS.items():
        for index in range(count):
            url = f"https://oui.doleta.gov/press/{year}/{index:06d}.pdf"
            availability = "SIGNAL_USABLE"
            direction = "BUY_EURUSD" if index % 2 == 0 else "SELL_EURUSD"
            residual = 1 if direction == "BUY_EURUSD" else -1
            if len(rows) in (0, 1):
                url = sorted(sut.MISSING_EXPECTED_URLS)[len(rows)]
                availability = "EXPECTED_NOT_PUBLISHED"
                direction = "FLAT"
                residual = None
            stage = (
                "TRAIN_SOURCE" if year <= 2022 else
                "INTERNAL_VALIDATION_SOURCE" if year <= 2024 else
                "SEALED_HOLDOUT_SOURCE_ONLY"
            )
            rows.append(
                {
                    "stage": stage,
                    "source_availability": availability,
                    "direction": direction,
                    "seasonal_residual": residual,
                    "release_date": f"{year}-01-{index + 1:02d}",
                    "release_utc": f"{year}-01-{index + 1:02d}T13:30:00Z",
                    "claims_week_ending": f"{year}-01-{index + 1:02d}",
                    "source_url": url,
                }
            )
    gates = sut.evaluate_source_gates(rows, sut.core.EXPECTED_YEAR_COUNTS)
    assert gates["usable_signal_rows_exact_439"]
    assert gates["missing_expected_exact_frozen_2_flat"]
    rows[0]["source_availability"] = "SIGNAL_USABLE"
    assert not sut.evaluate_source_gates(rows, sut.core.EXPECTED_YEAR_COUNTS)[
        "missing_expected_exact_frozen_2_flat"
    ]
