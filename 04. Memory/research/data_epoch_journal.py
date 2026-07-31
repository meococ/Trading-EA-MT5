#!/usr/bin/env python3
"""Shared fail-closed parsers for MT5 data-epoch tester journals."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any


SERIES_PROOF_FIELDS = (
    "m5_synchronized",
    "m5_first_epoch",
    "m5_terminal_first_epoch",
    "m1_server_first_epoch",
    "m1_terminal_first_epoch",
    "m5_bars",
    "terminal_maxbars",
    "copytime_from_epoch",
    "copytime_count",
    "copytime_result",
    "copytime_first_epoch",
    "copytime_last_error",
)

_REAL_TICK_MODE = "generating based on real ticks"
_GENERATED_MODES = {
    "every tick generating",
    "every tick generated from M1 bars",
}


def _tester_payloads(journal_text: str) -> list[str]:
    """Return only structured messages emitted by the MT5 Tester component."""
    payloads: list[str] = []
    for raw_line in journal_text.splitlines():
        if not raw_line.strip():
            continue
        fields = raw_line.split("\t")
        if len(fields) >= 5 and fields[3].strip() == "Tester":
            payloads.append("\t".join(fields[4:]).strip())
    return payloads


def _mode_from_payload(
    payload: str,
    symbol: str,
    period: str,
    server: str,
) -> str | None:
    prefix = f"{symbol},{period} ({server}): "
    for mode in (_REAL_TICK_MODE, *_GENERATED_MODES):
        if payload.strip() == f"{prefix}{mode}":
            return mode
    return None


def model4_mode_errors(
    journal_text: str,
    *,
    symbol: str,
    server: str,
    period: str = "M5",
    label: str = "journal",
) -> list[str]:
    """Require the exact bound structured Tester mode and reject contradictions."""
    modes = [
        mode
        for payload in _tester_payloads(journal_text)
        if (mode := _mode_from_payload(payload, symbol, period, server)) is not None
    ]
    errors: list[str] = []
    if _REAL_TICK_MODE not in modes:
        errors.append(
            f"{label}: Model 4 journal lacks exact Tester execution mode "
            f"'{symbol},{period} ({server}): {_REAL_TICK_MODE}'"
        )
    contradictions = sorted({mode for mode in modes if mode in _GENERATED_MODES})
    if contradictions:
        errors.append(
            f"{label}: Model 4 journal contains contradictory generated-tick "
            f"execution mode(s): {','.join(contradictions)}"
        )
    return errors


def journal_range(journal_text: str, symbol: str) -> dict[str, Any] | None:
    pattern = (
        r"(?im)(?<![A-Za-z0-9._+-])"
        + re.escape(symbol)
        + r":\s+history synchronized from "
        r"(?P<from>\d{4}\.\d{2}\.\d{2}) to (?P<to>\d{4}\.\d{2}\.\d{2})"
    )
    matches = list(re.finditer(pattern, journal_text))
    ranges = sorted({f"{match.group('from')}|{match.group('to')}" for match in matches})
    if len(ranges) != 1:
        return None
    actual_from, actual_to = ranges[0].split("|", 1)
    return {
        "actual_from": actual_from,
        "actual_to": actual_to,
        "exact_match_count": len(matches),
        "distinct_range_count": len(ranges),
    }


def journal_series_proof(
    journal_text: str,
    symbol: str,
    actual_from: str,
) -> dict[str, Any] | None:
    pattern = re.compile(
        rf"DATA_EPOCH_D0_SERIES_PROOF\s+symbol={re.escape(symbol)}"
        r"\s+m5_synchronized=(?P<m5_synchronized>[01])"
        r"\s+m5_first_epoch=(?P<m5_first_epoch>\d+)"
        r"\s+m5_terminal_first_epoch=(?P<m5_terminal_first_epoch>\d+)"
        r"\s+m1_server_first_epoch=(?P<m1_server_first_epoch>\d+)"
        r"\s+m1_terminal_first_epoch=(?P<m1_terminal_first_epoch>\d+)"
        r"\s+m5_bars=(?P<m5_bars>\d+)"
        r"\s+terminal_maxbars=(?P<terminal_maxbars>\d+)"
        r"\s+copytime_from_epoch=(?P<copytime_from_epoch>\d+)"
        r"\s+copytime_count=(?P<copytime_count>-?\d+)"
        r"\s+copytime_result=(?P<copytime_result>-?\d+)"
        r"\s+copytime_first_epoch=(?P<copytime_first_epoch>\d+)"
        r"\s+copytime_last_error=(?P<copytime_last_error>\d+)",
        flags=re.IGNORECASE | re.MULTILINE,
    )
    matches = list(pattern.finditer(journal_text))
    records = sorted({match.group(0) for match in matches})
    if len(records) != 1:
        return None
    proof = {key: int(matches[0].group(key)) for key in SERIES_PROOF_FIELDS}
    proof = {"symbol": symbol, **proof}
    if (
        proof["m5_synchronized"] != 1
        or proof["m5_bars"] <= 0
        or proof["terminal_maxbars"] <= 0
        or proof["copytime_from_epoch"] != proof["m5_first_epoch"]
        or proof["copytime_count"] != 1
        or proof["copytime_result"] != 1
        or proof["copytime_last_error"] != 0
        or any(
            proof[key] <= 0
            for key in (
                "m5_first_epoch",
                "m5_terminal_first_epoch",
                "m1_server_first_epoch",
                "m1_terminal_first_epoch",
                "copytime_first_epoch",
            )
        )
    ):
        return None
    try:
        actual_from_date = datetime.strptime(actual_from, "%Y.%m.%d").date()
        epoch_dates = {
            key: datetime.fromtimestamp(proof[key], tz=timezone.utc).date()
            for key in (
                "m5_first_epoch",
                "m5_terminal_first_epoch",
                "m1_server_first_epoch",
                "m1_terminal_first_epoch",
                "copytime_first_epoch",
            )
        }
    except (ValueError, OSError, OverflowError):
        return None
    if not (
        actual_from_date
        == epoch_dates["m5_first_epoch"]
        == epoch_dates["m5_terminal_first_epoch"]
        == epoch_dates["copytime_first_epoch"]
    ):
        return None
    if epoch_dates["m1_terminal_first_epoch"] != epoch_dates["m1_server_first_epoch"]:
        return None
    if epoch_dates["m1_server_first_epoch"] > epoch_dates["m5_first_epoch"]:
        return None
    floor = datetime(2018, 1, 1, tzinfo=timezone.utc).date()
    coverage_class = "FULL_2018_PLUS"
    if actual_from_date > floor:
        gap_days = (
            epoch_dates["m5_first_epoch"] - epoch_dates["m1_server_first_epoch"]
        ).days
        if epoch_dates["m1_server_first_epoch"] <= floor or gap_days > 7:
            return None
        coverage_class = "BROKER_LIMITED_START"
    return {"coverage_class": coverage_class, "series_proof": proof}
