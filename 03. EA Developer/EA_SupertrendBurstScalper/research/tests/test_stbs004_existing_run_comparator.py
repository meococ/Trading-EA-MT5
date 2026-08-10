from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
RESEARCH = ROOT / "03. EA Developer/EA_SupertrendBurstScalper/research"
COMPARATOR_PATH = RESEARCH / "compare_stbs004_existing_run.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CMP = load(COMPARATOR_PATH, "stbs004_comparator_under_test")


class Stbs004ExistingRunComparatorTests(unittest.TestCase):
    def test_ids_scope_and_attempt_root_are_fresh(self) -> None:
        self.assertEqual(CMP.HYPOTHESIS_ID, "HYP-STBS-XAUUSD-M15-004")
        self.assertEqual(CMP.FAILED_HYPOTHESIS_ID, "HYP-STBS-XAUUSD-M15-003")
        self.assertEqual(CMP.ATTEMPT_ID, "STBS004-COMPARATOR-001")
        self.assertFalse(CMP.OUTPUT_DIR.exists())
        self.assertNotIn("subprocess", COMPARATOR_PATH.read_text(encoding="utf-8"))

    def test_json_accepts_zero_or_one_leading_bom_only(self) -> None:
        raw = b'{"value":1}'
        self.assertEqual(CMP.decode_json(raw, "fixture"), {"value": 1})
        self.assertEqual(CMP.decode_json(CMP.BOM + raw, "fixture"), {"value": 1})
        for invalid in (
            CMP.BOM + CMP.BOM + raw,
            b'{"value":"' + CMP.BOM + b'"}',
            b"\xff\xfe{}",
            b'{"value":1,"value":2}',
        ):
            with self.subTest(invalid=invalid), self.assertRaises((ValueError, json.JSONDecodeError)):
                CMP.decode_json(invalid, "fixture")

    def test_strict_text_rejects_any_bom_and_invalid_utf8(self) -> None:
        self.assertEqual(CMP.decode_strict_utf8(b"ok", "fixture"), "ok")
        for invalid in (CMP.BOM + b"ok", b"x" + CMP.BOM, b"\xff"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                CMP.decode_strict_utf8(invalid, "fixture")

    def test_dual_clock_identity_uses_oracle_utc_and_server_axes(self) -> None:
        event = {
            "source_epoch": 1514952000,
            "next_source_epoch": 1514955600,
            "time_utc": "2018-01-03T02:00:00Z",
            "direction": "SHORT",
            "executable_event": 1,
        }
        next_row = {"time_utc": "2018-01-03T03:00:00Z"}
        signal = {
            "source_epoch": "1514944800",
            "decision_epoch": "1514948400",
            "source": "2018.01.03 04:00:00",
            "decision": "2018.01.03 05:00:00",
            "direction": "SHORT",
            "exact_next": "true",
        }
        self.assertTrue(all(CMP.event_identity_checks(signal, event, next_row).values()))
        for field, wrong in (
            ("source_epoch", "1514944801"),
            ("decision_epoch", "1514948401"),
            ("source", "2018.01.03 02:00:00"),
            ("decision", "2018.01.03 03:00:00"),
            ("direction", "LONG"),
            ("exact_next", "false"),
        ):
            mutated = dict(signal)
            mutated[field] = wrong
            with self.subTest(field=field):
                self.assertFalse(all(CMP.event_identity_checks(mutated, event, next_row).values()))

    def test_gap_uses_referenced_next_utc_not_one_hour_assumption(self) -> None:
        event = {
            "source_epoch": 1616191200,
            "next_source_epoch": 1616371200,
            "time_utc": "2021-03-19T20:00:00Z",
            "direction": "SHORT",
            "executable_event": 0,
        }
        next_row = {"time_utc": "2021-03-21T22:00:00Z"}
        signal = {
            "source_epoch": str(CMP.utc_epoch(event["time_utc"])),
            "decision_epoch": str(CMP.utc_epoch(next_row["time_utc"])),
            "source": CMP.server_text(event["source_epoch"]),
            "decision": CMP.server_text(event["next_source_epoch"]),
            "direction": "SHORT",
            "exact_next": "false",
        }
        self.assertTrue(all(CMP.event_identity_checks(signal, event, next_row).values()))

    def test_exact_outward_1atr_stop_and_1_5r_target_geometry(self) -> None:
        long_checks = CMP.geometry_contract_checks(
            "LONG", atr=2.16857143, entry=1320.02, stop=1317.85, target=1323.28
        )
        short_checks = CMP.geometry_contract_checks(
            "SHORT", atr=1.605, entry=1312.23, stop=1313.84, target=1309.81
        )
        self.assertTrue(all(long_checks.values()))
        self.assertTrue(all(short_checks.values()))
        for direction, atr, entry, stop, target in (
            ("LONG", 2.16857143, 1320.02, 1319.00, 1330.00),
            ("SHORT", 1.605, 1312.23, 1315.00, 1300.00),
            ("LONG", 2.16857143, 1320.02, 1317.85, 1325.00),
            ("SHORT", 1.605, 1312.23, 1313.84, 1308.00),
        ):
            with self.subTest(direction=direction, stop=stop, target=target):
                checks = CMP.geometry_contract_checks(
                    direction, atr, entry, stop, target
                )
                self.assertTrue(checks["sided"])
                self.assertFalse(all(checks.values()))

    def test_keyed_parser_rejects_duplicate_and_malformed_fields(self) -> None:
        parsed = CMP.parse_keyed_lines("prefix STBS_SIGNAL|a=1|b=2\n", "STBS_SIGNAL|")
        self.assertEqual(parsed, [{"record": "STBS_SIGNAL", "a": "1", "b": "2"}])
        for text in ("STBS_SIGNAL|a=1|a=2", "STBS_SIGNAL|broken"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                CMP.parse_keyed_lines(text, "STBS_SIGNAL|")

    def test_orders_shape_is_exact_and_malformed_colspan_fails(self) -> None:
        header = "".join(
            f"<td{' colspan=2' if span == 2 else ''}><b>H{i}</b></td>"
            for i, span in enumerate(CMP.EXPECTED_COLSPANS)
        )
        html = f"<b>Orders</b><tr>{header}</tr><tr><td></td></tr><b>Deals</b>"
        self.assertTrue(CMP.orders_section_is_empty(html))
        self.assertFalse(CMP.orders_section_is_empty(html.replace("<td><b>H0", "<td colspan=bad><b>H0")))
        self.assertFalse(CMP.orders_section_is_empty(html.replace("<tr><td></td></tr>", "<tr><td></td><td></td></tr>")))

    def test_static_binding_surface_is_complete_and_paths_are_unique(self) -> None:
        expected = {
            "hyp003_attempt_started", "hyp003_attempt_terminal",
            "hyp003_alpha_stdout", "hyp003_alpha_stderr",
            "hyp003_contract_receipt", "hyp003_failure", "hyp003_failure_review",
            "run_manifest", "run_manifest_duplicate", "report", "report_duplicate",
            "journal", "summary", "source_snapshot", "ex5_snapshot", "config",
            "config_duplicate", "config_snapshot", "overrides", "overrides_duplicate",
            "oracle",
        }
        self.assertEqual(set(CMP.STATIC_BINDINGS), expected)
        paths = [path.resolve() for path, _ in CMP.STATIC_BINDINGS.values()]
        self.assertEqual(len(paths), len(set(paths)))
        dynamic = {CMP.PREREG_PATH.resolve(), CMP.TEST_PATH.resolve(), CMP.REVIEW_PATH.resolve()}
        self.assertEqual(len(dynamic), 3)
        self.assertTrue(dynamic.isdisjoint(paths))
        self.assertTrue(all(ROOT.resolve() in path.parents for path in dynamic))

    def test_claim_precedes_every_external_binding_read(self) -> None:
        source = COMPARATOR_PATH.read_text(encoding="utf-8")
        claim = source.index("OUTPUT_DIR.mkdir(parents=True, exist_ok=False)")
        marker = source.index("write_exclusive(\n        started_path", claim)
        bound_loop = source.index("for label, (path, expected) in STATIC_BINDINGS.items()", marker)
        self.assertLess(claim, marker)
        self.assertLess(marker, bound_loop)

    def test_authority_surface_keeps_all_non_comparator_capabilities_false(self) -> None:
        required = {
            "mt5_authorized", "compile_authorized", "run_compile_authorized",
            "mql5_compile_authorized", "trade_api_authorized",
            "performance_metrics_authorized", "outcome_prices_authorized",
            "economics_authorized", "optimization_authorized",
            "validation_authorized", "holdout_authorized",
            "paper_trading_authorized", "live_trading_authorized",
            "same_id_retry_authorized", "registry_mutation_allowed",
        }
        self.assertTrue(required.issubset(CMP.FALSE_AUTHORITIES))
        source = COMPARATOR_PATH.read_text(encoding="utf-8")
        self.assertIn('"self_path": validation.get("reviewed_comparator_path")', source)
        self.assertIn('"test_path": validation.get("reviewed_test_path")', source)
        self.assertIn('"review_path": validation.get("independent_review_path")', source)
        self.assertNotIn("__PREREG_SHA256__", CMP.PREREG_SHA256)
        self.assertNotIn("__TEST_SHA256__", CMP.TEST_SHA256)

    def test_preregistration_precedes_authority_and_is_not_future(self) -> None:
        prereg = datetime.fromisoformat("2026-08-09T05:50:00+00:00")
        self.assertLessEqual(prereg, datetime.now(timezone.utc))

    def test_attempt_claim_is_exclusive_in_fixture_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "attempt"
            root.mkdir(parents=True, exist_ok=False)
            marker = root / "attempt_started.json"
            CMP.write_exclusive(marker, b"first")
            with self.assertRaises(FileExistsError):
                CMP.write_exclusive(marker, b"second")


if __name__ == "__main__":
    unittest.main()
