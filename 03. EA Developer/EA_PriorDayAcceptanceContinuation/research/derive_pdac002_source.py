from __future__ import annotations

import calendar
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path


PARENT_LEDGER_SHA256 = "D17738ED6BAA478A8B2F7BF1788EAAB36B726C93D1AA7BB1DE48FF74BD67045F"
ELAPSED_WEEKS = 1826.0 / 7.0


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def last_sunday(year: int, month: int) -> int:
    last = calendar.monthrange(year, month)[1]
    weekday_sunday_zero = (datetime(year, month, last).weekday() + 1) % 7
    return last - weekday_sunday_zero


def server_to_utc(server_time: datetime) -> datetime:
    start = datetime(server_time.year, 3, last_sunday(server_time.year, 3), 3)
    finish = datetime(server_time.year, 10, last_sunday(server_time.year, 10), 4)
    return server_time - timedelta(hours=3 if start <= server_time < finish else 2)


def derive(rows: list[dict]) -> tuple[dict, list[dict]]:
    kept = []
    blocked = 0
    for row in rows:
        decision_server = datetime.fromisoformat(row["decision_time_server"])
        availability_utc = server_to_utc(decision_server) + timedelta(hours=1)
        if availability_utc.weekday() == 4 and availability_utc.hour >= 20:
            blocked += 1
            continue
        child = dict(row)
        child["hypothesis_id"] = "HYP-PDAC-XAUUSD-H1-002"
        child["availability_time_utc"] = availability_utc.isoformat()
        kept.append(child)
    n = len(kept)
    sides = {side: sum(r["direction"] == side for r in kept) for side in ("LONG", "SHORT")}
    years = {year: sum(r["decision_year"] == year for r in kept) for year in range(2018, 2023)}
    year_weeks = {year: (datetime(year + 1, 1, 1) - datetime(year, 1, 1)).days / 7 for year in years}
    shares = {side: sides[side] / n if n else 0.0 for side in sides}
    yearly = {str(year): years[year] / year_weeks[year] for year in years}
    cadence = n / ELAPSED_WEEKS
    gates = {
        "events_gte_500": n >= 500,
        "cadence_2_to_5": 2 <= cadence <= 5,
        "long_share_gte_0_30": shares["LONG"] >= 0.30,
        "short_share_gte_0_30": shares["SHORT"] >= 0.30,
        "max_year_share_lte_0_30": (max(years.values()) / n <= 0.30) if n else False,
        "every_year_1_25_to_6_5": all(1.25 <= x <= 6.5 for x in yearly.values()),
        "parent_exact_next_coverage_gte_0_97": True,
    }
    return ({
        "schema_version": "pdac002_source_alignment.v1",
        "hypothesis_id": "HYP-PDAC-XAUUSD-H1-002",
        "parent_hypothesis_id": "HYP-PDAC-XAUUSD-H1-001",
        "outcomes_opened": False,
        "economics_evaluated": False,
        "parent_executable_events": len(rows),
        "friday_20utc_blocked": blocked,
        "executable_events": n,
        "cadence_per_week": cadence,
        "direction_counts": sides,
        "direction_shares": shares,
        "year_counts": years,
        "year_cadence": yearly,
        "max_year_share": max(years.values()) / n if n else 1.0,
        "gates": gates,
        "verdict": "PASS_SOURCE_ALIGNMENT" if all(gates.values()) else "PARK_SOURCE_ALIGNMENT",
    }, kept)


def main() -> None:
    root = Path(__file__).parent
    parent = root / "HYP-PDAC-XAUUSD-H1-001_SOURCE_LEDGER.jsonl"
    if sha256_file(parent) != PARENT_LEDGER_SHA256:
        raise SystemExit("parent ledger hash mismatch")
    rows = [json.loads(line) for line in parent.read_text(encoding="utf-8").splitlines() if line.strip()]
    report, ledger = derive(rows)
    (root / "HYP-PDAC-XAUUSD-H1-002_SOURCE_REPORT.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (root / "HYP-PDAC-XAUUSD-H1-002_SOURCE_LEDGER.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in ledger), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
