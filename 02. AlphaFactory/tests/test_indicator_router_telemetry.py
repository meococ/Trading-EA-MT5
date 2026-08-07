import csv
import importlib.util
import tempfile
import unittest
from datetime import date
from pathlib import Path


TOOL_PATH = Path(__file__).parents[1] / "tools" / "analyze_indicator_router_telemetry.py"
SPEC = importlib.util.spec_from_file_location("router_analyzer", TOOL_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


FIELDS = [
    "signal_id", "arm", "direction", "availability_research_clock", "research_year",
    "research_hour", "veto_mask", "veto_reasons", "router_pass", "aird_valid",
    "vrc_valid", "mbb_dc_valid", "qqe_primary", "qqe_secondary", "qqe_composite",
    "tb_closed_valid", "final_stop_pips", "cost_to_stop_ratio",
]


def row(signal, arm, direction, mask, reasons, passed, stop="14", ratio="0.10"):
    return {
        "signal_id": signal,
        "arm": arm,
        "direction": direction,
        "availability_research_clock": "2016.01.04 10:50",
        "research_year": "2016",
        "research_hour": "10",
        "veto_mask": str(mask),
        "veto_reasons": reasons,
        "router_pass": str(passed),
        "aird_valid": "1",
        "vrc_valid": "1",
        "mbb_dc_valid": "1",
        "qqe_primary": "0",
        "qqe_secondary": "0",
        "qqe_composite": "0",
        "tb_closed_valid": "1",
        "final_stop_pips": stop,
        "cost_to_stop_ratio": ratio,
    }


class RouterTelemetryTests(unittest.TestCase):
    def write_csv(self, rows, extra_fields=()):
        temp = tempfile.TemporaryDirectory()
        path = Path(temp.name) / "router.csv"
        fields = FIELDS + list(extra_fields)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        return temp, path

    def test_streaming_matched_pairs_and_group_counterfactual(self):
        rows = [
            row("S1", "TRUE_REVERSAL", "LONG", 0, "PASS", 1),
            row("S1", "FOLLOW_CONTROL", "SHORT", 0, "PASS", 1),
            row("S2", "TRUE_REVERSAL", "SHORT", 4, "AIRD_CONTINUATION", 0),
            row("S2", "FOLLOW_CONTROL", "LONG", 4, "AIRD_CONTINUATION", 0),
            row("S3", "TRUE_REVERSAL", "LONG", 20, "AIRD_CONTINUATION|VRC_HIGH_VOL", 0),
            row("S3", "FOLLOW_CONTROL", "SHORT", 20, "AIRD_CONTINUATION|VRC_HIGH_VOL", 0),
        ]
        temp, path = self.write_csv(rows)
        self.addCleanup(temp.cleanup)
        result = MODULE.analyze(path, analysis_from=date(2016, 1, 4), analysis_to=date(2020, 12, 31))
        self.assertEqual(result["population"]["raw_events"], 3)
        self.assertEqual(result["population"]["router_pass_events"], 1)
        removal = {x["key"]: x["count"] for x in result["router"]["counterfactual_pass_if_group_removed_alone"]}
        self.assertEqual(removal["AIRD"], 1)
        self.assertNotIn("VRC", removal)
        subsets = {
            x["removed_groups"]: x["total_pass_events"]
            for x in result["router"]["counterfactual_total_pass_if_groups_removed"]
        }
        self.assertEqual(subsets["AIRD"], 2)
        self.assertEqual(subsets["AIRD+VRC"], 3)
        self.assertEqual(result["integrity"]["matched_pair_error_count"], 0)

    def test_forbidden_outcome_column_fails_gate(self):
        rows = [
            {**row("S1", "TRUE_REVERSAL", "LONG", 0, "PASS", 1), "profit": "1"},
            {**row("S1", "FOLLOW_CONTROL", "SHORT", 0, "PASS", 1), "profit": "1"},
        ]
        temp, path = self.write_csv(rows, extra_fields=("profit",))
        self.addCleanup(temp.cleanup)
        result = MODULE.analyze(path, analysis_from=date(2016, 1, 4), analysis_to=date(2020, 12, 31))
        self.assertEqual(result["integrity"]["forbidden_outcome_columns"], ["profit"])
        self.assertFalse(result["frozen_gates"]["results"]["no_outcome_columns"])

    def test_non_adjacent_or_missing_arm_is_reported(self):
        rows = [row("S1", "TRUE_REVERSAL", "LONG", 0, "PASS", 1)]
        temp, path = self.write_csv(rows)
        self.addCleanup(temp.cleanup)
        result = MODULE.analyze(path, analysis_from=date(2016, 1, 4), analysis_to=date(2020, 12, 31))
        self.assertEqual(result["integrity"]["matched_pair_error_count"], 1)
        self.assertFalse(result["frozen_gates"]["results"]["matched_arms"])


if __name__ == "__main__":
    unittest.main()
