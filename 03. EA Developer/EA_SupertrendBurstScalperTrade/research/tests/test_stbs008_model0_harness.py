from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
RESEARCH = ROOT / "03. EA Developer/EA_SupertrendBurstScalperTrade/research"
BUILDER = RESEARCH / "build_stbs008_model0_packet.py"
RUNNER = RESEARCH / "run_stbs008_model0_train.py"
PREREG = RESEARCH / "HYP-STBS-XAUUSD-M15-008_MODEL0_EXECUTION_PREREG.md"


class Stbs008HarnessContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.builder = BUILDER.read_text(encoding="utf-8")
        cls.runner = RUNNER.read_text(encoding="utf-8")
        cls.prereg = PREREG.read_text(encoding="utf-8")
        ast.parse(cls.builder)
        ast.parse(cls.runner)

    def test_fresh_outer_and_frozen_inner_identity(self) -> None:
        for source in (self.builder, self.runner, self.prereg):
            self.assertIn("HYP-STBS-XAUUSD-M15-008", source)
            self.assertIn("HYP-STBS-XAUUSD-M15-007", source)

    def test_packet_claim_precedes_all_bound_reads(self) -> None:
        main = self.builder[self.builder.index("def main()") :]
        self.assertLess(main.index("marker = claim_packet()"), main.index("build_packet(marker)"))
        self.assertIn("PACKET_ROOT.mkdir(parents=True, exist_ok=False)", self.builder)
        self.assertIn('with path.open("xb")', self.builder)
        self.assertIn("os.fsync(handle.fileno())", self.builder)
        self.assertEqual(self.builder.count("REGISTRY.read_bytes()"), 1)
        self.assertIn("validate_packet_authority(registry_raw)", self.builder)
        self.assertIn("write_exclusive(SNAPSHOT, registry_raw)", self.builder)

    def test_runner_claim_precedes_authority_and_receipt_reads(self) -> None:
        main = self.runner[self.runner.index("def main()") :]
        self.assertLess(main.index("marker = claim(declared)"),
                        main.index("validate_after_claim(marker, declared)"))
        preclaim = main[: main.index("marker = claim(declared)")]
        self.assertNotIn("sha_file(ALPHA)", preclaim)
        self.assertNotIn("RECEIPT.read_", preclaim)
        self.assertNotIn("latest_row(", preclaim)

    def test_exact_two_stage_attempts(self) -> None:
        for source in (self.builder, self.runner, self.prereg):
            self.assertIn("STBS008-PACKET-BUILD-001", source)
            self.assertIn("STBS008-MODEL0-TRAIN-001", source)
        self.assertIn('metrics.get("packet_build_attempts_consumed") == 0', self.builder)
        self.assertIn('metrics.get("packet_build_attempts_consumed") == 1', self.runner)

    def test_full_compile_and_economic_run_authority(self) -> None:
        for field in (
            "run_compile_authorized", "mql5_compile_authorized",
            "trade_api_authorized", "performance_metrics_authorized",
            "outcome_prices_authorized", "economics_authorized",
        ):
            self.assertIn(field, self.builder)
            self.assertIn(field, self.runner)
        self.assertIn("RUN_TRUE_FIELDS", self.runner)
        self.assertIn("RUN_FALSE_FIELDS", self.runner)
        self.assertIn('metrics.get("model0_runs") == 0', self.runner)
        self.assertIn('metrics.get("mt5_launches") == 0', self.runner)
        self.assertIn('metrics.get("model0_runs") == 0', self.builder)
        self.assertIn('metrics.get("mt5_launches") == 0', self.builder)
        self.assertIn('row.get("acceptance_contract") == EXPECTED_ACCEPTANCE', self.runner)
        for alias in ("validation_access_authorized", "holdout_access_authorized"):
            self.assertIn(alias, self.builder)
            self.assertIn(alias, self.runner)

    def test_terminal_hyp007_is_exactly_bound(self) -> None:
        self.assertIn('hyp007.get("state") == "parked"', self.builder)
        self.assertIn('validation.get("hyp007_terminal_row_sha256")', self.builder)
        self.assertIn('"packet_build_attempts_consumed", "mt5_attempts_consumed"',
                      self.builder)
        self.assertIn("all(hyp007_metrics.get(name) == 0", self.builder)
        self.assertIn("HYP007_TERMINAL_FALSE_FIELDS", self.builder)

    def test_tools_are_receipt_evidence(self) -> None:
        self.assertIn('(\"packet_builder\", BUILDER)', self.builder)
        self.assertIn('(\"model0_launcher\", RUNNER)', self.builder)
        self.assertIn('validation.get("reviewed_packet_builder_sha256") == sha_file(BUILDER)',
                      self.builder)
        self.assertIn('validation.get("reviewed_model0_launcher_sha256") == sha_file(RUNNER)',
                      self.builder)

    def test_reserved_review_is_mutable_control_not_evidence(self) -> None:
        self.assertIn("RESERVED_NON_AUTHORITATIVE_PLACEHOLDER", self.builder)
        self.assertIn("reserved_mutable_control_paths", self.builder)
        self.assertIn("reserved review entered immutable evidence", self.builder)
        self.assertIn("PASS_SCREENED_AUTHORITY", self.runner)
        self.assertIn("live Git path set differs from sealed packet", self.runner)
        self.assertIn("review_raw = RESERVED_REVIEW.read_bytes()", self.runner)
        self.assertEqual(self.runner.count("RESERVED_REVIEW.read_bytes()"), 1)
        self.assertNotIn("RESERVED_REVIEW.read_text", self.runner)
        self.assertIn("review_text.startswith(review_prefix)", self.runner)

    def test_exact_alpha_invocation(self) -> None:
        for token in (
            '"backtest", "EA_SupertrendBurstScalperTrade"',
            '"-Symbol", "XAUUSD"', '"-Period", "M15"',
            '"-From", "2005.01.01"', '"-To", "2023.01.01"',
            '"-Model", "0"', '"-ExecutionMode", "0"',
            '"-FixedDelayMs", "0"', '"-RunRole", "control"',
            '"-TelemetryTier", "off"',
        ):
            self.assertIn(token, self.runner)
        self.assertNotIn('"-Spread"', self.runner)
        self.assertNotIn('"-Overrides"', self.runner)

    def test_no_promotion_or_retry(self) -> None:
        for source in (self.builder, self.runner):
            self.assertIn("same_id_retry_authorized", source)
            self.assertIn("registry_mutation_allowed", source)
            self.assertIn("promotion_eligible", source)
            self.assertIn("live_trading_authorized", source)


if __name__ == "__main__":
    unittest.main()
