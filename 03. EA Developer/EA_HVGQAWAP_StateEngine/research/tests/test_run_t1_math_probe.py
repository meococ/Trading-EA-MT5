from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "run_t1_math_probe.py"


def load_probe():
    spec = importlib.util.spec_from_file_location("run_t1_math_probe", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


probe = load_probe()


def test_constants_match_frozen_population_contract() -> None:
    assert probe.BASE_SEED == 20260731
    assert probe.OBS_N == 256
    assert probe.HVG_N == 64
    assert probe.LW_M == 32
    assert probe.DFA_SCALES == (8, 16, 32, 64)
    assert probe.LO_LAGS == (1, 3, 6, 12)
    assert probe.CANONICAL_NULL_CALIBRATION == 10_000
    assert probe.CANONICAL_NULL_VERIFICATION == 10_000
    assert probe.CANONICAL_ALT_VERIFICATION == 10_000


def test_estimators_reject_nonfinite_zero_variance_and_wrong_length() -> None:
    with pytest.raises(probe.InvalidReplicate):
        probe.memory_metrics(np.ones(256))
    bad = np.arange(256, dtype=float)
    bad[3] = np.nan
    with pytest.raises(probe.InvalidReplicate):
        probe.memory_metrics(bad)
    with pytest.raises(probe.InvalidReplicate):
        probe.memory_metrics(np.arange(255, dtype=float))


def test_lo_modified_rs_matches_manual_formula_for_lag_one() -> None:
    x = np.linspace(-1.0, 1.0, 256)
    x = x - x.mean()
    stats = probe.lo_modified_rs(x)
    gamma0 = float(np.dot(x, x) / 256)
    gamma1 = float(np.dot(x[1:], x[:-1]) / 256)
    hac = gamma0 + 2.0 * (1.0 - 1.0 / 2.0) * gamma1
    expected = float((np.max(np.cumsum(x)) - np.min(np.cumsum(x))) / np.sqrt(hac * 256))
    assert stats["lo_q1"] == pytest.approx(expected, rel=0, abs=1e-12)


def test_dfa1_matches_manual_polyfit_on_linear_profile() -> None:
    rng = np.random.default_rng(123)
    x = rng.standard_normal(256)
    got = probe.dfa1_h(x)
    profile = np.cumsum(x - x.mean())
    flucts = []
    for scale in (8, 16, 32, 64):
        residuals = []
        coords = np.arange(scale, dtype=float)
        design = np.column_stack([np.ones(scale), coords])
        for start in range(0, 256 - scale + 1, scale):
            segment = profile[start : start + scale]
            beta, *_ = np.linalg.lstsq(design, segment, rcond=None)
            residuals.append((segment - design @ beta) ** 2)
        for end in range(256, scale - 1, -scale):
            segment = profile[end - scale : end]
            beta, *_ = np.linalg.lstsq(design, segment, rcond=None)
            residuals.append((segment - design @ beta) ** 2)
        flucts.append(np.sqrt(np.mean(np.concatenate(residuals))))
    expected = float(np.polyfit(np.log([8, 16, 32, 64]), np.log(flucts), 1)[0])
    assert got == pytest.approx(expected, rel=0, abs=1e-12)


def test_seed_determinism_and_family_contracts() -> None:
    rng_a = probe.rng_for("AR_POS_06", "verification", 17)
    rng_b = probe.rng_for("AR_POS_06", "verification", 17)
    rng_c = probe.rng_for("AR_POS_06", "verification", 18)
    a = probe.generate_series("AR_POS_06", rng_a)
    b = probe.generate_series("AR_POS_06", rng_b)
    c = probe.generate_series("AR_POS_06", rng_c)
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)
    assert a.shape == (256,)
    assert abs(float(a.mean())) < 1e-12
    assert np.isfinite(a).all()
    assert probe.generate_series("BLOCK_PERMUTED_AR06", probe.rng_for("BLOCK_PERMUTED_AR06", "verification", 3)).shape == (256,)
    assert probe.generate_series("FGN_H060", probe.rng_for("FGN_H060", "alternative", 3)).shape == (256,)


def test_seed_sequence_uses_frozen_absolute_population_indices() -> None:
    assert probe.absolute_population_index("calibration", 17) == 17
    assert probe.absolute_population_index("verification", 17) == 10_017
    assert probe.absolute_population_index("alternative", 17) == 17
    direct = np.random.default_rng(np.random.SeedSequence(probe.BASE_SEED, spawn_key=(probe.family_index("AR_POS_06"), 10_017)))
    via_runner = probe.rng_for("AR_POS_06", "verification", 17)
    assert np.array_equal(direct.standard_normal(8), via_runner.standard_normal(8))

    smoke = probe.build_seed_ledger(probe.PopulationCounts(3, 4, 5))
    assert smoke["actual_ranges"]["null"]["IID_GAUSSIAN"]["calibration"]["absolute_start_inclusive"] == 0
    assert smoke["actual_ranges"]["null"]["IID_GAUSSIAN"]["calibration"]["absolute_stop_exclusive"] == 3
    assert smoke["actual_ranges"]["null"]["IID_GAUSSIAN"]["verification"]["absolute_start_inclusive"] == 10_000
    assert smoke["actual_ranges"]["null"]["IID_GAUSSIAN"]["verification"]["absolute_stop_exclusive"] == 10_004
    assert smoke["actual_ranges"]["alternative"]["FGN_H060"]["verification"]["absolute_start_inclusive"] == 0
    recorded_sha = smoke["seed_ledger_sha256"]
    recomputed = dict(smoke)
    del recomputed["seed_ledger_sha256"]
    assert recorded_sha == probe.sha256_bytes(probe.stable_json_dumps(recomputed).encode("utf-8"))


@pytest.mark.parametrize("h", [0.60, 0.65, 0.70])
def test_davies_harte_fgn_matches_theoretical_variance_and_lag_covariance(h: float) -> None:
    rng = np.random.default_rng(9000 + int(h * 100))
    samples = np.vstack([probe.davies_harte_fgn(rng, h, n=32, burn_in=0) for _ in range(3000)])
    gamma1 = 0.5 * (2.0 ** (2.0 * h) - 2.0)
    assert float(np.mean(samples[:, 0] ** 2)) == pytest.approx(1.0, abs=0.07)
    assert float(np.mean(samples[:, 1] * samples[:, 0])) == pytest.approx(gamma1, abs=0.07)


def test_hvg_ties_block_visibility_and_edges_are_forward_only() -> None:
    assert probe.hvg_edges([2.0, 2.0, 2.0]) == [(0, 1), (1, 2)]
    edges = probe.hvg_edges([3.0, 1.0, 3.0, 4.0])
    assert (0, 2) in edges
    assert (0, 3) not in edges
    assert all(i < j for i, j in edges)


def test_hvg_features_are_prefix_causal_under_future_append() -> None:
    rng = np.random.default_rng(456)
    prefix = rng.standard_normal(64)
    appended = np.concatenate([prefix, [999.0, -999.0]])
    prefix_edges = probe.hvg_edges(prefix)
    appended_prefix_edges = [(i, j) for i, j in probe.hvg_edges(appended) if i < 64 and j < 64]
    assert appended_prefix_edges == prefix_edges
    assert probe.hvg_features(prefix) == probe.hvg_features(appended[:64])


def test_reference_fixtures_are_full_replay_objects() -> None:
    fixtures = probe.reference_fixtures()
    assert len(fixtures["timestamps_utc"]) == 15
    assert set(fixtures["ohlc"]) == {"open", "high", "low", "close"}
    assert len(fixtures["tick_volume"]) == 15
    assert len(fixtures["typical_price"]) == 15
    assert fixtures["flags"]["utc_0000_reset_index"] == 2
    assert fixtures["flags"]["zero_tick_volume_indices"] == [3]
    assert fixtures["flags"]["missing_bar_indices"] == [4]
    assert fixtures["flags"]["bar_present"][4] is False
    assert fixtures["flags"]["post_gap_return_excluded_index"] == 5
    assert fixtures["flags"]["post_gap_positive_volume_qawap_update_index"] == 5
    assert len(fixtures["atr14"]["true_range"]) == 15
    assert len(fixtures["atr14"]["outputs"]) == 14 + 1
    assert len(fixtures["hvg"]["equal_vector"]) == 64
    assert len(fixtures["hvg"]["prefix_vector"]) == 64
    assert len(fixtures["hvg"]["future_vector"]) == 67
    assert fixtures["hvg"]["prefix_edges"] == fixtures["hvg"]["future_prefix_edges"]
    assert fixtures["hvg"]["prefix_features"] == fixtures["hvg"]["future_prefix_features"]
    for key in ("hvg_prefix_edges_sha256", "hvg_future_prefix_edges_sha256", "atr_sha256", "qawap_sha256"):
        assert len(fixtures["hashes"][key]) == 64
    assert len(fixtures["fixtures_sha256"]) == 64


def test_qawap_fixture_resets_rejects_and_resumes_accumulator() -> None:
    fixtures = probe.reference_fixtures()
    qawap = fixtures["qawap"]
    typical = fixtures["typical_price"]
    volume = fixtures["tick_volume"]

    assert qawap["actions"][0] == "ACCEPT_UPDATE"
    assert qawap["actions"][1] == "ACCEPT_UPDATE"
    assert qawap["actions"][2] == "ACCEPT_UPDATE"
    assert qawap["values"][2] == pytest.approx(typical[2], rel=0, abs=1e-12)
    assert qawap["values"][2] != pytest.approx(
        (typical[0] * volume[0] + typical[1] * volume[1] + typical[2] * volume[2])
        / (volume[0] + volume[1] + volume[2]),
        rel=0,
        abs=1e-9,
    )

    assert qawap["actions"][3] == "REJECT_ZERO_VOLUME_NO_STATE_UPDATE"
    assert qawap["values"][3] is None
    assert qawap["actions"][4] == "REJECT_MISSING_BAR_NO_STATE_UPDATE"
    assert qawap["values"][4] is None

    expected_resume = (typical[2] * volume[2] + typical[5] * volume[5]) / (volume[2] + volume[5])
    assert qawap["actions"][5] == "ACCEPT_UPDATE"
    assert qawap["values"][5] == pytest.approx(expected_resume, rel=0, abs=1e-12)
    assert qawap["values"][5] != pytest.approx(
        (typical[2] * volume[2] + typical[3] * volume[3] + typical[4] * volume[4] + typical[5] * volume[5])
        / (volume[2] + volume[3] + volume[4] + volume[5]),
        rel=0,
        abs=1e-9,
    )


def test_persistence_support_requires_three_lo_lags_and_estimator_agreement() -> None:
    criticals = {"d_hat": 0.1, "h_dfa": 0.6, "lo_q1": 1.0, "lo_q3": 1.0, "lo_q6": 1.0, "lo_q12": 1.0}
    row = {"d_hat": 0.2, "h_dfa": 0.68, "lo_q1": 1.1, "lo_q3": 1.1, "lo_q6": 1.1, "lo_q12": 0.9}
    assert probe.persistence_support(row, criticals)
    row_two_lags = dict(row, lo_q6=0.9)
    assert not probe.persistence_support(row_two_lags, criticals)
    row_disagree = dict(row, h_dfa=0.95)
    assert not probe.persistence_support(row_disagree, criticals)


def test_gate_logic_distinguishes_statistical_fail_from_invalid() -> None:
    calibration = {
        family: {
            "family": family,
            "stream": "calibration",
            "requested": 1,
            "valid": 1,
            "invalid": 0,
            "invalid_rate": 0.0,
            "memory": [{"d_hat": 0.0, "h_dfa": 0.5, "lo_q1": 1.0, "lo_q3": 1.0, "lo_q6": 1.0, "lo_q12": 1.0}],
            "hvg": [{"degree_kl": 0.0, "degree_entropy": 0.5, "motif4_imbalance": 0.0}],
        }
        for family in probe.NULL_FAMILIES
    }
    null_verification = {family: dict(payload, stream="verification") for family, payload in calibration.items()}
    alternatives = {
        family: {
            "family": family,
            "stream": "alternative",
            "requested": 100,
            "valid": 100,
            "invalid": 0,
            "invalid_rate": 0.0,
            "memory": [
                {"d_hat": 0.2, "h_dfa": 0.7, "lo_q1": 2.0, "lo_q3": 2.0, "lo_q6": 2.0, "lo_q12": 2.0}
                for _ in range(10)
            ]
            + [
                {"d_hat": 0.0, "h_dfa": 0.5, "lo_q1": 0.0, "lo_q3": 0.0, "lo_q6": 0.0, "lo_q12": 0.0}
                for _ in range(90)
            ],
            "hvg": [{"degree_kl": 0.0, "degree_entropy": 0.5, "motif4_imbalance": 0.0} for _ in range(100)],
        }
        for family in probe.ALT_D_BY_FAMILY
    }
    crit_mem = {"d_hat": 0.1, "h_dfa": 0.6, "lo_q1": 1.0, "lo_q3": 1.0, "lo_q6": 1.0, "lo_q12": 1.0}
    crit_hvg = {"degree_kl": 1.0, "motif4_imbalance": 1.0}
    result = probe.evaluate_gates(calibration, null_verification, alternatives, crit_mem, crit_hvg)
    assert result["verdict"] == probe.VERDICT_FAIL
    bad_cal = dict(calibration)
    bad_cal["IID_GAUSSIAN"] = dict(bad_cal["IID_GAUSSIAN"], invalid_rate=0.01)
    invalid = probe.evaluate_gates(bad_cal, null_verification, alternatives, crit_mem, crit_hvg)
    assert invalid["verdict"] == probe.VERDICT_INVALID


def test_invalid_reason_classification_counts_and_examples_are_emitted() -> None:
    codes = list(probe.INVALID_REASON_CODES)
    calls = {"index": 0}

    def invalid_generator(_family: str, _rng: np.random.Generator) -> np.ndarray:
        code = codes[calls["index"]]
        calls["index"] += 1
        raise probe.InvalidReplicate(code, f"synthetic {code}")

    payload = probe.collect_family("IID_GAUSSIAN", "calibration", len(codes), generator=invalid_generator)
    assert payload["requested"] == len(codes)
    assert payload["valid"] == 0
    assert payload["invalid"] == len(codes)
    assert payload["invalid_rate"] == 1.0
    assert payload["invalid_reason_counts"] == {code: 1 for code in codes}
    for index, code in enumerate(codes):
        examples = payload["invalid_reason_examples"][code]
        assert examples == [
            {
                "replicate_index": index,
                "absolute_population_index": index,
                "detail": f"synthetic {code}",
            }
        ]

    aggregate = probe.aggregate_invalid_observability([payload])
    key = "IID_GAUSSIAN:calibration"
    assert aggregate["total_reason_counts"] == {code: 1 for code in codes}
    assert aggregate["by_family_stream"][key]["requested_denominator"] == len(codes)
    assert aggregate["by_family_stream"][key]["reason_counts"] == {code: 1 for code in codes}


def test_untyped_numeric_errors_are_classified_as_other_numeric() -> None:
    def bad_generator(_family: str, _rng: np.random.Generator) -> np.ndarray:
        raise ValueError("synthetic numeric failure")

    payload = probe.collect_family("IID_GAUSSIAN", "verification", 1, generator=bad_generator)
    assert payload["invalid_reason_counts"]["OTHER_NUMERIC"] == 1
    example = payload["invalid_reason_examples"]["OTHER_NUMERIC"][0]
    assert example["replicate_index"] == 0
    assert example["absolute_population_index"] == 10_000
    assert "ValueError: synthetic numeric failure" in example["detail"]


def test_cli_smoke_emits_json_and_documented_exit_code(tmp_path: Path) -> None:
    output = tmp_path / "math_probe.json"
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--smoke", "--output", str(output)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == probe.EXIT_FAIL_CAPABILITY
    assert output.exists()
    payload = json.loads(output.read_text(encoding="utf-8"))
    printed = json.loads(completed.stdout)
    assert printed["sha256"] == probe.sha256_path(output)
    assert payload["schema_version"] == probe.SCHEMA_VERSION
    assert payload["hypothesis_id"] == probe.HYPOTHESIS_ID
    assert payload["mode"] == "smoke"
    assert payload["hash_bindings"]["plan_sha256"] == probe.EXPECTED_PLAN_SHA256
    assert payload["hash_bindings"]["runner_sha256"] == probe.sha256_path(SCRIPT)
    assert payload["hash_bindings"]["repair_task_packet"]["status"] == "BOUND"
    assert payload["hash_bindings"]["repair_task_packet"]["sha256"] == probe.EXPECTED_REPAIR_TASK_PACKET_SHA256
    assert payload["seed_contract"]["actual_ranges"]["null"]["IID_GAUSSIAN"]["verification"]["absolute_start_inclusive"] == 10_000
    assert len(payload["seed_contract"]["seed_ledger_sha256"]) == 64
    assert payload["invalid_replicate_observability"]["reason_codes"] == list(probe.INVALID_REASON_CODES)
    assert payload["invalid_replicate_observability"]["by_family_stream"]["IID_GAUSSIAN:verification"]["requested_denominator"] == probe.SMOKE_NULL_VERIFICATION
    assert "reference_fixtures" in payload
    assert payload["economic_trial_viewed"] is False
    assert payload["model0_authorized"] is False
    assert payload["verdict"] == probe.VERDICT_FAIL
