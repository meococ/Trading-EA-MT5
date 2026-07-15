import datetime as dt
import csv
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = ROOT / "02. AlphaFactory" / "analysis"
TOOLS_DIR = ROOT / "02. AlphaFactory" / "tools"
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import monte_carlo  # noqa: E402
import robustness_suite  # noqa: E402
import unified_validation  # noqa: E402
import walk_forward  # noqa: E402
import build_verified_cost_artifact as verified_cost_builder  # noqa: E402
from quant_analyzer import Trade  # noqa: E402


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    body = []
    for row in deals:
        values = [
            row["time"], row["deal"], row["symbol"], row["side"], row["direction"],
            row["volume"], row["price"], row["order"], row["fee"], row["swap"],
            row["profit"], row["balance"], row["comment"],
        ]
        body.append("<tr>" + "".join(f"<td>{value}</td>" for value in values) + "</tr>")
    return "<html><body><table><tr><th><b>Deals</b></th></tr>" + header + "".join(body) + "</table></body></html>"


def make_trades(count: int = 200) -> list[Trade]:
    start = dt.datetime(2021, 1, 1, 9, 0)
    profits = [35.0, -18.0, 22.0, -11.0, 14.0, -9.0]
    return [
        Trade(
            entry_time=start + dt.timedelta(days=index),
            exit_time=start + dt.timedelta(days=index, minutes=30),
            side="buy",
            profit=profits[index % len(profits)],
            n_out_deals=1,
            exit_comment="tp" if profits[index % len(profits)] > 0 else "sl",
            entry_comment="test",
        )
        for index in range(count)
    ]


class ArtifactFixture:
    def __init__(self, root: Path) -> None:
        self.run_dir = root / "run"
        self.out_dir = self.run_dir / "analysis"
        self.evidence_dir = self.run_dir / "evidence"
        self.snapshot_root = self.run_dir / "snapshot"
        self.variants_dir = self.run_dir / "variants"
        self.run_dir.mkdir(parents=True)
        self.out_dir.mkdir(parents=True)
        self.evidence_dir.mkdir(parents=True)
        self.snapshot_root.mkdir(parents=True)
        self.variants_dir.mkdir(parents=True)
        self.report = self.run_dir / "report.html"
        self.logs_dir = self.run_dir / "logs"
        self.logs_dir.mkdir(parents=True)
        self.lifecycle = self.logs_dir / "XAUUSD_1_PX6_Trades_fixture.csv"
        self.cost_source_manifest = self.evidence_dir / "cost_source_manifest.json"
        self.source = self.snapshot_root / "source" / "EA_Fixture.mq5"
        self.source.parent.mkdir(parents=True)
        self.source.write_text("// fixture source\n", encoding="utf-8")
        self.config_snapshot = self.snapshot_root / "fixture.ini"
        self.ex5_snapshot = self.snapshot_root / "EA_Fixture.ex5"
        self.tester_ex5 = self.run_dir / "tester" / "EA_Fixture.ex5"
        self.include_one = self.snapshot_root / "include" / "One.mqh"
        self.include_two = self.snapshot_root / "include" / "Two.mqh"
        self.config_snapshot.write_text("[Tester]\nModel=0\n", encoding="utf-8")
        self.ex5_snapshot.write_bytes(b"fixture-ex5")
        self.tester_ex5.parent.mkdir(parents=True)
        self.tester_ex5.write_bytes(self.ex5_snapshot.read_bytes())
        self.include_one.parent.mkdir(parents=True)
        self.include_one.write_text("// include one\n", encoding="utf-8")
        self.include_two.write_text("// include two\n", encoding="utf-8")
        (self.variants_dir / "variant_a.csv").write_text("month,pnl\n2024-01,1\n", encoding="utf-8")
        (self.variants_dir / "variant_b.csv").write_text("month,pnl\n2024-01,2\n", encoding="utf-8")
        self.spread_source = self.evidence_dir / "spread.csv"
        self.commission_source = self.evidence_dir / "commission.csv"
        self.slippage_source = self.evidence_dir / "slippage.csv"
        self.broker_contract_source = self.evidence_dir / "broker_contract.json"
        self._write_report_lifecycle_and_raw_cost_evidence()
        self.manifest_path = self.run_dir / "run_manifest.json"
        self.cost_path = self.out_dir / "sonic_cost_stress_fixture.json"
        self.wfa_path = self.out_dir / "optimization_wfa_results.json"
        self._write_manifest()
        self._write_nonrepaint_audit()
        self._write_defaults()

    def _write_report_lifecycle_and_raw_cost_evidence(self) -> None:
        deals = [
            {
                "time": "2024.01.01 00:00:00", "deal": 1, "symbol": "",
                "side": "balance", "direction": "", "volume": "", "price": "",
                "order": "", "fee": 0, "swap": 0, "profit": 100000,
                "balance": 100000, "comment": "",
            }
        ]
        lifecycle_fields = [
            "event_time", "tag", "action", "order_type", "volume", "price", "sl", "tp",
            "reason", "retcode", "deal", "order", "symbol", "position_id", "entry_price",
            "initial_sl", "initial_tp", "risk_pts", "initial_risk_account", "close_source",
            "deal_reason", "achievedr", "deal_profit", "deal_commission", "deal_swap",
            "deal_fee", "deal_net", "is_final_close",
        ]
        lifecycle_rows = []
        for index in range(18):
            day = index + 1
            side = "BUY" if index % 2 == 0 else "SELL"
            exit_side = "sell" if side == "BUY" else "buy"
            entry_side = side.lower()
            entry_deal = 2 + index * 2
            exit_deal = entry_deal + 1
            gross_r = 1.5 if index < 10 else -1.0
            profit = gross_r * 1000.0
            entry_price = 2000.0
            exit_price = 2015.0 if gross_r > 0 and side == "BUY" else 1985.0 if gross_r > 0 else 1990.0 if side == "BUY" else 2010.0
            date = f"2024.01.{day:02d}"
            deals.extend(
                [
                    {"time": f"{date} 09:00:00", "deal": entry_deal, "symbol": "XAUUSD", "side": entry_side, "direction": "in", "volume": 1, "price": entry_price, "order": entry_deal, "fee": -3.5, "swap": 0, "profit": 0, "balance": 100000, "comment": "entry"},
                    {"time": f"{date} 10:00:00", "deal": exit_deal, "symbol": "XAUUSD", "side": exit_side, "direction": "out", "volume": 1, "price": exit_price, "order": exit_deal, "fee": -3.5, "swap": 0, "profit": profit, "balance": 100000 + profit - 7, "comment": "exit"},
                ]
            )
            lifecycle_rows.extend(
                [
                    {"event_time": f"{date} 09:00:00", "tag": "fixture", "action": "OPEN", "order_type": side, "volume": 1, "price": entry_price, "sl": 1999, "tp": 2015, "reason": "entry", "retcode": 0, "deal": entry_deal, "order": entry_deal, "symbol": "XAUUSD", "position_id": 100 + index, "entry_price": entry_price, "initial_sl": 1999, "initial_tp": 2015, "risk_pts": 100, "initial_risk_account": 1000, "close_source": "", "deal_reason": "entry", "achievedr": "", "deal_profit": 0, "deal_commission": -3.5, "deal_swap": 0, "deal_fee": 0, "deal_net": -3.5, "is_final_close": 0},
                    {"event_time": f"{date} 10:00:00", "tag": "fixture", "action": "CLOSE", "order_type": side, "volume": 1, "price": exit_price, "sl": 1999, "tp": 2015, "reason": "exit", "retcode": 0, "deal": exit_deal, "order": exit_deal, "symbol": "XAUUSD", "position_id": 100 + index, "entry_price": entry_price, "initial_sl": 1999, "initial_tp": 2015, "risk_pts": 100, "initial_risk_account": 1000, "close_source": "exit", "deal_reason": "exit", "achievedr": gross_r, "deal_profit": profit, "deal_commission": -3.5, "deal_swap": 0, "deal_fee": 0, "deal_net": profit - 3.5, "is_final_close": 1},
                ]
            )
        self.report.write_text(report_html(deals), encoding="utf-8")
        write_csv(self.lifecycle, lifecycle_fields, lifecycle_rows)

        write_csv(
            self.spread_source,
            ["timestamp", "symbol", "bid", "ask"],
            [
                {"timestamp": f"2024.01.{(index % 28) + 1:02d} 09:00:00", "symbol": "XAUUSD", "bid": 2000.0, "ask": 2000.1}
                for index in range(1000)
            ],
        )
        write_csv(
            self.commission_source,
            ["position_id", "symbol", "account_currency", "round_turn_account_per_lot", "conversion_method"],
            [
                {"position_id": index + 1, "symbol": "XAUUSD", "account_currency": "USD", "round_turn_account_per_lot": 7.0, "conversion_method": "per_trade_contemporaneous"}
                for index in range(60)
            ],
        )
        slippage_rows = []
        for index in range(125):
            slippage_rows.append({"fill_id": f"B{index}", "timestamp": "2024.01.10 09:00:00", "symbol": "XAUUSD", "side": "BUY", "reference_side": "ask", "reference_price": 2000.0, "fill_price": 2000.007, "pip_size": 0.01})
            slippage_rows.append({"fill_id": f"S{index}", "timestamp": "2024.01.10 09:00:00", "symbol": "XAUUSD", "side": "SELL", "reference_side": "bid", "reference_price": 2000.0, "fill_price": 1999.992, "pip_size": 0.01})
        write_csv(
            self.slippage_source,
            ["fill_id", "timestamp", "symbol", "side", "reference_side", "reference_price", "fill_price", "pip_size"],
            slippage_rows,
        )
        self.broker_contract_source.write_text(
            json.dumps(
                {
                    "broker_fingerprint": "d" * 64,
                    "server_fingerprint": "e" * 64,
                    "account_fingerprint": "b" * 64,
                    "symbol": "XAUUSD",
                    "account_currency": "USD",
                    "per_lot_basis": True,
                    "round_turn_account_per_lot": 7.0,
                    "from": "2024.01.01",
                    "to": "2024.02.12",
                    "conversion_method": "per_trade_contemporaneous",
                    "description": "Published USD 7.00 round-turn commission contract.",
                }
            ),
            encoding="utf-8",
        )

    def write(self, name: str, payload: dict) -> Path:
        path = self.out_dir / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def _write_manifest(self, **updates: object) -> None:
        include_rows = [
            {"snapshot_path": str(self.include_one), "sha256": sha256_file(self.include_one)},
            {"snapshot_path": str(self.include_two), "sha256": sha256_file(self.include_two)},
        ]
        include_binding = unified_validation._include_snapshot_binding(
            {
                "snapshot_root": str(self.snapshot_root),
                "include_snapshots": include_rows,
                "includes_sha256": "0" * 64,
            },
            self.run_dir / "run_manifest.json",
        )
        payload = {
            "run_id": "fixture-run-001",
            "hypothesis_id": "HYP-FIXTURE-001",
            "run_role": "challenger",
            "ea_name": "EA_Fixture",
            "from": "2024.01.01",
            "to": "2024.02.12",  # 42 elapsed days = 6.0 calendar weeks
            "model": 0,
            "execution_lane": "research",
            "execution_mode": 0,
            "fixed_delay_ms": 0,
            "overrides": "InpFixture=1",
            "config_snapshot": str(self.config_snapshot),
            "config_sha256": sha256_file(self.config_snapshot),
            "ex5_snapshot": str(self.ex5_snapshot),
            "ex5_sha256": sha256_file(self.ex5_snapshot),
            "tester_ex5_path": str(self.tester_ex5),
            "tester_ex5_sha256": sha256_file(self.tester_ex5),
            "snapshot_root": str(self.snapshot_root),
            "include_snapshots": include_rows,
            "includes_sha256": include_binding["actual_sha256"],
            "git_commit": "a" * 40,
            "git_status_sha256": "4" * 64,
            "deposit": 100000,
            "leverage": 100,
            "spread": 0,
            "telemetry_tier": "trade-only",
            "report_path": str(self.report),
            "report_sha256": sha256_file(self.report),
            "source_path": str(self.source),
            "source_snapshot": str(self.source),
            "source_sha256": sha256_file(self.source),
            "symbol": "XAUUSD",
            "period": "M15",
            "broker_fingerprint": "d" * 64,
            "server_fingerprint": "e" * 64,
            "account_fingerprint": "b" * 64,
            "data_fingerprint": "c" * 64,
            "fingerprint_basis": {
                "broker": "MetaQuotes Ltd.",
                "server": "MetaQuotes-Demo",
                "currency": "USD",
                "digits": 2,
                "point": 0.01,
                "pip_size": 0.01,
            },
            "sidecars": [
                {
                    "path": f"logs/{self.lifecycle.name}",
                    "sha256": sha256_file(self.lifecycle),
                    "row_count": 36,
                }
            ],
        }
        if self.manifest_path.exists():
            payload.update(json.loads(self.manifest_path.read_text(encoding="utf-8")))
        payload.update(updates)
        self.manifest_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    def _write_nonrepaint_audit(self) -> None:
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        refs = [
            {"path": manifest["source_snapshot"], "sha256": manifest["source_sha256"]},
            *[
                {"path": row["snapshot_path"], "sha256": row["sha256"]}
                for row in manifest["include_snapshots"]
            ],
        ]
        self.write(
            "nonrepaint_audit.json",
            {
                "schema_version": "alphafactory_nonrepaint_audit.v1",
                "status": "PASS",
                "run_id": manifest["run_id"],
                "hypothesis_id": manifest["hypothesis_id"],
                "audited_files": refs,
                "findings": [],
            },
        )

    def _write_verified_cost(self) -> None:
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        basis = manifest["fingerprint_basis"]
        cost_source = {
            "schema_version": "alphafactory_cost_source_manifest.v1",
            "provenance_status": "VERIFIED",
            "audit_status": "PASS",
            "verdict": "PASS",
            "broker": basis["broker"],
            "server": basis["server"],
            "account_currency": basis["currency"],
            "broker_fingerprint": manifest["broker_fingerprint"],
            "server_fingerprint": manifest["server_fingerprint"],
            "account_fingerprint": manifest["account_fingerprint"],
            "data_fingerprint": manifest["data_fingerprint"],
            "symbol": manifest["symbol"],
            "from": manifest["from"],
            "to": manifest["to"],
            "symbol_geometry": {
                "digits": basis["digits"],
                "point": basis["point"],
                "pip_size": basis["pip_size"],
            },
            "historical_spread_provenance": {
                "verification_status": "VERIFIED",
                "source": str(self.spread_source),
                "source_sha256": sha256_file(self.spread_source),
                "symbol": manifest["symbol"],
                "coverage": {
                    "from": manifest["from"],
                    "to": manifest["to"],
                    "sample_count": 1000,
                    "total_count": 1000,
                    "coverage_ratio": 1.0,
                },
            },
            "commission_provenance": {
                "verification_status": "VERIFIED",
                "source": str(self.commission_source),
                "source_sha256": sha256_file(self.commission_source),
                "symbol": manifest["symbol"],
                "value": 7.0,
                "statistic": "p90",
                "sample_count": 60,
                "same_symbol_lifecycles": True,
                "method": "raw lifecycle P90 round-turn account commission per lot",
            },
            "slippage_provenance": {
                "verification_status": "VERIFIED",
                "source": str(self.slippage_source),
                "source_sha256": sha256_file(self.slippage_source),
                "symbol": manifest["symbol"],
                "sample_count": 250,
                "buy_count": 125,
                "sell_count": 125,
                "buy_reference_side": "ask",
                "sell_reference_side": "bid",
                "p90_buy": 0.7,
                "p90_sell": 0.8,
                "p90_roundturn": 1.5,
                "slippage_unit": "pips",
                "method": "raw side-referenced adverse fill delta",
                "independent_reference": True,
            },
            "direction_aware_methodology": {
                "verification_status": "VERIFIED",
                "direction_aware": True,
                "long_cost_treatment": "entry ask, exit bid",
                "short_cost_treatment": "entry bid, exit ask",
            },
        }
        self.cost_source_manifest.write_text(json.dumps(cost_source), encoding="utf-8")
        self.write(
            self.cost_path.name,
            verified_cost_builder.build(self.report, self.cost_source_manifest),
        )

    def _write_wfa(self) -> None:
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        self.write(
            self.wfa_path.name,
            {
                "analysis_kind": "optimization_aware_walk_forward",
                "promotion_eligible": True,
                "report": str(self.report),
                "report_sha256": sha256_file(self.report),
                "run_id": manifest["run_id"],
                "hypothesis_id": manifest["hypothesis_id"],
                "run_identity_sha256": unified_validation._run_identity_sha256(
                    manifest, sha256_file(self.report)
                ),
                "source_sha256": manifest["source_sha256"],
                "summary": {"oos_profitable_ratio": 0.8},
            },
        )

    def _write_variant_artifacts(self) -> None:
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        for name, schema_version, metrics in (
            (
                "cscv_pbo.json",
                "alphafactory_cscv_pbo.v1",
                {"n_variants": 4, "combos_used": 20, "pbo": 0.10},
            ),
            (
                "white_reality_check.json",
                "alphafactory_white_reality_check.v1",
                {"n_variants": 4, "n_bootstrap": 2000, "p_value": 0.01, "verdict": "PASS"},
            ),
        ):
            artifact_path = self.write(name, metrics)
            unified_validation._bind_variant_artifact(
                artifact_path,
                schema_version=schema_version,
                variants_dir=self.variants_dir,
                report_path=self.report,
                manifest=manifest,
            )

    def write_monthly_fitness(self, month_values: dict[str, float]) -> None:
        months = [
            {"month": month, "n": 1, "net_profit": value}
            for month, value in sorted(month_values.items())
        ]
        first_month = months[0]["month"] if months else None
        last_month = months[-1]["month"] if months else None
        self.write(
            "monthly_fitness.json",
            {
                "report": str(self.report),
                "run_manifest": str(self.manifest_path),
                "monthly_window": {
                    "from": f"{first_month}-01" if first_month else None,
                    "to": f"{last_month}-28" if last_month else None,
                    "total_months": len(months),
                    "active_months": len(months),
                    "inactive_months": 0,
                },
                "months": months,
            },
        )

    def configure_confirmed(self, month_values: dict[str, float] | None = None) -> None:
        self._write_manifest(**{"from": "2019.01.01", "to": "2025.12.31"})
        enhanced_path = self.out_dir / "enhanced_summary.json"
        enhanced = json.loads(enhanced_path.read_text(encoding="utf-8"))
        enhanced["n_trades"] = 1040
        enhanced_path.write_text(json.dumps(enhanced), encoding="utf-8")
        if month_values is None:
            month_values = {
                f"{year:04d}-{month:02d}": 100.0 + ((month % 3) - 1) * 10.0
                for year in range(2019, 2026)
                for month in range(1, 13)
            }
        self.write_monthly_fitness(month_values)
        self._write_verified_cost()
        self._write_wfa()
        self._write_variant_artifacts()

    def _write_defaults(self) -> None:
        self.write(
            "enhanced_summary.json",
            {
                "n_trades": 18,
                "profit_factor": 1.5,
                "max_drawdown_pct": 4.0,
                "net_profit": 100.0,
            },
        )
        self.write(
            "robustness_results.json",
            {"random_seed": 1729, "summary": {"passed": 6, "total": 7, "pass_rate": 85.7}},
        )
        self.write(
            "monte_carlo_results.json",
            {"random_seed": 1729, "max_drawdown_pct": {"p95": 6.0}},
        )
        self.write("equity_audit.json", {"verdict": "PASS"})
        self.write(
            "overnight_exposure.json",
            {
                "counts": {
                    "total_trades": 18,
                    "overnight_trades": 0,
                    "weekend_crossing_trades": 0,
                }
            },
        )
        self.write(
            "slippage_summary.json",
            {
                "available": True,
                "status": "OK",
                "execution_quality": {
                    "open_ack_minus_fill_gap": 0,
                    "modify_unresolved": 0,
                    "close_unresolved": 0,
                },
            },
        )
        self._write_verified_cost()
        self._write_wfa()
        self.write_monthly_fitness({"2024-01": 100.0, "2024-02": 100.0})
        self.write(
            "wfa_results.json",
            {
                "analysis_kind": "fixed_parameter_temporal_slicing",
                "promotion_eligible": False,
                "summary": {"oos_profitable_ratio": 0.8},
            },
        )
        self._write_variant_artifacts()


class ValidationHardeningTests(unittest.TestCase):
    def test_fixed_parameter_temporal_slicing_is_quarantined(self) -> None:
        result = walk_forward.walk_forward_analysis(make_trades(100), n_windows=5)

        self.assertEqual(result["analysis_kind"], "fixed_parameter_temporal_slicing")
        self.assertFalse(result["promotion_eligible"])
        self.assertEqual(result["promotion_status"], "DIAGNOSTIC_ONLY")
        self.assertIn("no per-window parameter optimization", result["quarantine_reason"].lower())

    def test_monte_carlo_default_seed_is_deterministic(self) -> None:
        trades = make_trades(80)

        first = monte_carlo.monte_carlo_equity(trades, 10_000.0, n_sims=100)
        second = monte_carlo.monte_carlo_equity(trades, 10_000.0, n_sims=100)

        self.assertEqual(first, second)
        self.assertEqual(first["random_seed"], monte_carlo.DEFAULT_RANDOM_SEED)

    def test_robustness_default_seed_is_deterministic(self) -> None:
        trades = make_trades(200)

        first = robustness_suite.run_full_suite(trades)
        second = robustness_suite.run_full_suite(trades)

        self.assertEqual(first, second)
        self.assertEqual(first["random_seed"], robustness_suite.DEFAULT_RANDOM_SEED)

    def test_challenger_uses_exact_elapsed_calendar_week_cadence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = ArtifactFixture(Path(tmp))
            # 18 completed positions / (42 elapsed days / 7) = exactly 3.0/week.
            summary = unified_validation.evaluate_validation_gates(
                str(fixture.report), str(fixture.out_dir), stage="challenger"
            )

            cadence = summary["gates"]["cadence"]
            self.assertEqual(cadence["status"], "PASS")
            self.assertEqual(cadence["actual"]["elapsed_days"], 42)
            self.assertEqual(cadence["actual"]["elapsed_calendar_weeks"], 6.0)
            self.assertEqual(cadence["actual"]["trades_per_week"], 3.0)

            manifest = json.loads((fixture.run_dir / "run_manifest.json").read_text())
            manifest["to"] = "2024.03.05"  # 64 days; 18 / (64/7) = 1.96875, below gate.
            (fixture.run_dir / "run_manifest.json").write_text(json.dumps(manifest))
            summary = unified_validation.evaluate_validation_gates(
                str(fixture.report), str(fixture.out_dir), stage="challenger"
            )
            self.assertEqual(summary["gates"]["cadence"]["status"], "FAIL")
            self.assertAlmostEqual(
                summary["gates"]["cadence"]["actual"]["trades_per_week"],
                1.96875,
            )

    def test_nonzero_runner_exit_blocks_direct_gate_evaluation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = ArtifactFixture(Path(tmp))
            summary = unified_validation.evaluate_validation_gates(
                str(fixture.report),
                str(fixture.out_dir),
                stage="challenger",
                runner_results={"every_runner": {"status": "FAIL", "returncode": 99}},
            )

            self.assertEqual(summary["verdict"], "REVIEW")
            self.assertEqual(summary["gates"]["runner_invocation_success"]["status"], "BLOCKED")
            self.assertEqual(summary["runners"]["every_runner"]["returncode"], 99)

    def test_nonzero_returncode_blocks_even_when_status_claims_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = ArtifactFixture(Path(tmp))
            summary = unified_validation.evaluate_validation_gates(
                str(fixture.report),
                str(fixture.out_dir),
                stage="challenger",
                runner_results={"lying_runner": {"status": "OK", "returncode": 7}},
            )

            self.assertEqual(summary["gates"]["runner_invocation_success"]["status"], "BLOCKED")
            self.assertEqual(summary["verdict"], "REVIEW")

    def test_run_all_blocks_stale_passing_artifacts_left_unchanged_by_failed_runners(self) -> None:
        runner_failure = {"status": "FAIL", "returncode": 99, "elapsed_s": 0.0}
        artifact_failure = {"status": "ERROR", "artifact": "diagnostic-only"}
        with tempfile.TemporaryDirectory() as tmp:
            fixture = ArtifactFixture(Path(tmp))
            with (
                mock.patch.object(unified_validation, "run_enhanced_analysis", return_value=runner_failure),
                mock.patch.object(unified_validation, "run_equity_audit", return_value=runner_failure),
                mock.patch.object(unified_validation, "run_monte_carlo", return_value=runner_failure),
                mock.patch.object(unified_validation, "run_walk_forward", return_value=runner_failure),
                mock.patch.object(unified_validation, "run_robustness", return_value=runner_failure),
                mock.patch.object(unified_validation, "generate_slippage_summary", return_value=artifact_failure),
                mock.patch.object(unified_validation, "generate_monthly_fitness", return_value=artifact_failure),
                mock.patch.object(unified_validation, "generate_overnight_exposure", return_value=artifact_failure),
            ):
                summary = unified_validation.run_all_validations(
                    str(fixture.report),
                    str(fixture.out_dir),
                    parallel=True,
                    stage="challenger",
                )

            self.assertEqual(summary["verdict"], "REVIEW")
            freshness = summary["gates"]["invocation_artifact_freshness"]
            self.assertEqual(freshness["status"], "BLOCKED")
            self.assertIn("enhanced_summary", freshness["actual"]["unchanged"])
            self.assertIn("equity_audit", freshness["actual"]["unchanged"])
            self.assertIn("monte_carlo", freshness["actual"]["unchanged"])
            self.assertIn("walk_forward", freshness["actual"]["unchanged"])
            self.assertIn("robustness", freshness["actual"]["unchanged"])
            self.assertIn("execution", freshness["actual"]["unchanged"])
            self.assertIn("overnight_exposure", freshness["actual"]["unchanged"])
            self.assertTrue(all(item["verdict_input"] for item in summary["tests"].values()))
            self.assertTrue(summary["invocation_id"])
            self.assertTrue(summary["invocation_start_utc"].endswith("Z"))

    def test_byte_identical_rewrite_is_not_fresh_even_when_runner_succeeds(self) -> None:
        runner_success = {"status": "OK", "returncode": 0, "elapsed_s": 0.0}
        with tempfile.TemporaryDirectory() as tmp:
            fixture = ArtifactFixture(Path(tmp))

            def rewrite(name: str):
                def _rewrite(*_args, **_kwargs):
                    path = fixture.out_dir / name
                    original = path.read_bytes()
                    path.write_bytes(original)
                    return runner_success

                return _rewrite

            with (
                mock.patch.object(unified_validation, "run_enhanced_analysis", side_effect=rewrite("enhanced_summary.json")),
                mock.patch.object(unified_validation, "run_equity_audit", side_effect=rewrite("equity_audit.json")),
                mock.patch.object(unified_validation, "run_monte_carlo", side_effect=rewrite("monte_carlo_results.json")),
                mock.patch.object(unified_validation, "run_walk_forward", side_effect=rewrite("wfa_results.json")),
                mock.patch.object(unified_validation, "run_robustness", side_effect=rewrite("robustness_results.json")),
                mock.patch.object(unified_validation, "generate_slippage_summary", side_effect=rewrite("slippage_summary.json")),
                mock.patch.object(unified_validation, "generate_monthly_fitness", side_effect=rewrite("monthly_fitness.json")),
                mock.patch.object(unified_validation, "generate_overnight_exposure", side_effect=rewrite("overnight_exposure.json")),
            ):
                summary = unified_validation.run_all_validations(
                    str(fixture.report),
                    str(fixture.out_dir),
                    parallel=True,
                    stage="challenger",
                )

            freshness = summary["gates"]["invocation_artifact_freshness"]
            self.assertEqual(freshness["status"], "BLOCKED")
            self.assertIn("enhanced_summary", freshness["actual"]["identical_rewrite"])
            self.assertEqual(summary["gates"]["runner_invocation_success"]["status"], "PASS")
            self.assertEqual(summary["verdict"], "REVIEW")

    def test_nonzero_runner_blocks_even_when_every_artifact_content_changes(self) -> None:
        runner_success = {"status": "OK", "returncode": 0, "elapsed_s": 0.0}
        runner_failure = {"status": "FAIL", "returncode": 9, "elapsed_s": 0.0}
        with tempfile.TemporaryDirectory() as tmp:
            fixture = ArtifactFixture(Path(tmp))

            def rewrite(name: str, result: dict):
                def _rewrite(*_args, **_kwargs):
                    path = fixture.out_dir / name
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    payload["invocation_marker"] = name
                    path.write_text(json.dumps(payload), encoding="utf-8")
                    return result

                return _rewrite

            with (
                mock.patch.object(unified_validation, "run_enhanced_analysis", side_effect=rewrite("enhanced_summary.json", runner_failure)),
                mock.patch.object(unified_validation, "run_equity_audit", side_effect=rewrite("equity_audit.json", runner_success)),
                mock.patch.object(unified_validation, "run_monte_carlo", side_effect=rewrite("monte_carlo_results.json", runner_success)),
                mock.patch.object(unified_validation, "run_walk_forward", side_effect=rewrite("wfa_results.json", runner_success)),
                mock.patch.object(unified_validation, "run_robustness", side_effect=rewrite("robustness_results.json", runner_success)),
                mock.patch.object(unified_validation, "generate_slippage_summary", side_effect=rewrite("slippage_summary.json", runner_success)),
                mock.patch.object(unified_validation, "generate_monthly_fitness", side_effect=rewrite("monthly_fitness.json", runner_success)),
                mock.patch.object(unified_validation, "generate_overnight_exposure", side_effect=rewrite("overnight_exposure.json", runner_success)),
            ):
                summary = unified_validation.run_all_validations(
                    str(fixture.report),
                    str(fixture.out_dir),
                    parallel=True,
                    stage="challenger",
                )

            freshness = summary["gates"]["invocation_artifact_freshness"]
            self.assertEqual(freshness["status"], "BLOCKED")
            self.assertIn("enhanced_summary", freshness["actual"]["not_fresh"])
            self.assertEqual(summary["gates"]["runner_invocation_success"]["status"], "BLOCKED")
            self.assertIn("enhanced_analysis", summary["gates"]["runner_invocation_success"]["actual"]["failed"])
            self.assertEqual(summary["verdict"], "REVIEW")

    def test_strict_pf_threshold_and_inclusive_risk_bounds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = ArtifactFixture(Path(tmp))
            metrics_path = fixture.out_dir / "enhanced_summary.json"
            metrics = json.loads(metrics_path.read_text())
            metrics.update({"profit_factor": 99.0, "max_drawdown_pct": 8.0})
            metrics_path.write_text(json.dumps(metrics))
            baseline = unified_validation.evaluate_validation_gates(
                str(fixture.report), str(fixture.out_dir), stage="challenger"
            )
            exact_pf = baseline["gates"]["profit_factor"]["actual"]["profit_factor"]

            summary = unified_validation.evaluate_validation_gates(
                str(fixture.report),
                str(fixture.out_dir),
                stage="challenger",
                thresholds={"min_profit_factor": exact_pf},
            )

            self.assertEqual(summary["gates"]["profit_factor"]["status"], "FAIL")
            self.assertEqual(summary["gates"]["max_drawdown_pct"]["status"], "PASS")

            metrics["profit_factor"] = 0.10
            metrics_path.write_text(json.dumps(metrics), encoding="utf-8")
            summary = unified_validation.evaluate_validation_gates(
                str(fixture.report),
                str(fixture.out_dir),
                stage="challenger",
                thresholds={"min_profit_factor": exact_pf - 0.01},
            )
            self.assertEqual(summary["gates"]["profit_factor"]["status"], "PASS")

    def test_challenger_blocks_non_real_tick_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = ArtifactFixture(Path(tmp))
            fixture._write_manifest(model=1)

            summary = unified_validation.evaluate_validation_gates(
                str(fixture.report), str(fixture.out_dir), stage="challenger"
            )

            self.assertEqual(summary["gates"]["mt5_real_ticks_model"]["status"], "BLOCKED")
            self.assertEqual(summary["verdict"], "REVIEW")
            self.assertFalse(summary["promotion_eligible"])

    def test_nonrepaint_gate_rehashes_exact_snapshot_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = ArtifactFixture(Path(tmp))
            audit_path = fixture.out_dir / "nonrepaint_audit.json"
            payload = json.loads(audit_path.read_text(encoding="utf-8"))
            payload["audited_files"] = payload["audited_files"][:-1]
            audit_path.write_text(json.dumps(payload), encoding="utf-8")

            summary = unified_validation.evaluate_validation_gates(
                str(fixture.report), str(fixture.out_dir), stage="challenger"
            )

            gate = summary["gates"]["nonrepaint_audit"]
            self.assertEqual(gate["status"], "BLOCKED")
            self.assertIn("exactly equal", gate["reason"])
            self.assertFalse(summary["promotion_eligible"])

    def test_confirmed_quarantines_proxy_robustness_pbo_and_white_rc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = ArtifactFixture(Path(tmp))
            fixture.configure_confirmed()

            challenger = unified_validation.evaluate_validation_gates(
                str(fixture.report), str(fixture.out_dir), stage="challenger"
            )
            confirmed = unified_validation.evaluate_validation_gates(
                str(fixture.report),
                str(fixture.out_dir),
                stage="confirmed",
                variants_dir=str(fixture.variants_dir),
            )

            for gate in (
                "minimum_trades",
                "walk_forward",
                "monthly_stability",
                "half_year_stability",
                "year_stability",
            ):
                self.assertNotIn(gate, challenger["gates"])
                self.assertEqual(confirmed["gates"][gate]["status"], "PASS")
            for gate in ("robustness_pass_rate", "pbo", "white_reality_check"):
                self.assertEqual(confirmed["gates"][gate]["status"], "BLOCKED")
            self.assertIn("diagnostic", confirmed["gates"]["pbo"]["reason"].lower())
            self.assertIn("diagnostic", confirmed["gates"]["white_reality_check"]["reason"].lower())
            self.assertEqual(confirmed["verdict"], "REVIEW")
            self.assertFalse(confirmed["promotion_eligible"])

    def test_confirmed_blocks_quarantined_fixed_parameter_wfa(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = ArtifactFixture(Path(tmp))
            fixture.configure_confirmed()
            (fixture.out_dir / "optimization_wfa_results.json").unlink()
            fixture.write(
                "wfa_results.json",
                {
                    "analysis_kind": "fixed_parameter_temporal_slicing",
                    "promotion_eligible": False,
                    "summary": {"oos_profitable_ratio": 1.0},
                },
            )
            summary = unified_validation.evaluate_validation_gates(
                str(fixture.report),
                str(fixture.out_dir),
                stage="confirmed",
                variants_dir=str(fixture.variants_dir),
            )

            self.assertEqual(summary["gates"]["walk_forward"]["status"], "BLOCKED")
            self.assertEqual(summary["verdict"], "REVIEW")
            self.assertFalse(summary["promotion_eligible"])

    def test_confirmed_wfa_requires_exact_optimization_aware_kind(self) -> None:
        for analysis_kind in ("", "not_a_walk_forward"):
            with self.subTest(analysis_kind=analysis_kind), tempfile.TemporaryDirectory() as tmp:
                fixture = ArtifactFixture(Path(tmp))
                fixture.configure_confirmed()
                payload = json.loads(fixture.wfa_path.read_text(encoding="utf-8"))
                payload["analysis_kind"] = analysis_kind
                fixture.wfa_path.write_text(json.dumps(payload), encoding="utf-8")

                summary = unified_validation.evaluate_validation_gates(
                    str(fixture.report),
                    str(fixture.out_dir),
                    stage="confirmed",
                    variants_dir=str(fixture.variants_dir),
                )

                self.assertEqual(summary["gates"]["walk_forward"]["status"], "BLOCKED")
                self.assertIn(
                    "analysis_kind must equal optimization_aware_walk_forward",
                    summary["gates"]["walk_forward"]["reason"],
                )

    def test_confirmed_blocks_unrelated_external_optimization_wfa(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = ArtifactFixture(Path(tmp))
            fixture.configure_confirmed()
            fixture.write(
                "optimization_wfa_results.json",
                {
                    "analysis_kind": "optimization_aware_walk_forward",
                    "promotion_eligible": True,
                    "report": str(Path(tmp) / "different_run" / "report.html"),
                    "run_id": "different-run-id",
                    "hypothesis_id": "different-hypothesis",
                    "summary": {"oos_profitable_ratio": 1.0},
                },
            )

            summary = unified_validation.evaluate_validation_gates(
                str(fixture.report),
                str(fixture.out_dir),
                stage="confirmed",
                variants_dir=str(fixture.variants_dir),
            )

            self.assertEqual(summary["gates"]["walk_forward"]["status"], "BLOCKED")
            self.assertIn("does not bind", summary["gates"]["walk_forward"]["reason"].lower())

    def test_confirmed_wfa_binding_requires_every_identity_match(self) -> None:
        invalid_cases = (
            ("report_sha256", "0" * 64, "report_sha256_match"),
            ("run_id", "different-run", "run_id_match"),
            ("hypothesis_id", "different-hypothesis", "hypothesis_id_match"),
            ("run_identity_sha256", "1" * 64, "run_identity_sha256_match"),
            ("source_sha256", "2" * 64, "source_sha256_match"),
        )
        for field, invalid_value, match_field in invalid_cases:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                fixture = ArtifactFixture(Path(tmp))
                fixture.configure_confirmed()
                payload = json.loads(fixture.wfa_path.read_text(encoding="utf-8"))
                payload[field] = invalid_value
                fixture.wfa_path.write_text(json.dumps(payload), encoding="utf-8")

                summary = unified_validation.evaluate_validation_gates(
                    str(fixture.report),
                    str(fixture.out_dir),
                    stage="confirmed",
                    variants_dir=str(fixture.variants_dir),
                )

                gate = summary["gates"]["walk_forward"]
                self.assertEqual(gate["status"], "BLOCKED")
                self.assertFalse(gate["actual"]["binding"][match_field])

    def test_canonical_run_identity_ignores_mutable_attestation_but_binds_economics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = ArtifactFixture(Path(tmp))
            fixture.configure_confirmed()
            enhanced_path = fixture.out_dir / "enhanced_summary.json"
            enhanced = json.loads(enhanced_path.read_text(encoding="utf-8"))
            enhanced["n_trades"] = 18
            enhanced_path.write_text(json.dumps(enhanced), encoding="utf-8")
            manifest = json.loads(fixture.manifest_path.read_text(encoding="utf-8"))
            identity_fields = unified_validation._run_identity_payload(
                manifest, sha256_file(fixture.report)
            )
            for required_field in (
                "run_role",
                "ea_name",
                "config_sha256",
                "ex5_sha256",
                "tester_ex5_sha256",
                "includes_sha256",
                "git_commit",
                "git_status_sha256",
                "deposit",
                "leverage",
                "spread",
                "telemetry_tier",
            ):
                self.assertIn(required_field, identity_fields)
            self.assertEqual(identity_fields["execution_mode"], 0)
            self.assertEqual(identity_fields["fixed_delay_ms"], 0)
            self.assertEqual(identity_fields["spread"], 0)
            manifest["research_loop"] = {
                "status": "PASS",
                "generated_at_utc": "2026-07-11T12:00:00Z",
            }
            fixture.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            summary = unified_validation.evaluate_validation_gates(
                str(fixture.report),
                str(fixture.out_dir),
                stage="confirmed",
                variants_dir=str(fixture.variants_dir),
            )
            self.assertEqual(summary["gates"]["walk_forward"]["status"], "PASS")
            self.assertEqual(summary["gates"]["cost_stress_x1_5"]["status"], "PASS")

            manifest["deposit"] = 50000
            fixture.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            summary = unified_validation.evaluate_validation_gates(
                str(fixture.report),
                str(fixture.out_dir),
                stage="confirmed",
                variants_dir=str(fixture.variants_dir),
            )
            self.assertEqual(summary["gates"]["walk_forward"]["status"], "BLOCKED")
            self.assertEqual(summary["gates"]["cost_stress_x1_5"]["status"], "BLOCKED")

    def test_confirmed_rehashes_every_run_snapshot_before_promotion(self) -> None:
        snapshot_cases = (
            "config_snapshot",
            "ex5_snapshot",
            "tester_ex5",
            "include_one",
        )
        for path_attribute in snapshot_cases:
            with self.subTest(snapshot=path_attribute), tempfile.TemporaryDirectory() as tmp:
                fixture = ArtifactFixture(Path(tmp))
                fixture.configure_confirmed()
                evidence_path = getattr(fixture, path_attribute)
                evidence_path.write_bytes(evidence_path.read_bytes() + b"\ntampered")

                summary = unified_validation.evaluate_validation_gates(
                    str(fixture.report),
                    str(fixture.out_dir),
                    stage="confirmed",
                    variants_dir=str(fixture.variants_dir),
                )

                self.assertEqual(summary["gates"]["walk_forward"]["status"], "BLOCKED")
                self.assertEqual(summary["gates"]["cost_stress_x1_5"]["status"], "BLOCKED")

    def test_confirmed_identity_binds_ea_tester_and_git_state(self) -> None:
        identity_cases = (
            ("ea_name", "EA_Different"),
            ("tester_ex5_sha256", "f" * 64),
            ("git_commit", "b" * 40),
            ("git_status_sha256", "5" * 64),
        )
        for field, replacement in identity_cases:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                fixture = ArtifactFixture(Path(tmp))
                fixture.configure_confirmed()
                manifest = json.loads(fixture.manifest_path.read_text(encoding="utf-8"))
                manifest[field] = replacement
                fixture.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

                summary = unified_validation.evaluate_validation_gates(
                    str(fixture.report),
                    str(fixture.out_dir),
                    stage="confirmed",
                    variants_dir=str(fixture.variants_dir),
                )

                for gate_name in (
                    "cost_stress_x1_5",
                    "walk_forward",
                    "pbo",
                    "white_reality_check",
                ):
                    self.assertEqual(summary["gates"][gate_name]["status"], "BLOCKED")

    def test_confirmed_does_not_reuse_stale_variant_artifacts_without_variants_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = ArtifactFixture(Path(tmp))
            fixture.configure_confirmed()

            summary = unified_validation.evaluate_validation_gates(
                str(fixture.report), str(fixture.out_dir), stage="confirmed"
            )
            owned = unified_validation._invocation_owned_artifacts(
                fixture.out_dir,
                stage="confirmed",
                variants_dir="",
            )

            self.assertEqual(summary["gates"]["pbo"]["status"], "BLOCKED")
            self.assertEqual(summary["gates"]["white_reality_check"]["status"], "BLOCKED")
            self.assertIn("nonempty variants_dir", summary["gates"]["pbo"]["reason"])
            self.assertIn("pbo", owned)
            self.assertIn("white_reality_check", owned)

    def test_confirmed_rejects_variant_family_hash_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = ArtifactFixture(Path(tmp))
            fixture.configure_confirmed()
            variant_path = fixture.variants_dir / "variant_a.csv"
            variant_path.write_text("month,pnl\n2024-01,999\n", encoding="utf-8")

            summary = unified_validation.evaluate_validation_gates(
                str(fixture.report),
                str(fixture.out_dir),
                stage="confirmed",
                variants_dir=str(fixture.variants_dir),
            )

            for gate_name in ("pbo", "white_reality_check"):
                gate = summary["gates"][gate_name]
                self.assertEqual(gate["status"], "BLOCKED")
                self.assertFalse(gate["actual"]["binding"]["variants_sha256_match"])

    def test_confirmed_blocks_missing_or_single_variant_family(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = ArtifactFixture(Path(tmp))
            fixture.configure_confirmed()
            fixture.write("cscv_pbo.json", {"n_variants": 1, "combos_used": 1, "pbo": 0.01})
            (fixture.out_dir / "white_reality_check.json").unlink()

            summary = unified_validation.evaluate_validation_gates(
                str(fixture.report),
                str(fixture.out_dir),
                stage="confirmed",
                variants_dir=str(fixture.variants_dir),
            )

            self.assertEqual(summary["gates"]["pbo"]["status"], "BLOCKED")
            self.assertEqual(summary["gates"]["white_reality_check"]["status"], "BLOCKED")
            self.assertEqual(summary["verdict"], "REVIEW")

    def test_confirmed_fails_closed_on_missing_required_artifacts(self) -> None:
        artifact_to_gate = {
            "sonic_cost_stress_fixture.json": "cost_stress_x1_5",
            "equity_audit.json": "equity_audit",
            "overnight_exposure.json": "overnight_weekend_exposure",
            "slippage_summary.json": "execution_reconciliation",
        }
        for artifact_name, gate_name in artifact_to_gate.items():
            with self.subTest(artifact=artifact_name), tempfile.TemporaryDirectory() as tmp:
                fixture = ArtifactFixture(Path(tmp))
                fixture.configure_confirmed()
                (fixture.out_dir / artifact_name).unlink()

                summary = unified_validation.evaluate_validation_gates(
                    str(fixture.report),
                    str(fixture.out_dir),
                    stage="confirmed",
                    variants_dir=str(fixture.variants_dir),
                )

                self.assertEqual(summary["gates"][gate_name]["status"], "BLOCKED")
                self.assertEqual(summary["verdict"], "REVIEW")

    def test_pf_rich_report_only_cost_proxy_is_diagnostic_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = ArtifactFixture(Path(tmp))
            fixture.write(
                "sonic_cost_stress_fixture.json",
                {
                    "schema_version": "sonic_cost_stress.v1",
                    "stress_mode": "report_only_cost_stress",
                    "report": str(fixture.report),
                    "net_r_x1_5": 89.0,
                    "scenarios": [
                        {
                            "scenario": "cost_x1_00",
                            "cost_multiplier": 1.0,
                            "profit_factor": 10.0,
                            "loss_count": 1,
                            "sum_positive_net_r": 100.0,
                            "sum_negative_net_r": -10.0,
                        },
                        {
                            "scenario": "cost_x1_50",
                            "cost_multiplier": 1.5,
                            "profit_factor": 9.9,
                            "loss_count": 1,
                            "sum_positive_net_r": 99.0,
                            "sum_negative_net_r": -10.0,
                        },
                        {
                            "scenario": "cost_x2_00",
                            "cost_multiplier": 2.0,
                            "profit_factor": 8.8,
                            "loss_count": 1,
                            "sum_positive_net_r": 88.0,
                            "sum_negative_net_r": -10.0,
                        },
                    ],
                    "cost_assumption": {
                        "note": "Report-only fixed-dollar proxy; not broker execution proof."
                    },
                },
            )

            summary = unified_validation.evaluate_validation_gates(
                str(fixture.report), str(fixture.out_dir), stage="challenger"
            )

            for gate_name, expected_pf in (
                ("cost_stress_x1_5", 9.9),
                ("cost_stress_x2", 8.8),
            ):
                gate = summary["gates"][gate_name]
                self.assertEqual(gate["status"], "BLOCKED")
                self.assertEqual(gate["actual"]["profit_factor"], expected_pf)
                self.assertIn("provenance", gate["reason"].lower())

    def test_verified_cost_schema_fails_closed_when_required_proof_is_incomplete(self) -> None:
        invalid_cases = (
            (("provenance_status",), "PENDING", "provenance_status"),
            (("provenance_status",), "verified", "provenance_status"),
            (("schema_version",), "sonic_cost_stress.v1", "schema_version"),
            (("execution_provenance", "broker"), "", "broker"),
            (("execution_provenance", "server"), "", "server"),
            (("execution_provenance", "broker_fingerprint"), "", "broker_fingerprint"),
            (("execution_provenance", "server_fingerprint"), "", "server_fingerprint"),
            (("execution_provenance", "account_fingerprint"), "", "account"),
            (("execution_provenance", "data_fingerprint"), "", "data_fingerprint"),
            (("execution_provenance", "symbol"), "", "symbol"),
            (("execution_provenance", "historical_spread", "source"), "", "historical_spread.source"),
            (("execution_provenance", "historical_spread", "sha256"), "not-a-hash", "historical_spread.sha256"),
            (("execution_provenance", "historical_spread", "verification_status"), "verified", "verification_status"),
            (("execution_provenance", "commission", "source"), "", "commission.source"),
            (("execution_provenance", "commission", "value"), None, "commission.value"),
            (("execution_provenance", "slippage", "source"), "", "slippage.source"),
            (("execution_provenance", "slippage", "sample_count"), 0, "slippage.sample_count"),
            (("execution_provenance", "slippage", "p90_roundturn"), None, "p90_roundturn"),
            (("execution_provenance", "cost_methodology", "direction_aware"), False, "direction_aware"),
            (("execution_provenance", "cost_methodology", "description"), "", "methodology.description"),
        )

        for field_path, invalid_value, reason_fragment in invalid_cases:
            with self.subTest(field=".".join(field_path)), tempfile.TemporaryDirectory() as tmp:
                fixture = ArtifactFixture(Path(tmp))
                artifact_path = fixture.out_dir / "sonic_cost_stress_fixture.json"
                payload = json.loads(artifact_path.read_text(encoding="utf-8"))
                target = payload
                for key in field_path[:-1]:
                    target = target[key]
                target[field_path[-1]] = invalid_value
                artifact_path.write_text(json.dumps(payload), encoding="utf-8")

                summary = unified_validation.evaluate_validation_gates(
                    str(fixture.report), str(fixture.out_dir), stage="challenger"
                )

                gate = summary["gates"]["cost_stress_x1_5"]
                self.assertEqual(gate["status"], "BLOCKED")
                self.assertIn(reason_fragment, gate["reason"])

        with tempfile.TemporaryDirectory() as tmp:
            fixture = ArtifactFixture(Path(tmp))
            payload = json.loads(fixture.cost_path.read_text(encoding="utf-8"))
            evidence = payload["execution_provenance"]
            commission = evidence["commission"]
            commission["broker_contract"] = {
                "source": str(fixture.broker_contract_source),
                "sha256": sha256_file(fixture.broker_contract_source),
                "broker_fingerprint": evidence["broker_fingerprint"],
                "server_fingerprint": evidence["server_fingerprint"],
                "account_fingerprint": evidence["account_fingerprint"],
                "symbol": evidence["symbol"],
                "account_currency": "USD",
                "per_lot_basis": True,
                "round_turn_account_per_lot": 0.0,
                "from": evidence["from"],
                "to": evidence["to"],
                "conversion_method": "per_trade_contemporaneous",
                "description": "Invalid zero commission contract.",
            }
            fixture.cost_path.write_text(json.dumps(payload), encoding="utf-8")

            summary = unified_validation.evaluate_validation_gates(
                str(fixture.report), str(fixture.out_dir), stage="challenger"
            )

            gate = summary["gates"]["cost_stress_x1_5"]
            self.assertEqual(gate["status"], "BLOCKED")
            self.assertIn("round_turn_account_per_lot", gate["reason"])

    def test_verified_cost_rejects_fake_source_self_attestation_and_hash_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = ArtifactFixture(Path(tmp))
            payload = json.loads(fixture.cost_path.read_text(encoding="utf-8"))
            spread = payload["execution_provenance"]["historical_spread"]
            spread["source"] = str(fixture.evidence_dir / "missing_spread.json")
            spread["sha256"] = "a" * 64
            fixture.cost_path.write_text(json.dumps(payload), encoding="utf-8")

            summary = unified_validation.evaluate_validation_gates(
                str(fixture.report), str(fixture.out_dir), stage="challenger"
            )
            reason = summary["gates"]["cost_stress_x1_5"]["reason"]
            self.assertIn("historical_spread.source does not exist", reason)

        with tempfile.TemporaryDirectory() as tmp:
            fixture = ArtifactFixture(Path(tmp))
            fixture.spread_source.write_text("tampered after attestation", encoding="utf-8")

            summary = unified_validation.evaluate_validation_gates(
                str(fixture.report), str(fixture.out_dir), stage="challenger"
            )
            reason = summary["gates"]["cost_stress_x1_5"]["reason"]
            self.assertIn("historical_spread.sha256 mismatch", reason)

    def test_verified_cost_binds_execution_identity_to_run_manifest(self) -> None:
        invalid_cases = (
            ("broker_fingerprint", "f" * 64),
            ("server_fingerprint", "a" * 64),
            ("account_fingerprint", "d" * 64),
            ("data_fingerprint", "e" * 64),
            ("symbol", "EURUSD"),
            ("from", "2023.01.01"),
            ("to", "2025.01.01"),
        )
        for field, invalid_value in invalid_cases:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                fixture = ArtifactFixture(Path(tmp))
                payload = json.loads(fixture.cost_path.read_text(encoding="utf-8"))
                payload["execution_provenance"][field] = invalid_value
                fixture.cost_path.write_text(json.dumps(payload), encoding="utf-8")

                summary = unified_validation.evaluate_validation_gates(
                    str(fixture.report), str(fixture.out_dir), stage="challenger"
                )
                reason = summary["gates"]["cost_stress_x1_5"]["reason"]
                self.assertIn(f"{field} does not match run manifest", reason)

    def test_verified_cost_requires_adequate_spread_commission_and_slippage_evidence(self) -> None:
        invalid_cases = (
            (("historical_spread", "coverage", "coverage_ratio"), 0.04, "coverage_ratio"),
            (("commission", "sample_count"), 2, "commission.sample_count"),
            (("slippage", "sample_count"), 20, "slippage.sample_count"),
            (("slippage", "method"), "", "slippage.method"),
            (("slippage", "independent_reference"), False, "independent_reference"),
        )
        for field_path, invalid_value, reason_fragment in invalid_cases:
            with self.subTest(field=".".join(field_path)), tempfile.TemporaryDirectory() as tmp:
                fixture = ArtifactFixture(Path(tmp))
                payload = json.loads(fixture.cost_path.read_text(encoding="utf-8"))
                target = payload["execution_provenance"]
                for key in field_path[:-1]:
                    target = target[key]
                target[field_path[-1]] = invalid_value
                fixture.cost_path.write_text(json.dumps(payload), encoding="utf-8")

                summary = unified_validation.evaluate_validation_gates(
                    str(fixture.report), str(fixture.out_dir), stage="challenger"
                )
                reason = summary["gates"]["cost_stress_x1_5"]["reason"]
                self.assertIn(reason_fragment, reason)

    def test_verified_cost_requires_side_specific_slippage_evidence(self) -> None:
        invalid_cases = (
            ("buy_count", 29, "buy_count"),
            ("sell_count", 29, "sell_count"),
            ("p90_buy", None, "p90_buy"),
            ("p90_sell", None, "p90_sell"),
            ("p90_roundturn", 1.6, "p90_roundturn"),
            ("buy_reference_side", "bid", "buy_reference_side"),
            ("sell_reference_side", "ask", "sell_reference_side"),
        )
        for field, invalid_value, reason_fragment in invalid_cases:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                fixture = ArtifactFixture(Path(tmp))
                payload = json.loads(fixture.cost_path.read_text(encoding="utf-8"))
                payload["execution_provenance"]["slippage"][field] = invalid_value
                fixture.cost_path.write_text(json.dumps(payload), encoding="utf-8")

                summary = unified_validation.evaluate_validation_gates(
                    str(fixture.report), str(fixture.out_dir), stage="challenger"
                )

                gate = summary["gates"]["cost_stress_x1_5"]
                self.assertEqual(gate["status"], "BLOCKED")
                self.assertIn(reason_fragment, gate["reason"])

        with tempfile.TemporaryDirectory() as tmp:
            fixture = ArtifactFixture(Path(tmp))
            payload = json.loads(fixture.cost_path.read_text(encoding="utf-8"))
            slippage = payload["execution_provenance"]["slippage"]
            slippage["buy_count"] = 100
            slippage["sell_count"] = 100
            fixture.cost_path.write_text(json.dumps(payload), encoding="utf-8")

            summary = unified_validation.evaluate_validation_gates(
                str(fixture.report), str(fixture.out_dir), stage="challenger"
            )
            reason = summary["gates"]["cost_stress_x1_5"]["reason"]
            self.assertIn("sample_count must equal buy_count + sell_count", reason)

    def test_verified_cost_accepts_zero_side_p90_when_sample_evidence_is_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = ArtifactFixture(Path(tmp))
            with fixture.slippage_source.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            for row in rows:
                row["fill_price"] = row["reference_price"]
            write_csv(fixture.slippage_source, list(rows[0]), rows)
            source = json.loads(fixture.cost_source_manifest.read_text(encoding="utf-8"))
            slippage = source["slippage_provenance"]
            slippage["source_sha256"] = sha256_file(fixture.slippage_source)
            slippage["p90_buy"] = 0.0
            slippage["p90_sell"] = 0.0
            slippage["p90_roundturn"] = 0.0
            fixture.cost_source_manifest.write_text(json.dumps(source), encoding="utf-8")
            fixture.cost_path.write_text(
                json.dumps(verified_cost_builder.build(fixture.report, fixture.cost_source_manifest)),
                encoding="utf-8",
            )

            summary = unified_validation.evaluate_validation_gates(
                str(fixture.report), str(fixture.out_dir), stage="challenger"
            )

            self.assertEqual(summary["gates"]["cost_stress_x1_5"]["status"], "PASS")

    def test_verified_cost_accepts_exact_spread_coverage_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = ArtifactFixture(Path(tmp))
            with fixture.spread_source.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            for row in rows[:10]:
                row["ask"] = ""
            write_csv(fixture.spread_source, list(rows[0]), rows)
            source = json.loads(fixture.cost_source_manifest.read_text(encoding="utf-8"))
            spread = source["historical_spread_provenance"]
            spread["source_sha256"] = sha256_file(fixture.spread_source)
            coverage = spread["coverage"]
            coverage["sample_count"] = 990
            coverage["total_count"] = 1000
            coverage["coverage_ratio"] = 0.99
            fixture.cost_source_manifest.write_text(json.dumps(source), encoding="utf-8")
            fixture.cost_path.write_text(
                json.dumps(verified_cost_builder.build(fixture.report, fixture.cost_source_manifest)),
                encoding="utf-8",
            )

            summary = unified_validation.evaluate_validation_gates(
                str(fixture.report), str(fixture.out_dir), stage="challenger"
            )

            self.assertEqual(summary["gates"]["cost_stress_x1_5"]["status"], "PASS")

    def test_verified_cost_accepts_hash_bound_commission_contract_as_true_alternative(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = ArtifactFixture(Path(tmp))
            source = json.loads(fixture.cost_source_manifest.read_text(encoding="utf-8"))
            commission = source["commission_provenance"]
            for field in ("source", "source_sha256", "method", "statistic", "sample_count", "same_symbol_lifecycles"):
                commission.pop(field, None)
            commission["broker_contract"] = {
                "source": str(fixture.broker_contract_source),
                "source_sha256": sha256_file(fixture.broker_contract_source),
                "broker_fingerprint": source["broker_fingerprint"],
                "server_fingerprint": source["server_fingerprint"],
                "account_fingerprint": source["account_fingerprint"],
                "symbol": source["symbol"],
                "account_currency": "USD",
                "per_lot_basis": True,
                "round_turn_account_per_lot": 7.0,
                "from": source["from"],
                "to": source["to"],
                "conversion_method": "per_trade_contemporaneous",
                "description": "Published USD 7.00 round-turn commission contract.",
            }
            fixture.cost_source_manifest.write_text(json.dumps(source), encoding="utf-8")
            fixture.cost_path.write_text(
                json.dumps(verified_cost_builder.build(fixture.report, fixture.cost_source_manifest)),
                encoding="utf-8",
            )

            summary = unified_validation.evaluate_validation_gates(
                str(fixture.report), str(fixture.out_dir), stage="challenger"
            )

            self.assertEqual(summary["gates"]["cost_stress_x1_5"]["status"], "PASS")

    def test_verified_cost_broker_contract_binds_full_account_and_conversion_identity(self) -> None:
        invalid_cases = (
            ("broker", "broker_fingerprint", "f" * 64, "broker_fingerprint"),
            ("server", "server_fingerprint", "f" * 64, "server_fingerprint"),
            ("account", "account_fingerprint", "f" * 64, "account_fingerprint"),
            ("symbol", "symbol", "EURUSD", "symbol"),
            ("currency", "account_currency", "EUR", "account_currency"),
            ("per_lot", "per_lot_basis", False, "per_lot_basis"),
            (
                "round_turn_zero",
                "round_turn_account_per_lot",
                0.0,
                "round_turn_account_per_lot must be finite and > 0",
            ),
            (
                "round_turn_mismatch",
                "round_turn_account_per_lot",
                8.0,
                "round_turn_account_per_lot must equal commission.value",
            ),
            ("from", "from", "2023.01.01", "from"),
            ("to", "to", "2026.12.31", "to"),
            ("conversion", "conversion_method", "fixed_snapshot", "conversion_method"),
        )
        for label, field, invalid_value, reason_fragment in invalid_cases:
            with self.subTest(case=label), tempfile.TemporaryDirectory() as tmp:
                fixture = ArtifactFixture(Path(tmp))
                payload = json.loads(fixture.cost_path.read_text(encoding="utf-8"))
                evidence = payload["execution_provenance"]
                commission = evidence["commission"]
                commission.pop("source")
                commission.pop("sha256")
                commission["sample_count"] = 0
                commission["same_symbol_lifecycles"] = False
                commission["broker_contract"] = {
                    "source": str(fixture.broker_contract_source),
                    "sha256": sha256_file(fixture.broker_contract_source),
                    "broker_fingerprint": evidence["broker_fingerprint"],
                    "server_fingerprint": evidence["server_fingerprint"],
                    "account_fingerprint": evidence["account_fingerprint"],
                    "symbol": evidence["symbol"],
                    "account_currency": "USD",
                    "per_lot_basis": True,
                    "round_turn_account_per_lot": 7.0,
                    "from": evidence["from"],
                    "to": evidence["to"],
                    "conversion_method": "per_trade_contemporaneous",
                    "description": "Published USD 7.00 round-turn commission contract.",
                }
                commission["broker_contract"][field] = invalid_value
                fixture.cost_path.write_text(json.dumps(payload), encoding="utf-8")

                summary = unified_validation.evaluate_validation_gates(
                    str(fixture.report), str(fixture.out_dir), stage="challenger"
                )

                gate = summary["gates"]["cost_stress_x1_5"]
                self.assertEqual(gate["status"], "BLOCKED")
                self.assertIn(reason_fragment, gate["reason"])

    def test_verified_cost_binds_exact_symbol_geometry_and_pip_unit(self) -> None:
        invalid_cases = (
            ("cost_missing_digits", "cost_geometry", "digits", None, True, "symbol_geometry.digits"),
            ("cost_point_mismatch", "cost_geometry", "point", 0.001, False, "symbol_geometry.point"),
            ("manifest_missing_pip", "manifest_geometry", "pip_size", None, True, "fingerprint_basis.pip_size"),
            ("manifest_digits_mismatch", "manifest_geometry", "digits", 3, False, "symbol_geometry.digits"),
            ("missing_unit", "slippage", "slippage_unit", None, True, "slippage_unit"),
            ("wrong_unit", "slippage", "slippage_unit", "points", False, "slippage_unit"),
        )
        for label, target_name, field, value, remove, reason_fragment in invalid_cases:
            with self.subTest(case=label), tempfile.TemporaryDirectory() as tmp:
                fixture = ArtifactFixture(Path(tmp))
                manifest = json.loads(fixture.manifest_path.read_text(encoding="utf-8"))
                cost = json.loads(fixture.cost_path.read_text(encoding="utf-8"))
                targets = {
                    "cost_geometry": cost["execution_provenance"]["symbol_geometry"],
                    "manifest_geometry": manifest["fingerprint_basis"],
                    "slippage": cost["execution_provenance"]["slippage"],
                }
                target = targets[target_name]
                if remove:
                    target.pop(field)
                else:
                    target[field] = value
                fixture.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                fixture.cost_path.write_text(json.dumps(cost), encoding="utf-8")

                summary = unified_validation.evaluate_validation_gates(
                    str(fixture.report), str(fixture.out_dir), stage="challenger"
                )

                gate = summary["gates"]["cost_stress_x1_5"]
                self.assertEqual(gate["status"], "BLOCKED")
                self.assertIn(reason_fragment, gate["reason"])

    def test_cost_scenarios_require_exact_unique_label_and_multiplier(self) -> None:
        cases = ("alias", "conflict", "duplicate", "missing_multiplier")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                fixture = ArtifactFixture(Path(tmp))
                payload = json.loads(fixture.cost_path.read_text(encoding="utf-8"))
                scenarios = payload["scenarios"]
                x1_5 = next(row for row in scenarios if row["scenario"] == "cost_x1_50")
                if case == "alias":
                    x1_5["scenario"] = "alias_x1_50"
                elif case == "conflict":
                    x1_5["cost_multiplier"] = 2.0
                elif case == "duplicate":
                    scenarios.append(dict(x1_5))
                else:
                    x1_5.pop("cost_multiplier")
                fixture.cost_path.write_text(json.dumps(payload), encoding="utf-8")

                summary = unified_validation.evaluate_validation_gates(
                    str(fixture.report), str(fixture.out_dir), stage="challenger"
                )

                self.assertEqual(summary["gates"]["cost_stress_x1_5"]["status"], "BLOCKED")

        with tempfile.TemporaryDirectory() as tmp:
            fixture = ArtifactFixture(Path(tmp))
            payload = json.loads(fixture.cost_path.read_text(encoding="utf-8"))
            scenario = next(
                row for row in payload["scenarios"] if row["scenario"] == "cost_x1_50"
            )
            scenario.update(
                {
                    "profit_factor": 1.333333,
                    "sum_positive_net_r": 4.0,
                    "sum_negative_net_r": -3.0,
                }
            )
            payload["net_r_x1_5"] = 1.0
            fixture.cost_path.write_text(json.dumps(payload), encoding="utf-8")
            summary = unified_validation.evaluate_validation_gates(
                str(fixture.report), str(fixture.out_dir), stage="challenger"
            )
            self.assertEqual(summary["gates"]["cost_stress_x1_5"]["status"], "BLOCKED")
            self.assertIn(
                "canonical raw-evidence rebuild",
                summary["gates"]["cost_stress_x1_5"]["reason"],
            )

    def test_cost_scenarios_recompute_profit_factor_and_require_real_losses(self) -> None:
        invalid_cases = (
            ("self_declared_pf", "profit_factor", 9.9, False),
            ("zero_loss_count", "loss_count", 0, False),
            ("zero_negative_sum", "sum_negative_net_r", 0.0, False),
            ("missing_positive_sum", "sum_positive_net_r", None, True),
        )
        for label, field, value, remove in invalid_cases:
            with self.subTest(case=label), tempfile.TemporaryDirectory() as tmp:
                fixture = ArtifactFixture(Path(tmp))
                payload = json.loads(fixture.cost_path.read_text(encoding="utf-8"))
                scenario = next(
                    row for row in payload["scenarios"] if row["scenario"] == "cost_x1_50"
                )
                if remove:
                    scenario.pop(field)
                else:
                    scenario[field] = value
                fixture.cost_path.write_text(json.dumps(payload), encoding="utf-8")

                summary = unified_validation.evaluate_validation_gates(
                    str(fixture.report), str(fixture.out_dir), stage="challenger"
                )

                self.assertEqual(summary["gates"]["cost_stress_x1_5"]["status"], "BLOCKED")

    def test_verified_cost_requires_positive_recomputed_net_r_x1_5(self) -> None:
        invalid_cases = (
            ("missing", None, True),
            ("negative", -1.0, False),
            ("scenario_mismatch", 4.0, False),
        )
        for label, value, remove in invalid_cases:
            with self.subTest(case=label), tempfile.TemporaryDirectory() as tmp:
                fixture = ArtifactFixture(Path(tmp))
                payload = json.loads(fixture.cost_path.read_text(encoding="utf-8"))
                if remove:
                    payload.pop("net_r_x1_5")
                else:
                    payload["net_r_x1_5"] = value
                fixture.cost_path.write_text(json.dumps(payload), encoding="utf-8")

                summary = unified_validation.evaluate_validation_gates(
                    str(fixture.report), str(fixture.out_dir), stage="challenger"
                )

                gate = summary["gates"]["cost_stress_x1_5"]
                self.assertEqual(gate["status"], "BLOCKED")
                self.assertIn("net_r_x1_5", gate["reason"])

    def test_confirmed_stability_fails_closed_when_monthly_evidence_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = ArtifactFixture(Path(tmp))
            fixture.configure_confirmed()
            (fixture.out_dir / "monthly_fitness.json").unlink()

            summary = unified_validation.evaluate_validation_gates(
                str(fixture.report),
                str(fixture.out_dir),
                stage="confirmed",
                variants_dir=str(fixture.variants_dir),
            )

            for gate_name in ("monthly_stability", "half_year_stability", "year_stability"):
                self.assertEqual(summary["gates"][gate_name]["status"], "BLOCKED")
            self.assertEqual(summary["verdict"], "REVIEW")

    def test_confirmed_enforces_month_half_year_year_stability_and_concentration(self) -> None:
        cases: list[tuple[str, dict[str, float], str]] = []

        weak_months = {
            f"{year:04d}-{month:02d}": (100.0 if index < 35 else -10.0)
            for index, (year, month) in enumerate(
                (year, month) for year in range(2019, 2026) for month in range(1, 13)
            )
        }
        cases.append(("weak_months", weak_months, "monthly_stability"))

        weak_half_years = {
            f"{year:04d}-{month:02d}": (
                100.0 if ((year - 2019) * 2 + (0 if month <= 6 else 1)) < 8 else -20.0
            )
            for year in range(2019, 2026)
            for month in range(1, 13)
        }
        cases.append(("weak_half_years", weak_half_years, "half_year_stability"))

        weak_years = {
            f"{year:04d}-{month:02d}": (
                10.0 if year <= 2021 or month <= 6 else -20.0
            )
            for year in range(2019, 2026)
            for month in range(1, 13)
        }
        cases.append(("weak_years", weak_years, "year_stability"))

        concentrated_year = {
            f"{year:04d}-{month:02d}": (1000.0 if year == 2019 else 10.0)
            for year in range(2019, 2026)
            for month in range(1, 13)
        }
        cases.append(("concentrated_year", concentrated_year, "year_stability"))

        for label, month_values, expected_gate in cases:
            with self.subTest(case=label), tempfile.TemporaryDirectory() as tmp:
                fixture = ArtifactFixture(Path(tmp))
                fixture.configure_confirmed(month_values)
                summary = unified_validation.evaluate_validation_gates(
                    str(fixture.report),
                    str(fixture.out_dir),
                    stage="confirmed",
                    variants_dir=str(fixture.variants_dir),
                )

                self.assertEqual(summary["gates"][expected_gate]["status"], "FAIL")
                self.assertEqual(summary["verdict"], "REVIEW")

    def test_zero_or_missing_manifest_span_blocks_cadence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = ArtifactFixture(Path(tmp))
            manifest_path = fixture.run_dir / "run_manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["to"] = manifest["from"]
            manifest_path.write_text(json.dumps(manifest))

            summary = unified_validation.evaluate_validation_gates(
                str(fixture.report), str(fixture.out_dir), stage="challenger"
            )

            self.assertEqual(summary["gates"]["cadence"]["status"], "BLOCKED")


class RegistrySchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry_dir = ROOT / "03. EA Developer" / "EA_SonicR" / "research"
        cls.schema = json.loads(
            (cls.registry_dir / "CANDIDATE_REGISTRY.schema.json").read_text(
                encoding="utf-8-sig"
            )
        )
        cls.rows = [
            json.loads(line)
            for line in (
                cls.registry_dir / "CANDIDATE_REGISTRY.jsonl"
            ).read_text(encoding="utf-8-sig").splitlines()
            if line.strip()
        ]

    def test_whole_registry_validates_including_nonpromotable_legacy_results(self) -> None:
        self.assertEqual(len(self.rows), 54)
        for row in self.rows:
            with self.subTest(
                record_type=row.get("record_type"),
                hypothesis_id=row.get("hypothesis_id"),
            ):
                jsonschema.validate(row, self.schema)

    def test_confirmed_candidate_rejects_missing_or_out_of_range_cadence(self) -> None:
        row = json.loads(json.dumps(self.rows[-1]))
        row["state"] = "confirmed"
        row["verdict"] = "confirm"
        row["metrics"].update(
            {
                "trades": 150,
                "elapsed_days": 365,
                "elapsed_calendar_weeks": 365 / 7,
                "trades_per_elapsed_week": 3.0,
                "cost_pf_x1": 1.31,
                "cost_pf_x1_5": 1.25,
                "cost_pf_x2": 1.0,
                "net_r_x1_5": 1.0,
            }
        )
        for label, cadence in (
            ("null", None),
            ("below", 0.0),
            ("above", 999.0),
        ):
            invalid = json.loads(json.dumps(row))
            invalid["metrics"]["trades_per_elapsed_week"] = cadence
            with self.subTest(case=label), self.assertRaises(
                jsonschema.ValidationError
            ):
                jsonschema.validate(invalid, self.schema)

    def test_legacy_candidate_result_cannot_claim_confirmed_state(self) -> None:
        row = next(
            json.loads(json.dumps(item))
            for item in self.rows
            if item.get("record_type") == "candidate_result"
        )
        row["state"] = "confirmed"
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(row, self.schema)


if __name__ == "__main__":
    unittest.main()
