import importlib.util
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[4]
RUNNER = ROOT / "03. EA Developer" / "EA_SupertrendBurstScalperTradeV4" / "research" / "run_stbs014_model0_audit.py"
SPEC = importlib.util.spec_from_file_location("stbs014_runner", RUNNER)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class Stbs014AuditRunnerTests(unittest.TestCase):
    def _journal(self, mutate=None):
        lines = []
        for index in range(690):
            exact = index >= 7
            direction = "LONG" if index < 7 + 339 else "SHORT"
            if exact:
                line = (
                    f"STBS_SIGNAL|source=s|decision=d|source_epoch={index}|decision_epoch={index+1}|"
                    f"direction={direction}|exact_next=true|atr_ready=true|geometry_ready=true|"
                    "margin_ready=true|atr=1|entry=1|sl=1|tp=1|volume=0.01|projected_level=9999|audit=true"
                )
            else:
                line = (
                    f"STBS_SIGNAL|source=s|decision=d|source_epoch={index}|decision_epoch={index+1}|"
                    f"direction={direction}|exact_next=false|consumed=true"
                )
            lines.extend([line, line])
        summary = (
            f"STBS_SUMMARY|hypothesis={MODULE.HYPOTHESIS_ID}|reason=0|raw=690|executable=683|gaps=7|"
            "long=339|short=344|atr_ready=683|geometry_ready=683|margin_ready=683|margin_rejects=0|"
            "margin_emergencies=0|forced_stopouts=0|entries=0|entry_rejects=0|closes=0|"
            "lifecycle_open_rows=0|lifecycle_final_close_rows=0|lifecycle_positions_opened=0|"
            "lifecycle_positions_final_closed=0|exec_state=0|exit_intent=0|failed=false"
        )
        lines.extend([summary, summary])
        if mutate:
            lines = mutate(lines)
        return "\n".join(lines)

    def _validate(self, content):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "journal.log"
            path.write_text(content, encoding="utf-8")
            return MODULE.validate_journal(path)

    def test_duplicate_journal_is_normalized(self):
        result = self._validate(self._journal())
        self.assertEqual(result["summary_multiplicity"], 2)
        self.assertEqual(result["signal_multiplicity"], 2)

    def test_nonidentical_duplicate_fails(self):
        def mutate(lines):
            lines[1] = lines[1].replace("consumed=true", "consumed=false")
            return lines
        with self.assertRaisesRegex(RuntimeError, "non-identical duplicate"):
            self._validate(self._journal(mutate))

    def test_any_order_gateway_marker_fails(self):
        with self.assertRaisesRegex(RuntimeError, "forbidden audit journal marker"):
            self._validate(self._journal() + "\nSTBS_ENTRY_REQUEST|decision=x")

    def test_margin_reject_false_pass_fails(self):
        def mutate(lines):
            return [line.replace("margin_ready=683", "margin_ready=682") for line in lines]
        with self.assertRaisesRegex(RuntimeError, "summary margin_ready"):
            self._validate(self._journal(mutate))

    def test_runner_freezes_audit_only_and_no_retry(self):
        source = RUNNER.read_text(encoding="utf-8")
        self.assertIn('"InpAuditOnly=true;"', source)
        self.assertNotIn('"InpAuditOnly=true;InpEnableTelemetry=', source)
        self.assertIn('"same_id_retry_authorized": False', source)
        self.assertIn("os.O_CREAT | os.O_EXCL", source)
        self.assertIn('"trade_api_authorized"', source)
        self.assertIn("assert_reserved_placeholders(latest)", source)

    def test_exact_empty_orders_shape(self):
        spans = MODULE.EXPECTED_ORDER_COLSPANS
        cells = "".join(
            f'<td{(" colspan=\"%d\"" % span) if span != 1 else ""}><b>H</b></td>'
            for span in spans
        )
        html = f"<b>Orders</b><tr>{cells}</tr><tr><td></td></tr><b>Deals</b>"
        self.assertTrue(MODULE.orders_section_is_empty(html))

    def test_exact_empty_vietnamese_orders_shape(self):
        spans = MODULE.EXPECTED_ORDER_COLSPANS
        cells = "".join(
            f'<td{(" colspan=\"%d\"" % span) if span != 1 else ""}><b>H</b></td>'
            for span in spans
        )
        html = f"<b>Các lệnh đặt</b><tr>{cells}</tr><tr><td></td></tr><b>Deals</b>"
        self.assertTrue(MODULE.orders_section_is_empty(html))

    def test_orders_shape_rejects_malformed_colspan(self):
        cells = '<td colspan=bad><b>H</b></td>' + "".join('<td><b>H</b></td>' for _ in range(10))
        html = f"<b>Orders</b><tr>{cells}</tr><tr><td></td></tr><b>Deals</b>"
        self.assertFalse(MODULE.orders_section_is_empty(html))

    def test_runner_archives_static_and_parses_captured_run_bytes(self):
        source = RUNNER.read_text(encoding="utf-8")
        self.assertIn("snapshot_static_review(latest)", source)
        self.assertIn('RUN_ARCHIVE_ROOT / "report.html"', source)
        self.assertIn("validate_journal_text(journal_raw.decode", source)
        self.assertIn('static_review["reviewed_quant_analyzer"]["archive_path"]', source)
        self.assertIn("run_ex5_sha != manifest.get(\"ex5_sha256\")", source)
        self.assertIn('run_log.get("zero_error_warning_result_count") != 1', source)

    def test_failure_path_captures_compile_and_run_delta_before_returncode(self):
        source = RUNNER.read_text(encoding="utf-8")
        capture_index = source.index("post_alpha_compile = capture_post_alpha_compile()")
        delta_index = source.index("run_set_delta = {")
        returncode_index = source.index("if completed.returncode != 0:")
        self.assertLess(capture_index, returncode_index)
        self.assertLess(delta_index, returncode_index)
        self.assertIn("failed_run_inventory = capture_created_run_inventory(created)", source)
        self.assertIn('failure["created_run_inventory"] = failed_run_inventory', source)


if __name__ == "__main__":
    unittest.main()
