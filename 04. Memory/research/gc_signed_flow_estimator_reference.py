"""Outcome-blind reference math for the GC count-sign innovation screen.

This module is deliberately source-independent. It does not read market data,
define a trading hypothesis, calculate returns, or authorize acquisition.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import NamedTuple


MIN_TRANSITIONS_PER_STATE = 10_000
MIN_VALID_PRIOR_BINS = 1_000
TAIL_SIGMA_MULTIPLE = 3.0
MIN_RESPONSE_TICKS = 1.0
SIGNS = (-1, 1)


class EstimatorUnavailable(ValueError):
    """Raised when a frozen feature or event gate is unavailable."""


class CompletedSession(NamedTuple):
    instrument_id: str
    session_ordinal: int
    signs: tuple[int, ...]
    valid_u_bins: tuple[float, ...]


class FrozenSessionParameters(NamedTuple):
    instrument_id: str
    session_ordinal: int
    expectation_after_negative: float
    expectation_after_positive: float
    sigma: float


def _sign(value: int) -> int:
    if isinstance(value, bool) or value not in SIGNS:
        raise ValueError(f"trade sign must be -1 or +1, got {value!r}")
    return value


def count_within_session_transitions(
    sessions: Sequence[Sequence[int]],
) -> dict[tuple[int, int], int]:
    """Count sign transitions without ever linking two session boundaries."""

    counts = {(previous, current): 0 for previous in SIGNS for current in SIGNS}
    for session in sessions:
        validated = [_sign(value) for value in session]
        for previous, current in zip(validated, validated[1:]):
            counts[(previous, current)] += 1
    return counts


def count_transitions_by_instrument(
    instrument_sessions: Mapping[str, Sequence[Sequence[int]]],
) -> dict[str, dict[tuple[int, int], int]]:
    """Keep raw instruments separate so a front-roll never creates a transition."""

    if not instrument_sessions:
        raise ValueError("at least one raw instrument is required")
    return {
        instrument: count_within_session_transitions(sessions)
        for instrument, sessions in instrument_sessions.items()
    }


def fit_markov_expectations(
    counts: Mapping[tuple[int, int], int],
) -> dict[int, float]:
    """Fit E[epsilon_i | epsilon_(i-1)] with the frozen per-state floor."""

    expected_keys = {(previous, current) for previous in SIGNS for current in SIGNS}
    if set(counts) != expected_keys:
        raise ValueError("transition counts must contain exactly four sign pairs")

    expectations: dict[int, float] = {}
    for previous in SIGNS:
        positive = counts[(previous, 1)]
        negative = counts[(previous, -1)]
        if isinstance(positive, bool) or isinstance(negative, bool):
            raise ValueError("transition counts must be nonnegative integers")
        if not isinstance(positive, int) or not isinstance(negative, int):
            raise ValueError("transition counts must be nonnegative integers")
        if positive < 0 or negative < 0:
            raise ValueError("transition counts must be nonnegative integers")
        denominator = positive + negative
        if denominator < MIN_TRANSITIONS_PER_STATE:
            raise EstimatorUnavailable(
                f"previous sign {previous:+d} has {denominator} transitions; "
                f"requires {MIN_TRANSITIONS_PER_STATE}"
            )
        expectations[previous] = (positive - negative) / denominator
    return expectations


def session_innovations(
    signs: Sequence[int], expectations: Mapping[int, float]
) -> list[float | None]:
    """Return one-session innovations; the first trade is always unavailable."""

    if set(expectations) != set(SIGNS):
        raise ValueError("expectations must contain exactly previous signs -1 and +1")
    validated = [_sign(value) for value in signs]
    result: list[float | None] = []
    previous: int | None = None
    for current in validated:
        if previous is None:
            result.append(None)
        else:
            expectation = float(expectations[previous])
            if not math.isfinite(expectation) or not -1.0 <= expectation <= 1.0:
                raise ValueError("expected sign must be finite and within [-1, +1]")
            result.append(current - expectation)
        previous = current
    return result


def aggregate_complete_bin(
    signs: Sequence[int], innovations: Sequence[float | None]
) -> tuple[float, float]:
    """Return (U, X); a bin containing an unavailable innovation fails closed."""

    if len(signs) != len(innovations) or not signs:
        raise ValueError("a bin requires equal nonempty sign and innovation arrays")
    validated = [_sign(value) for value in signs]
    if any(value is None for value in innovations):
        raise EstimatorUnavailable("bin contains an unavailable innovation")
    numeric = [float(value) for value in innovations if value is not None]
    if not all(math.isfinite(value) for value in numeric):
        raise ValueError("innovations must be finite")
    scale = math.sqrt(len(validated))
    return sum(numeric) / scale, sum(validated) / scale


def prior_population_sigma(values: Sequence[float]) -> float:
    """Population sigma over the frozen expanding history of valid prior bins."""

    if len(values) < MIN_VALID_PRIOR_BINS:
        raise EstimatorUnavailable(
            f"requires {MIN_VALID_PRIOR_BINS} valid prior bins, got {len(values)}"
        )
    numeric = [float(value) for value in values]
    if not all(math.isfinite(value) for value in numeric):
        raise ValueError("historical U values must be finite")
    mean = sum(numeric) / len(numeric)
    variance = sum((value - mean) ** 2 for value in numeric) / len(numeric)
    sigma = math.sqrt(variance)
    if not math.isfinite(sigma) or sigma <= 0.0:
        raise EstimatorUnavailable("historical U sigma must be finite and positive")
    return sigma


def freeze_session_parameters(
    *,
    instrument_id: str,
    session_ordinal: int,
    completed_sessions: Sequence[CompletedSession],
) -> FrozenSessionParameters:
    """Freeze one session from same-instrument, strictly prior completed records."""

    if not instrument_id:
        raise ValueError("instrument_id must be nonempty")
    if isinstance(session_ordinal, bool) or not isinstance(session_ordinal, int):
        raise ValueError("session_ordinal must be an integer")
    if not completed_sessions:
        raise EstimatorUnavailable("completed prior sessions are required")

    prior_ordinals: list[int] = []
    signs_by_session: list[tuple[int, ...]] = []
    prior_u_bins: list[float] = []
    for session in completed_sessions:
        if session.instrument_id != instrument_id:
            raise ValueError("cross-instrument session contamination")
        if isinstance(session.session_ordinal, bool) or not isinstance(
            session.session_ordinal, int
        ):
            raise ValueError("completed session ordinal must be an integer")
        if session.session_ordinal >= session_ordinal:
            raise ValueError("session parameters may use only strictly prior sessions")
        prior_ordinals.append(session.session_ordinal)
        signs_by_session.append(session.signs)
        prior_u_bins.extend(session.valid_u_bins)

    if prior_ordinals != sorted(prior_ordinals) or len(set(prior_ordinals)) != len(
        prior_ordinals
    ):
        raise ValueError("completed sessions must be unique and strictly ordered")

    expectations = fit_markov_expectations(
        count_within_session_transitions(signs_by_session)
    )
    sigma = prior_population_sigma(prior_u_bins)
    return FrozenSessionParameters(
        instrument_id=instrument_id,
        session_ordinal=session_ordinal,
        expectation_after_negative=expectations[-1],
        expectation_after_positive=expectations[1],
        sigma=sigma,
    )


def paired_candidate(
    *, innovation_flow: float, raw_flow: float, response_ticks: float, sigma: float
) -> dict[str, int] | None:
    """Apply direction-neutral gates and return paired challenger/null directions."""

    values = (innovation_flow, raw_flow, response_ticks, sigma)
    if not all(math.isfinite(float(value)) for value in values):
        raise ValueError("candidate inputs must be finite")
    if sigma <= 0.0:
        raise EstimatorUnavailable("sigma must be positive")
    if abs(innovation_flow) < TAIL_SIGMA_MULTIPLE * sigma:
        return None
    if abs(response_ticks) < MIN_RESPONSE_TICKS:
        return None
    if raw_flow == 0.0:
        return None
    return {
        "challenger_direction": 1 if innovation_flow > 0.0 else -1,
        "null_direction": 1 if raw_flow > 0.0 else -1,
    }
