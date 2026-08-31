#!/usr/bin/env python3
"""Purged and embargoed combinatorial cross-validation for variant events.

Input is deliberately event-level. Each row must preserve the decision start
and the label/end time; daily return grids cannot prove overlap purging.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from datetime import datetime, timedelta, timezone
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = "alphafactory_purged_cpcv.v1"


class EventRecord:
    def __init__(
        self,
        variant_id: str,
        event_id: str,
        start_time: datetime,
        label_end: datetime,
        net_r: float,
    ) -> None:
        if not variant_id or not event_id:
            raise ValueError("variant_id and event_id are required")
        if start_time.tzinfo is None or label_end.tzinfo is None:
            raise ValueError("event timestamps must be timezone-aware")
        if label_end < start_time:
            raise ValueError(f"event {event_id} label_end precedes start_time")
        if not math.isfinite(float(net_r)):
            raise ValueError(f"event {event_id} net_r must be finite")
        self.variant_id = variant_id
        self.event_id = event_id
        self.start_time = start_time.astimezone(timezone.utc)
        self.label_end = label_end.astimezone(timezone.utc)
        self.net_r = float(net_r)


class CPCVSplit:
    def __init__(
        self,
        *,
        test_groups: Sequence[int],
        train_indices: Sequence[int],
        test_indices: Sequence[int],
        purged_indices: Sequence[int],
        embargoed_indices: Sequence[int],
    ) -> None:
        self.test_groups = tuple(test_groups)
        self.train_indices = tuple(train_indices)
        self.test_indices = tuple(test_indices)
        self.purged_indices = tuple(purged_indices)
        self.embargoed_indices = tuple(embargoed_indices)


def _parse_time(raw: str) -> datetime:
    value = raw.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid ISO timestamp: {raw}") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp lacks an explicit timezone: {raw}")
    return parsed.astimezone(timezone.utc)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_events_csv(path: Path | str) -> list[EventRecord]:
    events_path = Path(path)
    if not events_path.is_file():
        raise ValueError(f"event CSV not found: {events_path}")
    required = {"variant_id", "event_id", "start_time", "label_end", "net_r"}
    records: list[EventRecord] = []
    seen: set[tuple[str, str]] = set()
    with events_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"event CSV missing columns: {sorted(missing)}")
        for row_number, row in enumerate(reader, start=2):
            key = ((row.get("variant_id") or "").strip(), (row.get("event_id") or "").strip())
            if key in seen:
                raise ValueError(f"duplicate variant/event identity at row {row_number}: {key}")
            seen.add(key)
            try:
                net_r = float(row.get("net_r") or "")
            except ValueError as exc:
                raise ValueError(f"row {row_number} net_r is not numeric") from exc
            records.append(
                EventRecord(
                    key[0],
                    key[1],
                    _parse_time(row.get("start_time") or ""),
                    _parse_time(row.get("label_end") or ""),
                    net_r,
                )
            )
    if not records:
        raise ValueError("event CSV is empty")
    return records


def interval_overlaps_any(
    start_time: datetime,
    label_end: datetime,
    intervals: Iterable[tuple[datetime, datetime]],
) -> bool:
    return any(start_time <= other_end and label_end >= other_start for other_start, other_end in intervals)


def _time_groups(records: Sequence[EventRecord], n_groups: int) -> list[tuple[int, ...]]:
    unique_starts = sorted({record.start_time for record in records})
    if n_groups < 2:
        raise ValueError("n_groups must be at least 2")
    if n_groups > len(unique_starts):
        raise ValueError("n_groups exceeds the number of unique event start times")

    base, remainder = divmod(len(unique_starts), n_groups)
    chunks: list[list[datetime]] = []
    cursor = 0
    for group_index in range(n_groups):
        size = base + (1 if group_index < remainder else 0)
        chunks.append(unique_starts[cursor : cursor + size])
        cursor += size
    start_to_group = {
        timestamp: group_index
        for group_index, timestamps in enumerate(chunks)
        for timestamp in timestamps
    }
    return [
        tuple(index for index, record in enumerate(records) if start_to_group[record.start_time] == group)
        for group in range(n_groups)
    ]


def build_cpcv_splits(
    records: Sequence[EventRecord],
    *,
    n_groups: int,
    n_test_groups: int,
    embargo_pct: float,
    max_combinations: int = 5000,
) -> list[CPCVSplit]:
    if not records:
        raise ValueError("CPCV needs event records")
    if not 1 <= n_test_groups < n_groups:
        raise ValueError("n_test_groups must be between 1 and n_groups - 1")
    if not 0.0 <= embargo_pct < 1.0:
        raise ValueError("embargo_pct must be in [0, 1)")
    combination_count = math.comb(n_groups, n_test_groups)
    if combination_count > max_combinations:
        raise ValueError(
            f"full CPCV requires {combination_count} combinations, above max {max_combinations}"
        )

    groups = _time_groups(records, n_groups)
    global_start = min(record.start_time for record in records)
    global_end = max(record.label_end for record in records)
    embargo = timedelta(seconds=(global_end - global_start).total_seconds() * embargo_pct)
    all_indices = set(range(len(records)))
    splits: list[CPCVSplit] = []

    for test_group_tuple in combinations(range(n_groups), n_test_groups):
        test_indices = sorted({index for group in test_group_tuple for index in groups[group]})
        test_intervals = [(records[index].start_time, records[index].label_end) for index in test_indices]
        candidates = sorted(all_indices - set(test_indices))
        purged = [
            index
            for index in candidates
            if interval_overlaps_any(
                records[index].start_time,
                records[index].label_end,
                test_intervals,
            )
        ]
        after_purge = [index for index in candidates if index not in set(purged)]

        group_ends = [
            max(records[index].label_end for index in groups[group]) for group in test_group_tuple
        ]
        embargoed = [
            index
            for index in after_purge
            if any(group_end < records[index].start_time <= group_end + embargo for group_end in group_ends)
        ]
        train_indices = [index for index in after_purge if index not in set(embargoed)]
        splits.append(
            CPCVSplit(
                test_groups=test_group_tuple,
                train_indices=train_indices,
                test_indices=test_indices,
                purged_indices=purged,
                embargoed_indices=embargoed,
            )
        )
    return splits


def _metric(values: Sequence[float], metric: str) -> float:
    if not values:
        raise ValueError("metric needs observations")
    if metric == "mean":
        return statistics.mean(values)
    if metric == "sharpe":
        if len(values) < 2:
            raise ValueError("Sharpe needs at least two observations")
        std = statistics.stdev(values)
        if std <= 0.0:
            raise ValueError("Sharpe is undefined for a zero-variance fold")
        result = statistics.mean(values) / std
        if not math.isfinite(result):
            raise ValueError("Sharpe fold metric is not finite")
        return result
    if metric == "pf":
        gross_profit = sum(value for value in values if value > 0.0)
        gross_loss = -sum(value for value in values if value < 0.0)
        if gross_loss == 0.0:
            raise ValueError("profit factor is undefined for a zero-loss fold")
        result = gross_profit / gross_loss
        if not math.isfinite(result):
            raise ValueError("profit-factor fold metric is not finite")
        return result
    raise ValueError(f"unsupported metric: {metric}")


def _validate_aligned_event_universe(
    records: Sequence[EventRecord], variants: Sequence[str]
) -> None:
    grids: dict[str, dict[str, tuple[datetime, datetime]]] = {
        variant: {} for variant in variants
    }
    for record in records:
        grids[record.variant_id][record.event_id] = (record.start_time, record.label_end)
    reference_variant = variants[0]
    reference_grid = grids[reference_variant]
    for variant in variants[1:]:
        if grids[variant] != reference_grid:
            missing = sorted(set(reference_grid) - set(grids[variant]))
            extra = sorted(set(grids[variant]) - set(reference_grid))
            raise ValueError(
                "CPCV requires an aligned event universe across variants; "
                f"variant {variant} differs from {reference_variant} "
                f"(missing={missing[:5]}, extra={extra[:5]})"
            )


def _average_rank_percentile(
    metric_by_variant: Mapping[str, float], selected_variant: str
) -> float:
    ordered = sorted(metric_by_variant.items(), key=lambda item: item[1])
    selected_value = metric_by_variant[selected_variant]
    tied_ranks = [
        index
        for index, (_, value) in enumerate(ordered, start=1)
        if math.isclose(value, selected_value, rel_tol=1e-12, abs_tol=1e-12)
    ]
    average_rank = statistics.mean(tied_ranks)
    return (average_rank - 0.5) / len(ordered)


def run_purged_cpcv(
    records: Sequence[EventRecord],
    *,
    n_groups: int = 8,
    n_test_groups: int = 2,
    embargo_pct: float = 0.01,
    metric: str = "sharpe",
    min_observations: int = 2,
    max_combinations: int = 5000,
    frozen_pre_outcome: bool = False,
) -> dict[str, Any]:
    variants = sorted({record.variant_id for record in records})
    if len(variants) < 2:
        raise ValueError("CPCV selection analysis requires at least two variants")
    _validate_aligned_event_universe(records, variants)
    splits = build_cpcv_splits(
        records,
        n_groups=n_groups,
        n_test_groups=n_test_groups,
        embargo_pct=embargo_pct,
        max_combinations=max_combinations,
    )
    rows: list[dict[str, Any]] = []
    insufficient_observation_combinations = 0
    invalid_metric_combinations = 0
    non_informative_tie_combinations = 0
    for split_number, split in enumerate(splits, start=1):
        train_metrics: dict[str, float] = {}
        test_metrics: dict[str, float] = {}
        metric_invalid = False
        for variant in variants:
            train_values = [
                records[index].net_r
                for index in split.train_indices
                if records[index].variant_id == variant
            ]
            test_values = [
                records[index].net_r
                for index in split.test_indices
                if records[index].variant_id == variant
            ]
            if len(train_values) < min_observations or len(test_values) < min_observations:
                continue
            try:
                train_metrics[variant] = _metric(train_values, metric)
                test_metrics[variant] = _metric(test_values, metric)
            except ValueError:
                metric_invalid = True
                break
        if metric_invalid:
            invalid_metric_combinations += 1
            continue
        if len(train_metrics) != len(variants) or len(test_metrics) != len(variants):
            insufficient_observation_combinations += 1
            continue
        best_train_metric = max(train_metrics.values())
        best_variants = [
            variant
            for variant, value in train_metrics.items()
            if math.isclose(value, best_train_metric, rel_tol=1e-12, abs_tol=1e-12)
        ]
        if len(best_variants) != 1:
            non_informative_tie_combinations += 1
            continue
        selected_variant = best_variants[0]
        percentile = _average_rank_percentile(test_metrics, selected_variant)
        logit = math.log(percentile / (1.0 - percentile))
        rows.append(
            {
                "split": split_number,
                "test_groups": list(split.test_groups),
                "selected_variant": selected_variant,
                "selected_train_metric": train_metrics[selected_variant],
                "selected_test_metric": test_metrics[selected_variant],
                "selected_oos_rank_percentile": percentile,
                "selected_oos_logit": logit,
                "train_event_count": len(split.train_indices),
                "test_event_count": len(split.test_indices),
                "purged_event_count": len(split.purged_indices),
                "embargoed_event_count": len(split.embargoed_indices),
            }
        )

    pbo = (
        sum(1 for row in rows if row["selected_oos_logit"] <= 0.0) / len(rows)
        if rows
        else None
    )
    unusable = (
        insufficient_observation_combinations
        + invalid_metric_combinations
        + non_informative_tie_combinations
    )
    complete = unusable == 0 and len(rows) == len(splits)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis_kind": "event_level_purged_embargoed_combinatorial_cv",
        "settings": {
            "n_groups": n_groups,
            "n_test_groups": n_test_groups,
            "embargo_pct": embargo_pct,
            "metric": metric,
            "min_observations": min_observations,
            "full_combination_count": len(splits),
            "sampled": False,
        },
        "input": {
            "event_count": len(records),
            "variant_count": len(variants),
            "variants": variants,
            "required_interval_fields": ["start_time", "label_end"],
        },
        "results": {
            "usable_combinations": len(rows),
            "unusable_combinations": unusable,
            "insufficient_observation_combinations": insufficient_observation_combinations,
            "invalid_metric_combinations": invalid_metric_combinations,
            "non_informative_tie_combinations": non_informative_tie_combinations,
            "pbo": pbo,
            "selected_oos_metric_distribution": [row["selected_test_metric"] for row in rows],
            "splits": rows,
        },
        "frozen_pre_outcome": frozen_pre_outcome,
        "analysis_complete": bool(complete and rows),
        "anti_overfit_gate_eligible": False,
        "promotion_eligible": False,
        "limitation": (
            "CPCV is one diagnostic validation artifact. The CLI frozen flag is not a "
            "hash-bound preregistration receipt, so schema v1 cannot independently pass "
            "a gate. It also does not replace cumulative trial-count DSR, White Reality "
            "Check, WFA, cost provenance, or holdout gates."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Event-level purged and embargoed CPCV")
    parser.add_argument("--events-csv", required=True)
    parser.add_argument("--out", default="")
    parser.add_argument("--groups", type=int, default=8)
    parser.add_argument("--test-groups", type=int, default=2)
    parser.add_argument("--embargo-pct", type=float, default=0.01)
    parser.add_argument("--metric", choices=["mean", "sharpe", "pf"], default="sharpe")
    parser.add_argument("--min-observations", type=int, default=2)
    parser.add_argument("--max-combinations", type=int, default=5000)
    parser.add_argument("--frozen-pre-outcome", action="store_true")
    args = parser.parse_args()

    try:
        path = Path(args.events_csv)
        records = load_events_csv(path)
        result = run_purged_cpcv(
            records,
            n_groups=args.groups,
            n_test_groups=args.test_groups,
            embargo_pct=args.embargo_pct,
            metric=args.metric,
            min_observations=args.min_observations,
            max_combinations=args.max_combinations,
            frozen_pre_outcome=args.frozen_pre_outcome,
        )
        result["input"].update({"path": str(path.resolve()), "sha256": _sha256(path)})
        out_dir = Path(args.out) if args.out else path.resolve().parent / "cpcv_analysis"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "purged_cpcv.json"
        out_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False),
            encoding="utf-8",
        )
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2

    print(f"[PURGED CPCV] {out_path}")
    print(
        f"combinations={result['results']['usable_combinations']} "
        f"pbo={result['results']['pbo']} gate_eligible={result['anti_overfit_gate_eligible']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
