#!/usr/bin/env python3
"""Build frozen HYP-012 matched control/challenger execution receipts."""

from __future__ import annotations

import argparse
from pathlib import Path

import build_hyp010_fullchart_microrisk_receipt as base


base.HYPOTHESIS_ID = "HYP-ICT-FVG-CONTEXT-STATE-EURUSD-M5-012"
base.PARENT_HYPOTHESIS_ID = (
    "HYP-ICT-FVG-FULLCHART-NONEWS-2018YTD-EURUSD-M5-011"
)
base.FROM_DATE = "2018.01.01"
base.TO_DATE = "2026.07.19"
base.AUTHORITY = "OWNER_AUTHORIZED_CONTEXT_STATE_MATCHED_DIAGNOSTIC_MODEL0"
base.TASK_NOTE = (
    "Exactly one frozen immediate control followed by one closed-bar "
    "context-state challenger; no optimization, rerun, promotion, paper or live."
)
base.PREREG = (
    base.PACKAGE
    / "research"
    / "HYP-ICT-FVG-CONTEXT-STATE-EURUSD-M5-012_MODEL0_PLAN_V2.md"
)
base.OUT = (
    base.ROOT
    / "02. AlphaFactory"
    / "runtime"
    / "ict_fvg_context_state_hyp012_receipts"
)
base.PRESETS = {
    "control": base.PACKAGE
    / "presets"
    / "EURUSD_M5_CONTEXT_CONTROL_2018YTD.set",
    "challenger": base.PACKAGE
    / "presets"
    / "EURUSD_M5_CONTEXT_CHALLENGER_2018YTD.set",
}
base.EXPECTED_PRESET_SHA256 = {
    "control": "9FC1B200E66D76309F130205B9D825B63B398C4C056541A33AE0896618FDE6D2",
    "challenger": "7230C264DE07095CB26E6404C1B12E4A6C8D5D70AFF46384FF4CC5D4F1958E8E",
}


def read_frozen_overrides(role: str) -> str:
    preset = base.PRESETS[role]
    actual_hash = base.sha_file(preset)
    expected_hash = base.EXPECTED_PRESET_SHA256[role]
    if actual_hash != expected_hash:
        raise ValueError(
            f"{role} preset drifted: expected {expected_hash}, got {actual_hash}"
        )
    lines = [
        line.strip()
        for line in preset.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith(("#", ";"))
    ]
    expected_mode = "InpSignalMode=0" if role == "control" else "InpSignalMode=2"
    if expected_mode not in lines:
        raise ValueError(f"{role} preset does not contain {expected_mode}")
    if sum(line.startswith("InpSignalMode=") for line in lines) != 1:
        raise ValueError(f"{role} preset must bind exactly one signal mode")
    override_map: dict[str, str] = {}
    for line in lines:
        if "=" not in line:
            raise ValueError(f"malformed preset line: {line}")
        name, value = line.split("=", 1)
        if name in override_map:
            raise ValueError(f"duplicate preset input: {name}")
        override_map[name] = value
    return ";".join(f"{name}={override_map[name]}" for name in sorted(override_map))


base.read_frozen_overrides = read_frozen_overrides


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("role", choices=("control", "challenger"))
    parser.add_argument("--control-run", type=Path)
    args = parser.parse_args()
    receipt, receipt_sha, overrides = base.build(args.role, args.control_run)
    print(f"receipt={receipt}")
    print(f"sha256={receipt_sha}")
    print(f"overrides={overrides}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
