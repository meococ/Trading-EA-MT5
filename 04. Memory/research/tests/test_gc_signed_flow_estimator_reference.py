from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import pytest


RESEARCH = Path(__file__).resolve().parents[1]
MODULE_PATH = RESEARCH / "gc_signed_flow_estimator_reference.py"
SPEC = importlib.util.spec_from_file_location("gc_signed_flow_reference", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
SUT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUT)


def test_session_reset_never_creates_boundary_transition() -> None:
    counts = SUT.count_within_session_transitions([[1, -1], [1, 1]])

    assert counts[(1, -1)] == 1
    assert counts[(1, 1)] == 1
    assert counts[(-1, 1)] == 0


def test_first_trade_is_unavailable_after_every_session_reset() -> None:
    expectations = {-1: -0.4, 1: 0.6}

    assert SUT.session_innovations([1, -1], expectations) == [None, -1.6]
    assert SUT.session_innovations([-1, 1], expectations) == [None, 1.4]
    with pytest.raises(SUT.EstimatorUnavailable, match="unavailable innovation"):
        SUT.aggregate_complete_bin([1, -1], [None, -1.6])


def test_asymmetric_markov_expectations_and_state_floor() -> None:
    counts = {
        (-1, -1): 7_000,
        (-1, 1): 3_000,
        (1, -1): 2_000,
        (1, 1): 8_000,
    }

    assert SUT.fit_markov_expectations(counts) == {-1: -0.4, 1: 0.6}

    counts[(1, 1)] -= 1
    with pytest.raises(SUT.EstimatorUnavailable, match="requires 10000"):
        SUT.fit_markov_expectations(counts)


def test_raw_contracts_never_splice_across_roll() -> None:
    counts = SUT.count_transitions_by_instrument(
        {"GCJ9": [[1]], "GCM9": [[-1]]}
    )

    assert sum(counts["GCJ9"].values()) == 0
    assert sum(counts["GCM9"].values()) == 0


def test_u_x_and_population_sigma_are_deterministic() -> None:
    u_value, x_value = SUT.aggregate_complete_bin(
        [1, 1, -1], [0.4, 0.4, -1.6]
    )

    assert math.isclose(u_value, -0.8 / math.sqrt(3))
    assert math.isclose(x_value, 1.0 / math.sqrt(3))
    history = [-1.0, 1.0] * 500
    assert SUT.prior_population_sigma(history) == 1.0
    with pytest.raises(SUT.EstimatorUnavailable, match="requires 1000"):
        SUT.prior_population_sigma(history[:-1])


def completed_prior_session(
    *, instrument_id: str = "GCJ9", session_ordinal: int = 1
) -> object:
    return SUT.CompletedSession(
        instrument_id=instrument_id,
        session_ordinal=session_ordinal,
        signs=tuple([1, -1] * 10_001),
        valid_u_bins=tuple([-1.0, 1.0] * 500),
    )


def test_session_parameters_freeze_from_same_instrument_prior_history() -> None:
    frozen = SUT.freeze_session_parameters(
        instrument_id="GCJ9",
        session_ordinal=2,
        completed_sessions=[completed_prior_session()],
    )

    assert frozen.instrument_id == "GCJ9"
    assert frozen.session_ordinal == 2
    assert frozen.expectation_after_negative == 1.0
    assert frozen.expectation_after_positive == -1.0
    assert frozen.sigma == 1.0


def test_session_parameters_reject_current_session_contamination() -> None:
    with pytest.raises(ValueError, match="strictly prior"):
        SUT.freeze_session_parameters(
            instrument_id="GCJ9",
            session_ordinal=2,
            completed_sessions=[
                completed_prior_session(),
                completed_prior_session(session_ordinal=2),
            ],
        )


def test_session_parameters_reject_cross_instrument_expectation_and_sigma() -> None:
    with pytest.raises(ValueError, match="cross-instrument"):
        SUT.freeze_session_parameters(
            instrument_id="GCJ9",
            session_ordinal=3,
            completed_sessions=[
                completed_prior_session(),
                completed_prior_session(instrument_id="GCM9", session_ordinal=2),
            ],
        )


def test_paired_null_uses_same_event_without_response_direction_bias() -> None:
    event = SUT.paired_candidate(
        innovation_flow=3.0,
        raw_flow=-2.0,
        response_ticks=-1.0,
        sigma=1.0,
    )

    assert event == {"challenger_direction": 1, "null_direction": -1}
    assert SUT.paired_candidate(
        innovation_flow=3.0,
        raw_flow=-2.0,
        response_ticks=1.0,
        sigma=1.0,
    ) == event


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"innovation_flow": 2.99, "raw_flow": 1.0, "response_ticks": 1.0, "sigma": 1.0}, None),
        ({"innovation_flow": 3.0, "raw_flow": 1.0, "response_ticks": 0.99, "sigma": 1.0}, None),
        ({"innovation_flow": 3.0, "raw_flow": 0.0, "response_ticks": 1.0, "sigma": 1.0}, None),
    ],
)
def test_candidate_boundaries_fail_closed(kwargs: dict[str, float], expected: None) -> None:
    assert SUT.paired_candidate(**kwargs) is expected
