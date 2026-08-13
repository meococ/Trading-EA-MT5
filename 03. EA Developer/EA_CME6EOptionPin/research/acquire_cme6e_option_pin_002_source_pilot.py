"""Acquire the frozen EUU.OPT quarterly definition/statistics pilot only."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


BASE_SCRIPT = Path(__file__).with_name(
    "acquire_cme6e_option_pin_001_source_pilot.py"
)
BASE_SCRIPT_SHA256 = "73C190C016E3C9B08D42F57FC359BD35501A48CDD92378AF6B6CC1E4E6280970"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


if sha256_file(BASE_SCRIPT) != BASE_SCRIPT_SHA256:
    raise RuntimeError("shared acquisition implementation drifted")

SPEC = importlib.util.spec_from_file_location("option_pin_acquisition", BASE_SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load shared acquisition implementation")
acquisition = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(acquisition)

acquisition.PILOT_ID = "CME6EOPTPIN002-SOURCE-PILOT-002"
acquisition.PARENT = "EUU.OPT"
acquisition.START = "2019-09-04T00:00:00Z"
acquisition.END = "2019-09-06T13:45:00Z"
acquisition.PLAN_REL = Path(
    "03. EA Developer/EA_CME6EOptionPin/research/"
    "HYP-CME6E-OPT-PIN-EURUSD-M15-001_SOURCE_PILOT_002_PLAN.md"
)
acquisition.PLAN_SHA256 = (
    "83A203DC00195D8DACEE35B5663FE13559125DD88F8FB8DEBAD18B9221153AF0"
)
acquisition.AUTHORITY_REL = Path(
    "03. EA Developer/EA_CME6EOptionPin/research/"
    "HYP-CME6E-OPT-PIN-EURUSD-M15-001_SOURCE_PILOT_002_AUTHORITY.json"
)
acquisition.AUTHORITY_SHA256 = (
    "69F36BEB3350CEBC4DEDE39E27A92F85424299C89C6F5CE20F82D1E827B40A45"
)
acquisition.OUTPUT_REL = Path(
    "02. AlphaFactory/data/databento/cme_6e_option_pin/"
    f"{acquisition.HYPOTHESIS_ID}/{acquisition.PILOT_ID}"
)


def workspace_from_source() -> Path:
    return Path(__file__).resolve().parents[3]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace_from_source())
    args = parser.parse_args()
    try:
        receipt_path = acquisition.execute(args.workspace)
        receipt = json.loads(receipt_path.read_text(encoding="ascii"))
        print(
            "CME6EOPTPIN002_SOURCE_ACQUIRED "
            f"cost={receipt['live_estimated_usd']:.12f} "
            f"bytes={receipt['live_billable_bytes']} calls=2"
        )
        print(f"RECEIPT {receipt_path}")
        return 0
    except acquisition.PilotError as exc:
        print(f"CME6EOPTPIN002_SOURCE_BLOCKED reason={exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
