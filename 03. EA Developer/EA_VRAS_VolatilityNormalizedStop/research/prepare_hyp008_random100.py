#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import random
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[3]
PKG = ROOT / "03. EA Developer" / "EA_VRAS_VolatilityNormalizedStop"
RESEARCH = PKG / "research"
RUN = ROOT / "02. AlphaFactory" / "runs" / "EA_VRAS_VolatilityNormalizedStop" / "20260722_233420"
PLAN = RESEARCH / "HYP-VRAS-EURUSD-M5-008_GROK_RANDOM100_FORENSIC_PLAN.md"
BARS_M1 = ROOT / "02. AlphaFactory" / "data" / "fivepercent" / "EURUSD" / "EURUSD_M1_2015_now.parquet"
BARS_H1 = ROOT / "02. AlphaFactory" / "data" / "fivepercent" / "EURUSD" / "EURUSD_H1_2015_now.parquet"
OUT = RESEARCH / "evidence" / "HYP-VRAS-EURUSD-M5-008_GROK_RANDOM100"
CASES = OUT / "cases_random_100.csv"
SELECTION = OUT / "selection_manifest.json"
SEED = 18416118573351363056


def load_clock():
    path = ROOT / "02. AlphaFactory" / "tools" / "research" / "fivepercent_server_clock.py"
    spec = importlib.util.spec_from_file_location("fivepercent_server_clock", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load canonical clock model: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CLOCK = load_clock()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def utc_session(hour: int) -> str:
    if 7 <= hour < 13:
        return "Europe"
    if 13 <= hour < 18:
        return "NewYork"
    if 0 <= hour < 7:
        return "Asia"
    return "OffHours"


def load_report_close_comments(report: Path) -> dict[int, str]:
    soup = BeautifulSoup(report.read_text(encoding="utf-16"), "html.parser")
    tables = soup.find_all("table")
    if len(tables) < 2:
        raise RuntimeError("MT5 report does not contain the orders table")
    comments: dict[int, str] = {}
    for report_row in tables[1].find_all("tr"):
        cells = [cell.get_text(" ", strip=True) for cell in report_row.find_all(["td", "th"])]
        if len(cells) == 1 and cells[0] == "Deals":
            break
        if len(cells) != 11 or not cells[1].isdigit() or cells[9] != "filled":
            continue
        comment = cells[10]
        if comment == "HYP-VRAS-EURUSD-M5-008":
            continue
        order_id = int(cells[1])
        if order_id in comments:
            raise RuntimeError(f"Duplicate filled closing-order ID in report: {order_id}")
        comments[order_id] = comment
    return comments


def exact_exit_class(comment: str, initial_stop: float) -> tuple[str, float | None]:
    if comment == "VRAS HYP006 time exit":
        return "TIME_EXIT", None
    parts = comment.split()
    if len(parts) == 2 and parts[0] == "tp":
        return "TARGET", float(parts[1])
    if len(parts) == 2 and parts[0] == "sl":
        active_stop = float(parts[1])
        if abs(active_stop - initial_stop) <= 0.000011:
            return "INITIAL_SL", active_stop
        return "MOVED_SL", active_stop
    return "UNKNOWN", None


def load_positions(lifecycle: Path, report_comments: dict[int, str]) -> list[dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    with lifecycle.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            groups[row["position_id"]].append(row)
    positions: list[dict] = []
    for position_id, events in groups.items():
        opens = [row for row in events if row["action"] == "OPEN"]
        closes = [row for row in events if row["is_final_close"] == "1"]
        if len(opens) != 1 or len(closes) != 1:
            raise RuntimeError(f"Position {position_id} lifecycle is not exact one OPEN/one final CLOSE")
        entry = opens[0]
        close = closes[0]
        direction = 1 if entry["order_type"] == "BUY" else -1
        entry_price = float(entry["price"])
        risk_distance = float(entry["risk_pts"]) * 0.00001
        initial_risk = float(entry["initial_risk_account"])
        net = sum(float(row["deal_net"]) for row in events)
        entry_time_server = datetime.strptime(entry["event_time"], "%Y.%m.%d %H:%M:%S")
        exit_time_server = datetime.strptime(close["event_time"], "%Y.%m.%d %H:%M:%S")
        entry_time_utc = CLOCK.server_to_utc(entry_time_server)
        exit_time_utc = CLOCK.server_to_utc(exit_time_server)
        initial_stop = entry_price - direction * risk_distance
        close_deal_id = int(close["deal"])
        exit_comment = report_comments.get(close_deal_id)
        if exit_comment is None:
            raise RuntimeError(f"No report closing-order comment for lifecycle close deal {close_deal_id}")
        exit_class, active_stop_at_exit = exact_exit_class(exit_comment, initial_stop)
        if exit_class == "UNKNOWN":
            raise RuntimeError(f"Unknown report exit comment for deal {close_deal_id}: {exit_comment!r}")
        positions.append({
            "position_id": int(position_id),
            "entry_time": entry["event_time"],
            "exit_time": close["event_time"],
            "direction": direction,
            "side": entry["order_type"],
            "entry": entry_price,
            "lifecycle_sl": initial_stop,
            "exit": float(close["price"]),
            "volume": float(entry["volume"]),
            "initial_risk_account": initial_risk,
            "risk_pips": risk_distance / 0.0001,
            "net_usd": net,
            "net_r": net / initial_risk if initial_risk > 0 else None,
            "holding_minutes": (exit_time_utc - entry_time_utc).total_seconds() / 60.0,
            "entry_time_utc": entry_time_utc.strftime("%Y.%m.%d %H:%M:%S"),
            "exit_time_utc": exit_time_utc.strftime("%Y.%m.%d %H:%M:%S"),
            "server_utc_offset_h": CLOCK.server_offset_hours(entry_time_server),
            "weekday_utc": entry_time_utc.strftime("%A"),
            "session_utc": utc_session(entry_time_utc.hour),
            "close_deal_id": close_deal_id,
            "exit_comment": exit_comment,
            "exit_class": exit_class,
            "active_stop_at_exit": active_stop_at_exit,
        })
    return sorted(positions, key=lambda row: row["position_id"])


def load_accepted(telemetry: Path) -> dict[tuple[str, int], dict]:
    accepted: dict[tuple[str, int], dict] = {}
    with telemetry.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["status"] != "ORDER_ACCEPTED":
                continue
            key = (row["server_time"], int(row["direction"]))
            if key in accepted:
                raise RuntimeError(f"Duplicate ORDER_ACCEPTED telemetry key {key}")
            accepted[key] = row
    return accepted


def main() -> int:
    lifecycle = next((RUN / "analysis" / "logs").glob("*_LifecycleTrades_*.csv"))
    telemetry = next((RUN / "analysis" / "logs").glob("*_DecisionTelemetry_*.csv"))
    runmeta = next((RUN / "analysis" / "logs").glob("*_RunMeta_*.json"))
    manifest = RUN / "run_manifest.json"
    report = RUN / "report.html"
    source = RUN / "snapshot" / "source" / "EA_VRAS_VolatilityNormalizedStop.mq5"

    expected = {
        manifest: "FF9332450A14E1F0E8B190F735C5BC1B9834267265C16BB60154C4A4703D97F2",
        lifecycle: "2CB21056F69708D2FD735A2A06E725DC578FD9F56E39487C393CD3B3B340C556",
        telemetry: "C510692DB20D710D92FCDE52C8628B158D98AAFE00BD3211E5E36E74254EDF66",
        source: "720D45505282123D4C8B78428B9913F6ADD41176013E5B968A60C56CF446E53C",
        report: "483E5D42D08EE9DFF538015F5A2305DEFA3A81CC702496A859B03DCBE92F7F68",
        BARS_M1: "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A",
    }
    for path, frozen in expected.items():
        actual = sha256(path)
        if actual != frozen:
            raise RuntimeError(f"Frozen SHA mismatch for {path}: {actual} != {frozen}")

    report_comments = load_report_close_comments(report)
    positions = load_positions(lifecycle, report_comments)
    if len(positions) != 3611:
        raise RuntimeError(f"Expected 3611 unique positions, got {len(positions)}")
    accepted = load_accepted(telemetry)
    if len(accepted) != 3611:
        raise RuntimeError(f"Expected 3611 ORDER_ACCEPTED rows, got {len(accepted)}")

    rng = random.Random(SEED)
    selected = rng.sample(positions, 100)
    if len({row["position_id"] for row in selected}) != 100:
        raise RuntimeError("Random selection contains duplicate positions")

    OUT.mkdir(parents=True, exist_ok=True)
    fields = [
        "case_id", "position_id", "entry_time_server", "exit_time_server", "entry_time_utc", "exit_time_utc",
        "server_utc_offset_h", "direction", "side",
        "entry", "sl", "tp", "exit", "volume", "initial_risk_account", "risk_pips",
        "net_usd", "net_r", "holding_minutes", "weekday_utc", "session_utc", "selection_reason", "label",
        "close_deal_id", "exact_exit_class", "exact_exit_comment", "active_stop_at_exit",
        "telemetry_status", "h1_close", "h1_ema", "rolling_vwap_48", "atr14", "spread_pips",
    ]
    rows: list[dict] = []
    for index, position in enumerate(selected, 1):
        key = (position["entry_time"], position["direction"])
        decision = accepted.get(key)
        if decision is None:
            raise RuntimeError(f"No ORDER_ACCEPTED telemetry for position {position['position_id']} key={key}")
        telemetry_entry = float(decision["entry"])
        telemetry_stop = float(decision["stop"])
        telemetry_target = float(decision["target"])
        if abs(telemetry_entry - position["entry"]) > 0.00001:
            raise RuntimeError(f"Entry parity failure for position {position['position_id']}")
        if abs(telemetry_stop - position["lifecycle_sl"]) > 0.00002:
            raise RuntimeError(f"Stop parity failure for position {position['position_id']}")
        if position["net_usd"] > 0:
            label = "WIN_RANDOM"
        elif position["net_usd"] < 0:
            label = "LOSS_RANDOM"
        else:
            label = "FLAT_RANDOM"
        row = {
            "case_id": f"VRAS-008-R{index:03d}-P{position['position_id']}",
            "position_id": position["position_id"],
            "entry_time_server": position["entry_time"],
            "exit_time_server": position["exit_time"],
            "entry_time_utc": position["entry_time_utc"],
            "exit_time_utc": position["exit_time_utc"],
            "server_utc_offset_h": position["server_utc_offset_h"],
            "direction": position["direction"],
            "side": position["side"],
            "entry": position["entry"],
            "sl": telemetry_stop,
            "tp": telemetry_target,
            "exit": position["exit"],
            "volume": position["volume"],
            "initial_risk_account": position["initial_risk_account"],
            "risk_pips": position["risk_pips"],
            "net_usd": position["net_usd"],
            "net_r": position["net_r"],
            "holding_minutes": position["holding_minutes"],
            "weekday_utc": position["weekday_utc"],
            "session_utc": position["session_utc"],
            "selection_reason": "RANDOM_UNIFORM_WITHOUT_REPLACEMENT",
            "label": label,
            "close_deal_id": position["close_deal_id"],
            "exact_exit_class": position["exit_class"],
            "exact_exit_comment": position["exit_comment"],
            "active_stop_at_exit": position["active_stop_at_exit"],
            "telemetry_status": decision["status"],
            "h1_close": float(decision["h1_close"]),
            "h1_ema": float(decision["h1_ema"]),
            "rolling_vwap_48": float(decision["rolling_vwap_48"]),
            "atr14": float(decision["atr14"]),
            "spread_pips": float(decision["spread_pips"]),
        }
        rows.append(row)

    with CASES.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    selection = {
        "schema_version": "vras_hyp008_random100_selection.v1",
        "created_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_id": "HYP-VRAS-EURUSD-M5-008",
        "run_id": "20260722_233420",
        "forensic_only": True,
        "plan_path": PLAN.relative_to(ROOT).as_posix(),
        "plan_sha256": sha256(PLAN),
        "population_positions": len(positions),
        "sample_size": len(rows),
        "sampling": {
            "method": "python_random_sample_without_replacement",
            "population_order": "numeric_position_id_ascending",
            "seed": SEED,
            "seed_derivation": "unsigned integer from first 16 hex characters of frozen run-manifest SHA256",
            "preserve_draw_order": True,
            "replacement_or_rebalance_allowed": False,
        },
        "sample_composition": {
            "wins": sum(row["net_usd"] > 0 for row in rows),
            "losses": sum(row["net_usd"] < 0 for row in rows),
            "flats": sum(row["net_usd"] == 0 for row in rows),
            "buy": sum(row["direction"] > 0 for row in rows),
            "sell": sum(row["direction"] < 0 for row in rows),
            "weekend_crossings": sum(
                datetime.strptime(row["exit_time_utc"], "%Y.%m.%d %H:%M:%S").date()
                > datetime.strptime(row["entry_time_utc"], "%Y.%m.%d %H:%M:%S").date()
                and datetime.strptime(row["entry_time_utc"], "%Y.%m.%d %H:%M:%S").weekday() == 4
                for row in rows
            ),
            "exact_exit_classes": {
                exit_class: sum(row["exact_exit_class"] == exit_class for row in rows)
                for exit_class in ("INITIAL_SL", "TARGET", "TIME_EXIT", "MOVED_SL")
            },
        },
        "bindings": {
            "run_manifest": {"path": manifest.relative_to(ROOT).as_posix(), "sha256": sha256(manifest)},
            "lifecycle": {"path": lifecycle.relative_to(ROOT).as_posix(), "sha256": sha256(lifecycle)},
            "decision_telemetry": {"path": telemetry.relative_to(ROOT).as_posix(), "sha256": sha256(telemetry)},
            "run_meta": {"path": runmeta.relative_to(ROOT).as_posix(), "sha256": sha256(runmeta)},
            "source": {"path": source.relative_to(ROOT).as_posix(), "sha256": sha256(source)},
            "tester_report": {"path": report.relative_to(ROOT).as_posix(), "sha256": sha256(report)},
            "bars_m1": {"path": BARS_M1.relative_to(ROOT).as_posix(), "sha256": sha256(BARS_M1)},
            "bars_h1": {"path": BARS_H1.relative_to(ROOT).as_posix(), "sha256": sha256(BARS_H1)},
            "cases_csv": {"path": CASES.relative_to(ROOT).as_posix(), "sha256": sha256(CASES)},
        },
        "case_ids": [row["case_id"] for row in rows],
        "position_ids": [row["position_id"] for row in rows],
    }
    SELECTION.write_text(json.dumps(selection, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "HYP008_RANDOM100_FROZEN",
        "selection": str(SELECTION),
        "cases": str(CASES),
        "sample_composition": selection["sample_composition"],
        "selection_sha256": sha256(SELECTION),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
