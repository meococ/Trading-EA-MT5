#!/usr/bin/env python3
"""Build the frozen HYP-011 2018-to-present no-news diagnostic receipt."""

from pathlib import Path

import build_hyp010_fullchart_microrisk_receipt as base


base.HYPOTHESIS_ID = "HYP-ICT-FVG-FULLCHART-NONEWS-2018YTD-EURUSD-M5-011"
base.PARENT_HYPOTHESIS_ID = "HYP-ICT-FVG-FULLCHART-MICRORISK-EURUSD-M5-010"
base.FROM_DATE = "2018.01.01"
base.TO_DATE = "2026.07.19"
base.AUTHORITY = "OWNER_REQUESTED_2018_YTD_NONEWS_FULLCHART_DIAGNOSTIC_MODEL0"
base.TASK_NOTE = (
    "Exactly one frozen 2018-to-present no-news micro-risk control arm; "
    "no optimization, report-fidelity claim, promotion, paper or live authority."
)
base.PREREG = (
    base.PACKAGE
    / "research"
    / f"{base.HYPOTHESIS_ID}_DIAGNOSTIC_PLAN.md"
)
base.OUT = (
    base.ROOT
    / "02. AlphaFactory"
    / "runtime"
    / "ict_fvg_fullchart_2018ytd_nonews_receipts"
)
base.PRESETS = {
    "control": base.PACKAGE
    / "presets"
    / "EURUSD_M5_CONTROL_FULLCHART_2018YTD_NONEWS.set",
}
base.EXPECTED_PRESET_SHA256 = {
    "control": "1B48AAA7ACBE2C50686A1261D4A3C6CF019C2625DB1654BBD9454B25125B2997",
}


if __name__ == "__main__":
    raise SystemExit(base.main())
