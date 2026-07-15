import csv
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "02. AlphaFactory" / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import build_verified_cost_artifact as builder  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def report_html(deals: list[dict]) -> str:
    header = (
        "<tr><td>Time</td><td>Deal</td><td>Symbol</td><td>Type</td><td>Direction</td>"
        "<td>Volume</td><td>Price</td><td>Order</td><td>Fee</td><td>Swap</td>"
        "<td>Profit</td><td>Balance</td><td>Comment</td></tr>"
    )
    rows = []
    for row in deals:
        values = [
            row["time"], row["deal"], row["symbol"], row["side"], row["direction"],
            row["volume"], row["price"], row["order"], row["fee"], row["swap"],
            row["profit"], row["balance"], row["comment"],
        ]
        rows.append("<tr>" + "".join(f"<td>{value}</td>" for value in values) + "</tr>")
    return "<html><body><table><tr><th><b>Deals</b></th></tr>" + header + "".join(rows) + "</table></body></html>"


class VerifiedCostBuilderTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[Path, Path, Path, Path]:
        run_dir = root / "run"
        logs = run_dir / "logs"
        evidence = root / "evidence"
        logs.mkdir(parents=True)
        evidence.mkdir(parents=True)
        report = run_dir / "report.html"
        lifecycle = logs / "EURUSD_1_PX6_Trades_fixture.csv"

        deals = [
            {"time": "2024.01.01 00:00:00", "deal": 1, "symbol": "", "side": "balance", "direction": "", "volume": "", "price": "", "order": "", "fee": 0, "swap": 0, "profit": 100000, "balance": 100000, "comment": ""},
            {"time": "2024.01.01 09:00:00", "deal": 2, "symbol": "EURUSD", "side": "buy", "direction": "in", "volume": 1, "price": 1.10000, "order": 2, "fee": -3.5, "swap": 0, "profit": 0, "balance": 99996.5, "comment": "entry"},
            {"time": "2024.01.01 10:00:00", "deal": 3, "symbol": "EURUSD", "side": "sell", "direction": "out", "volume": 1, "price": 1.10200, "order": 3, "fee": -3.5, "swap": 0, "profit": 200, "balance": 100193, "comment": "tp"},
            {"time": "2024.01.02 09:00:00", "deal": 4, "symbol": "EURUSD", "side": "sell", "direction": "in", "volume": 1, "price": 1.10000, "order": 4, "fee": -3.5, "swap": 0, "profit": 0, "balance": 100189.5, "comment": "entry"},
            {"time": "2024.01.02 10:00:00", "deal": 5, "symbol": "EURUSD", "side": "buy", "direction": "out", "volume": 1, "price": 1.10100, "order": 5, "fee": -3.5, "swap": 0, "profit": -100, "balance": 100086, "comment": "sl"},
        ]
        report.write_text(report_html(deals), encoding="utf-8")

        fields = [
            "event_time", "tag", "action", "order_type", "volume", "price", "sl", "tp",
            "reason", "retcode", "deal", "order", "symbol", "position_id", "entry_price",
            "initial_sl", "initial_tp", "risk_pts", "initial_risk_account", "close_source",
            "deal_reason", "achievedr", "deal_profit", "deal_commission", "deal_swap",
            "deal_fee", "deal_net", "is_final_close",
        ]
        rows = []
        specs = [
            ("101", "BUY", 2, 3, "2024.01.01", 1.10000, 1.10200, 200.0, 2.0),
            ("102", "SELL", 4, 5, "2024.01.02", 1.10000, 1.10100, -100.0, -1.0),
        ]
        for position, side, entry_deal, exit_deal, day, entry_price, exit_price, profit, achieved_r in specs:
            rows.extend(
                [
                    {
                        "event_time": f"{day} 09:00:00", "tag": "fixture", "action": "OPEN",
                        "order_type": side, "volume": 1, "price": entry_price, "sl": 1.099,
                        "tp": 1.102, "reason": "entry", "retcode": 0, "deal": entry_deal,
                        "order": entry_deal, "symbol": "EURUSD", "position_id": position,
                        "entry_price": entry_price, "initial_sl": 1.099, "initial_tp": 1.102,
                        "risk_pts": 100, "initial_risk_account": 100, "close_source": "",
                        "deal_reason": "entry", "achievedr": "", "deal_profit": 0,
                        "deal_commission": -3.5, "deal_swap": 0, "deal_fee": 0,
                        "deal_net": -3.5, "is_final_close": 0,
                    },
                    {
                        "event_time": f"{day} 10:00:00", "tag": "fixture", "action": "CLOSE",
                        "order_type": side, "volume": 1, "price": exit_price, "sl": 1.099,
                        "tp": 1.102, "reason": "exit", "retcode": 0, "deal": exit_deal,
                        "order": exit_deal, "symbol": "EURUSD", "position_id": position,
                        "entry_price": entry_price, "initial_sl": 1.099, "initial_tp": 1.102,
                        "risk_pts": 100, "initial_risk_account": 100, "close_source": "exit",
                        "deal_reason": "exit", "achievedr": achieved_r, "deal_profit": profit,
                        "deal_commission": -3.5, "deal_swap": 0, "deal_fee": 0,
                        "deal_net": profit - 3.5, "is_final_close": 1,
                    },
                ]
            )
        write_csv(lifecycle, fields, rows)

        spread = evidence / "spread.csv"
        write_csv(
            spread,
            ["timestamp", "symbol", "bid", "ask"],
            [
                {"timestamp": f"2024.01.{(index % 28) + 1:02d} 09:00:00", "symbol": "EURUSD", "bid": 1.1, "ask": 1.1001}
                for index in range(100)
            ],
        )
        commission = evidence / "commission.csv"
        write_csv(
            commission,
            ["position_id", "symbol", "account_currency", "round_turn_account_per_lot", "conversion_method"],
            [
                {"position_id": index + 1, "symbol": "EURUSD", "account_currency": "USD", "round_turn_account_per_lot": 7.0, "conversion_method": "per_trade_contemporaneous"}
                for index in range(30)
            ],
        )
        slippage = evidence / "slippage.csv"
        slippage_rows = []
        for index in range(50):
            slippage_rows.append({"fill_id": f"B{index}", "timestamp": "2024.01.10 09:00:00", "symbol": "EURUSD", "side": "BUY", "reference_side": "ask", "reference_price": 1.10000, "fill_price": 1.10007, "pip_size": 0.0001})
            slippage_rows.append({"fill_id": f"S{index}", "timestamp": "2024.01.10 09:00:00", "symbol": "EURUSD", "side": "SELL", "reference_side": "bid", "reference_price": 1.10000, "fill_price": 1.09992, "pip_size": 0.0001})
        write_csv(
            slippage,
            ["fill_id", "timestamp", "symbol", "side", "reference_side", "reference_price", "fill_price", "pip_size"],
            slippage_rows,
        )

        manifest = {
            "run_id": "run-001", "hypothesis_id": "HYP-001", "run_role": "challenger",
            "ea_name": "EA_SonicR", "symbol": "EURUSD", "period": "M15",
            "from": "2024.01.01", "to": "2024.12.31", "model": 0,
            "execution_lane": "research", "execution_mode": 0, "fixed_delay_ms": 0,
            "overrides": "", "config_sha256": "1" * 64, "ex5_sha256": "2" * 64,
            "tester_ex5_sha256": "2" * 64, "includes_sha256": "3" * 64,
            "git_commit": "a" * 40, "git_status_sha256": "4" * 64, "deposit": 100000,
            "leverage": 100, "spread": "current", "telemetry_tier": "trade-only",
            "broker_fingerprint": "a" * 64, "server_fingerprint": "b" * 64,
            "account_fingerprint": "c" * 64, "data_fingerprint": "d" * 64,
            "report_path": str(report), "report_sha256": sha(report),
            "fingerprint_basis": {"broker": "Fixture Broker", "server": "Fixture-Demo", "currency": "USD", "digits": 5, "point": 0.00001, "pip_size": 0.0001},
            "sidecars": [{"path": f"logs/{lifecycle.name}", "sha256": sha(lifecycle), "row_count": 4}],
        }
        (run_dir / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        cost_source = {
            "schema_version": "alphafactory_cost_source_manifest.v1", "provenance_status": "VERIFIED",
            "audit_status": "PASS", "verdict": "PASS", "broker": "Fixture Broker",
            "server": "Fixture-Demo", "account_currency": "USD",
            "broker_fingerprint": manifest["broker_fingerprint"], "server_fingerprint": manifest["server_fingerprint"],
            "account_fingerprint": manifest["account_fingerprint"], "data_fingerprint": manifest["data_fingerprint"],
            "symbol": "EURUSD", "from": manifest["from"], "to": manifest["to"],
            "symbol_geometry": {"digits": 5, "point": 0.00001, "pip_size": 0.0001},
            "historical_spread_provenance": {"verification_status": "VERIFIED", "source": str(spread), "source_sha256": sha(spread), "symbol": "EURUSD", "coverage": {"from": manifest["from"], "to": manifest["to"], "sample_count": 100, "total_count": 100, "coverage_ratio": 1.0}},
            "commission_provenance": {"verification_status": "VERIFIED", "source": str(commission), "source_sha256": sha(commission), "symbol": "EURUSD", "value": 7.0, "statistic": "p90", "sample_count": 30, "same_symbol_lifecycles": True, "method": "raw lifecycle P90 round-turn account commission per lot"},
            "slippage_provenance": {"verification_status": "VERIFIED", "source": str(slippage), "source_sha256": sha(slippage), "symbol": "EURUSD", "sample_count": 100, "buy_count": 50, "sell_count": 50, "independent_reference": True, "buy_reference_side": "ask", "sell_reference_side": "bid", "p90_buy": 0.7, "p90_sell": 0.8, "p90_roundturn": 1.5, "slippage_unit": "pips", "method": "raw side-referenced adverse fill delta"},
            "direction_aware_methodology": {"verification_status": "VERIFIED", "direction_aware": True, "long_cost_treatment": "entry ask and exit bid", "short_cost_treatment": "entry bid and exit ask"},
        }
        cost_path = root / "cost-source.json"
        cost_path.write_text(json.dumps(cost_source), encoding="utf-8")
        return report, cost_path, lifecycle, spread

    def test_build_reprices_report_deals_and_recomputes_scenarios(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report, cost_path, _, _ = self.fixture(Path(tmp))
            payload = builder.build(report, cost_path)
            self.assertEqual(payload["provenance_status"], "VERIFIED")
            self.assertEqual(payload["lifecycle_evidence"]["schema_version"], "sonic_telemetry.v3")
            self.assertEqual(len(payload["trade_repricing"]), 2)
            x1 = next(row for row in payload["scenarios"] if row["scenario"] == "cost_x1_00")
            self.assertAlmostEqual(x1["sum_positive_net_r"], 1.78)
            self.assertAlmostEqual(x1["sum_negative_net_r"], -1.22)

    def test_missing_ordercalc_risk_account_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report, cost_path, lifecycle, _ = self.fixture(Path(tmp))
            with lifecycle.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            rows[0]["initial_risk_account"] = ""
            write_csv(lifecycle, list(rows[0]), rows)
            manifest_path = report.parent / "run_manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["sidecars"][0]["sha256"] = sha(lifecycle)
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "initial_risk_account"):
                builder.build(report, cost_path)

    def test_raw_spread_coverage_below_contract_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report, cost_path, _, spread = self.fixture(Path(tmp))
            with spread.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            rows[0]["ask"] = ""
            write_csv(spread, list(rows[0]), rows)
            payload = json.loads(cost_path.read_text())
            coverage = payload["historical_spread_provenance"]["coverage"]
            coverage.update({"sample_count": 99, "total_count": 100, "coverage_ratio": 0.99})
            payload["historical_spread_provenance"]["source_sha256"] = sha(spread)
            cost_path.write_text(json.dumps(payload))
            builder.build(report, cost_path)  # exact 99% boundary is valid
            rows[1]["ask"] = ""
            write_csv(spread, list(rows[0]), rows)
            payload["historical_spread_provenance"]["source_sha256"] = sha(spread)
            coverage.update({"sample_count": 98, "coverage_ratio": 0.98})
            cost_path.write_text(json.dumps(payload))
            with self.assertRaisesRegex(ValueError, "99%"):
                builder.build(report, cost_path)

    def test_report_deal_profit_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report, cost_path, _, _ = self.fixture(Path(tmp))
            report.write_text(report.read_text().replace(">200<", ">999<", 1), encoding="utf-8")
            manifest_path = report.parent / "run_manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["report_sha256"] = sha(report)
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "profit does not match"):
                builder.build(report, cost_path)

    def test_achievedr_tamper_cannot_change_report_bound_repricing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report, cost_path, lifecycle, _ = self.fixture(Path(tmp))
            baseline = builder.build(report, cost_path)
            with lifecycle.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            rows[1]["achievedr"] = "99"
            write_csv(lifecycle, list(rows[0]), rows)
            manifest_path = report.parent / "run_manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["sidecars"][0]["sha256"] = sha(lifecycle)
            manifest_path.write_text(json.dumps(manifest))
            rebuilt = builder.build(report, cost_path)
            self.assertEqual(rebuilt["scenarios"], baseline["scenarios"])

    def test_raw_commission_rows_override_no_self_attested_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report, cost_path, _, _ = self.fixture(Path(tmp))
            payload = json.loads(cost_path.read_text())
            payload["commission_provenance"]["value"] = 70.0
            cost_path.write_text(json.dumps(payload))
            with self.assertRaisesRegex(ValueError, "raw-evidence P90"):
                builder.build(report, cost_path)


if __name__ == "__main__":
    unittest.main()
