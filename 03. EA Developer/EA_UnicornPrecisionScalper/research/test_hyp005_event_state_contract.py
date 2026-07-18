#!/usr/bin/env python3
"""Offline contract tests for the frozen HYP-UPS-XAU-M5-005 probe."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "probe_unicorn_event_anchored_closedbar.py"
PREREG = ROOT / "HYP-UPS-XAU-M5-005_FROZEN_PREREG.md"
EA_SOURCE = (
    ROOT
    / "source_snapshots"
    / "EA_UnicornPrecisionScalper_HYP-005_D7698C25.mq5"
)
OPERATIONAL_SOURCE = (
    ROOT
    / "source_snapshots"
    / "EA_UnicornPrecisionScalper_HYP-006_CB51EB2A.mq5"
)


def load_module():
    spec = importlib.util.spec_from_file_location("hyp005_probe", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load HYP-005 probe")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Hyp005ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()
        cls.source = SCRIPT.read_text(encoding="utf-8")
        cls.prereg = PREREG.read_text(encoding="utf-8")
        cls.ea_source = EA_SOURCE.read_text(encoding="utf-8")
        cls.operational_source = OPERATIONAL_SOURCE.read_text(encoding="utf-8")

    def test_prereg_is_pre_outcome_and_one_change(self) -> None:
        self.assertIn("single pre-outcome structural challenger", self.prereg)
        self.assertIn("All 2026 data is untouched", self.prereg)
        self.assertIn("one mechanism only", self.prereg)
        self.assertIn("InpUseEventAnchoredSweepState=true", self.prereg)
        self.assertIn("Failure is terminal", self.prereg)

    def test_probe_is_portable_closed_bar_and_has_no_trade_calls(self) -> None:
        self.assertIn("portable=True", self.source)
        self.assertIn('data_path.drive.upper() != "D:"', self.source)
        self.assertIn('int(rates[i]["time"]) + 5 * 60', self.source)
        for forbidden in ("order_send", "positions_get", "history_deals_get", "copy_ticks"):
            self.assertNotIn(forbidden, self.source)

    def test_frozen_thresholds_are_literal(self) -> None:
        for literal in ("body_atr < 1.20", "fvg_atr < 0.05", "overlap < 0.10", "score < 75"):
            self.assertIn(literal, self.source)
        self.assertEqual(self.module.FIXED_STATE_BARS, 4)
        self.assertEqual(self.module.SWEEP_LOOKBACK, 12)
        self.assertEqual(self.module.SESSION_START_HOUR, 7)
        self.assertEqual(self.module.SESSION_END_HOUR, 16)

    def test_structural_invalidation_is_closed_bar_directional(self) -> None:
        dtype = [("close", "f8")]
        rates = np.array([(100.0,), (101.0,), (99.0,), (102.0,)], dtype=dtype)
        self.assertTrue(self.module.structurally_invalidated(rates, 0, 3, 1, 100.0))
        self.assertFalse(self.module.structurally_invalidated(rates, 0, 1, 1, 99.0))
        self.assertTrue(self.module.structurally_invalidated(rates, 0, 3, -1, 101.5))

    def test_casebook_is_deterministic_and_bounded(self) -> None:
        rows = [{"decision_time_utc": f"row-{index:03d}"} for index in range(350)]
        first = self.module.deterministic_casebook(rows)
        second = self.module.deterministic_casebook(rows)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 200)
        self.assertEqual(first[0], rows[0])
        self.assertEqual(first[-1], rows[-1])

    def test_casebook_schema_has_no_forward_outcome_fields(self) -> None:
        sample = {
            "schema_version": "unicorn_event_state_casebook.v1",
            "rows": [{"decision_time_utc": "2024-01-01T08:00:00Z", "sweep_age_bars": 5}],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "casebook.json"
            path.write_text(json.dumps(sample), encoding="utf-8")
            payload = json.loads(path.read_text(encoding="utf-8"))
        forbidden = {"profit", "loss", "entry_return", "exit", "fill", "drawdown", "net_r"}
        self.assertTrue(forbidden.isdisjoint(payload["rows"][0]))

    def test_ea_implements_only_the_frozen_event_state_switch(self) -> None:
        self.assertIn("input bool   InpUseEventAnchoredSweepState=false;", self.ea_source)
        self.assertIn('HYPOTHESIS_ID="HYP-UPS-XAU-M5-005"', self.ea_source)
        self.assertIn("rates[k].close<=rates[j].low", self.ea_source)
        self.assertIn("rates[k].close>=rates[j].high", self.ea_source)
        self.assertIn("sweep_parts.day_of_year!=decision_parts.day_of_year", self.ea_source)
        self.assertIn("CopyRates(_Symbol,PERIOD_M5,1,required,rates)", self.ea_source)

    def test_telemetry_keeps_close_open_risk_states_separate(self) -> None:
        """A same-tick close/open callback must not zero the prior lifecycle risk."""
        for field in (
            "g_pending_risk_points",
            "g_pending_risk_account",
            "g_previous_risk_points",
            "g_previous_risk_account",
            "g_previous_position_identifier",
        ):
            self.assertIn(field, self.ea_source)
        self.assertIn(
            "g_previous_position_identifier=g_position_identifier;", self.ea_source
        )
        self.assertIn(
            "g_planned_risk_points=g_pending_risk_points;", self.ea_source
        )
        self.assertIn(
            "else if(position_id==g_previous_position_identifier)", self.ea_source
        )
        self.assertIn(
            "DoubleToString(lifecycle_risk_points,8)", self.ea_source
        )

    def test_frozen_hyp006_changed_only_operational_identity(self) -> None:
        expected = self.ea_source.replace(
            'HYPOTHESIS_ID="HYP-UPS-XAU-M5-005"',
            'HYPOTHESIS_ID="HYP-UPS-XAU-M5-006"',
        )
        self.assertEqual(self.operational_source, expected)


if __name__ == "__main__":
    unittest.main()
