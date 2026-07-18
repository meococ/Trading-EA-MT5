#!/usr/bin/env python3
"""Generate the hash-bound MQL5 DTWEXBGS include used by KLR replication."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "data/DTWEXBGS.csv"
OUTPUT = HERE / "generated/KLR_DTWEXBGS_Data.mqh"
EXPECTED_SOURCE_SHA256 = (
    "15B46514271F0E8D5D721CFEE2FA5A994DB56982E042B55F66F23750B70E8951"
)
FROM_DATE = pd.Timestamp("2021-12-20")
TO_DATE = pd.Timestamp("2024-12-31")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def chunks(values: list[str], width: int = 6) -> list[str]:
    return [", ".join(values[i : i + width]) for i in range(0, len(values), width)]


def main() -> int:
    actual = sha256(SOURCE)
    if actual != EXPECTED_SOURCE_SHA256:
        raise SystemExit(f"DTWEXBGS hash mismatch: {actual}")

    frame = pd.read_csv(SOURCE)
    if list(frame.columns) != ["observation_date", "DTWEXBGS"]:
        raise SystemExit(f"unexpected columns: {list(frame.columns)}")
    frame["observation_date"] = pd.to_datetime(frame["observation_date"], errors="raise")
    frame["DTWEXBGS"] = pd.to_numeric(frame["DTWEXBGS"], errors="coerce")
    frame = frame.dropna().sort_values("observation_date").reset_index(drop=True)
    frame["usd_change"] = frame["DTWEXBGS"].diff()
    frame = frame.loc[
        frame["observation_date"].between(FROM_DATE, TO_DATE)
    ].dropna(subset=["usd_change"])
    if len(frame) != 758:
        raise SystemExit(f"unexpected embedded row count: {len(frame)}")

    dates = [f"D'{value:%Y.%m.%d} 00:00'" for value in frame["observation_date"]]
    changes = [f"{float(value):.10f}" for value in frame["usd_change"]]
    lines = [
        "#ifndef KLR_DTWEXBGS_DATA_MQH",
        "#define KLR_DTWEXBGS_DATA_MQH",
        "",
        f'const string KLR_DTWEXBGS_SOURCE_SHA256="{EXPECTED_SOURCE_SHA256}";',
        f"const int KLR_USD_OBSERVATION_COUNT={len(frame)};",
        "datetime KLR_USD_DATES[] =",
        "  {",
    ]
    date_chunks = chunks(dates)
    lines.extend(f"   {line}{',' if index < len(date_chunks) - 1 else ''}" for index, line in enumerate(date_chunks))
    lines.extend(["  };", "", "double KLR_USD_CHANGES[] =", "  {"])
    change_chunks = chunks(changes)
    lines.extend(
        f"   {line}{',' if index < len(change_chunks) - 1 else ''}"
        for index, line in enumerate(change_chunks)
    )
    lines.extend(["  };", "", "#endif", ""])

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".mqh.tmp")
    temporary.write_text("\n".join(lines), encoding="ascii", newline="\n")
    temporary.replace(OUTPUT)
    print(f"generated={OUTPUT} rows={len(frame)} source_sha256={actual}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
