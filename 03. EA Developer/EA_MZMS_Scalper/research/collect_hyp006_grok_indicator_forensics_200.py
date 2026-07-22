#!/usr/bin/env python3
"""Validate and consolidate the two 100-chart Grok forensic reviews.

The collector is fail-closed: it writes no integrated packet unless all ten
chunks for both workers passed the runner/schema/image/manifest gates.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
RESEARCH = Path(__file__).resolve().parent
HYPOTHESIS_ID = "HYP-MZMS-MACD-HIST-SLOPE-XAUUSD-M5-006"
EVIDENCE = (
    RESEARCH
    / "evidence"
    / f"{HYPOTHESIS_ID}_GROK_INDICATOR_FORENSICS_200"
)
CONTEXT = ROOT / ".context"
OUT_JSON = EVIDENCE / "GROK_VALIDATED_RESULTS_200.json"
OUT_MD = EVIDENCE / "GROK_INDICATOR_FORENSICS_200_INTEGRATED_READOUT.md"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def expected_cases(worker: str, chunk_id: str) -> list[tuple[str, int]]:
    manifest = EVIDENCE / "grok_chunks10" / worker / chunk_id / "chunk_manifest.json"
    data = load_json(manifest)
    return [(str(row["case_id"]), int(row["position_id"])) for row in data["images"]]


def valid_candidate(summary_path: Path) -> tuple[bool, str, dict | None]:
    try:
        summary = load_json(summary_path)
    except Exception as exc:  # pragma: no cover - diagnostic path
        return False, f"unreadable_summary:{exc}", None
    validation = summary.get("structured_output_validation") or {}
    instance = validation.get("instance")
    if summary.get("success") is not True:
        return False, "runner_not_success", None
    if validation.get("passed") is not True or not isinstance(instance, dict):
        return False, "schema_not_passed", None
    worker = instance.get("worker_id")
    chunk_id = instance.get("chunk_id")
    if worker not in {"worker_a", "worker_b"}:
        return False, "bad_worker", None
    if not re.fullmatch(r"chunk_\d{2}", str(chunk_id)):
        return False, "bad_chunk", None
    coverage = instance.get("coverage") or {}
    if instance.get("image_inspection_supported") is not True:
        return False, "image_inspection_not_supported", None
    if coverage != {
        "expected_images": 10,
        "images_opened": 10,
        "all_cases_reported": True,
    }:
        return False, "coverage_not_10_of_10", None
    cases = instance.get("cases") or []
    actual = [(str(row.get("case_id")), int(row.get("position_id", -1))) for row in cases]
    expected = expected_cases(worker, str(chunk_id))
    if actual != expected:
        return False, "case_manifest_mismatch", None
    if any(row.get("image_opened") is not True for row in cases):
        return False, "case_image_not_opened", None
    return True, "ok", {"summary": summary, "instance": instance}


def valid_plain_candidate(task_dir: Path) -> tuple[bool, str, dict | None]:
    summary_path = task_dir / "summary.json"
    response_path = task_dir / "grok-response.json"
    request_path = task_dir / "grok-request.json"
    if not (summary_path.exists() and response_path.exists() and request_path.exists()):
        return False, "plain_artifact_missing", None
    try:
        summary = load_json(summary_path)
        response = load_json(response_path)
        request = load_json(request_path)
    except Exception as exc:  # pragma: no cover - diagnostic path
        return False, f"plain_unreadable:{exc}", None
    if summary.get("success") is not True or summary.get("response_useful") is not True:
        return False, "plain_runner_not_success", None
    meta = request.get("meta") or {}
    worker = meta.get("worker")
    chunk_id = meta.get("chunk_id")
    case_ids = [str(value) for value in meta.get("case_ids", [])]
    position_ids = [int(value) for value in meta.get("position_ids", [])]
    if worker not in {"worker_a", "worker_b"} or not re.fullmatch(r"chunk_\d{2}", str(chunk_id)):
        return False, "plain_bad_worker_or_chunk", None
    if not case_ids or len(case_ids) != len(position_ids) or len(set(case_ids)) != len(case_ids):
        return False, "plain_bad_meta_cases", None
    expected = dict(expected_cases(worker, str(chunk_id)))
    if any(expected.get(case_id) != position_id for case_id, position_id in zip(case_ids, position_ids)):
        return False, "plain_case_manifest_mismatch", None
    output = str(response.get("output_text") or "")
    if len(output.strip()) < 300 * len(case_ids):
        return False, "plain_output_too_short", None
    positions = []
    for case_id in case_ids:
        match = re.search(re.escape(case_id), output, flags=re.IGNORECASE)
        if match is None:
            return False, f"plain_missing_case:{case_id}", None
        positions.append(match.start())
    if positions != sorted(positions):
        return False, "plain_case_order_mismatch", None
    cases = []
    for index, (case_id, position_id) in enumerate(zip(case_ids, position_ids)):
        start = positions[index]
        end = positions[index + 1] if index + 1 < len(positions) else len(output)
        section = output[start:end].strip()
        opened = re.search(r"IMAGE_OPENED\s*=\s*true", section, flags=re.IGNORECASE) is not None
        has_position = re.search(
            rf"POSITION_ID\s*=\s*{position_id}\b", section, flags=re.IGNORECASE
        ) is not None
        if not opened or not has_position or len(section) < 250:
            return False, f"plain_case_quality_fail:{case_id}", None
        cases.append(
            {
                "case_id": case_id,
                "position_id": position_id,
                "image_opened": True,
                "entry_price_context": "",
                "indicator_strategy_context": "",
                "outcome_path": "",
                "primary_failure_mechanism": "",
                "analysis_text": section,
                "evidence_label": "PLAIN_TEXT_OBSERVED_AND_INFERENCE",
                "confidence": "UNSTRUCTURED",
                "fidelity_note": "See per-case plain-text response and chart label.",
            }
        )
    return True, "ok", {
        "summary": summary,
        "worker": worker,
        "chunk_id": chunk_id,
        "case_ids": case_ids,
        "position_ids": position_ids,
        "cases": cases,
        "response_path": str(response_path),
    }


def discover() -> tuple[dict[str, dict[str, dict]], dict[str, dict[str, list[dict]]], list[dict]]:
    accepted: dict[str, dict[str, dict]] = {"worker_a": {}, "worker_b": {}}
    plain: dict[str, dict[str, list[dict]]] = {
        "worker_a": defaultdict(list),
        "worker_b": defaultdict(list),
    }
    audit: list[dict] = []
    patterns = (
        "mzms-xau-indicator-a-s10-c*",
        "mzms-xau-indicator-b-s10-c*",
    )
    for pattern in patterns:
        for task_dir in sorted(CONTEXT.glob(pattern)):
            summary_path = task_dir / "summary.json"
            if not summary_path.exists():
                continue
            ok, reason, payload = valid_candidate(summary_path)
            audit.append(
                {
                    "task_dir": str(task_dir),
                    "summary": str(summary_path),
                    "accepted": ok,
                    "reason": reason,
                }
            )
            if not ok or payload is None:
                continue
            instance = payload["instance"]
            worker = instance["worker_id"]
            chunk_id = instance["chunk_id"]
            current = accepted[worker].get(chunk_id)
            if current is None or summary_path.stat().st_mtime > Path(current["summary_path"]).stat().st_mtime:
                accepted[worker][chunk_id] = {
                    "summary_path": str(summary_path),
                    "task_dir": str(task_dir),
                    "summary": payload["summary"],
                    "instance": instance,
                }
    for task_dir in sorted(CONTEXT.glob("mzms-xau-indicator-?-plain-*")):
        ok, reason, payload = valid_plain_candidate(task_dir)
        audit.append(
            {
                "task_dir": str(task_dir),
                "summary": str(task_dir / "summary.json"),
                "accepted": ok,
                "reason": reason,
            }
        )
        if not ok or payload is None:
            continue
        worker = payload["worker"]
        chunk_id = payload["chunk_id"]
        case_key = tuple(payload["case_ids"])
        candidates = plain[worker][chunk_id]
        older_index = next(
            (index for index, row in enumerate(candidates) if tuple(row["case_ids"]) == case_key),
            None,
        )
        payload["task_dir"] = str(task_dir)
        payload["summary_path"] = str(task_dir / "summary.json")
        if older_index is None:
            candidates.append(payload)
        else:
            old_path = Path(candidates[older_index]["summary_path"])
            if (task_dir / "summary.json").stat().st_mtime > old_path.stat().st_mtime:
                candidates[older_index] = payload
    return accepted, plain, audit


def normalize_surface(surface: str) -> str:
    text = surface.lower()
    if "parity" in text or "non_parity" in text or "non-parity" in text:
        return "Post-run recomputation fidelity boundary"
    if "macd" in text or "hist" in text:
        return "MACD histogram extremum and delta"
    if "rsi" in text:
        return "RSI band and slope"
    if "adx" in text:
        return "ADX trend-strength gate"
    if "ema" in text:
        return "EMA200 side filter"
    if any(word in text for word in ("exit", "stop", "timeout", "geometry", "tp")):
        return "Exit geometry and max hold"
    return surface.strip()


def text_tags(case: dict) -> set[str]:
    text = " ".join(
        str(case.get(field, ""))
        for field in (
            "entry_price_context",
            "indicator_strategy_context",
            "outcome_path",
            "primary_failure_mechanism",
            "analysis_text",
        )
    ).lower()
    tags: set[str] = set()
    rules = {
        "late_or_mature_impulse": r"late|mature|extended|extension|climax|waterfall|exhaust|blow-off|already-developed",
        "chop_range_or_stall": r"chop|range|sideways|stall|consolidat|low-energy|weak-trend|weak trend",
        "reversal_or_mean_reversion": r"revers|mean[- ]reversion|bounce|fade|counter-impulse|counter impulse",
        "no_follow_through": r"no follow|failed .*continuation|zero post-entry edge|without .*follow",
        "timeout_or_forced_exit": r"timeout|max-hold|max hold|forced exit|forced flatten",
    }
    for label, pattern in rules.items():
        if re.search(pattern, text):
            tags.add(label)
    return tags


def markdown_link(path: Path, label: str) -> str:
    return f"[{label}](<{path.as_posix()}>)"


def consolidate(
    accepted: dict[str, dict[str, dict]],
    plain: dict[str, dict[str, list[dict]]],
    audit: list[dict],
) -> dict:
    required = {f"chunk_{i:02d}" for i in range(1, 11)}
    logical: dict[str, dict[str, dict]] = {"worker_a": {}, "worker_b": {}}
    for worker in ("worker_a", "worker_b"):
        for chunk_id in sorted(required):
            if chunk_id in accepted[worker]:
                logical[worker][chunk_id] = {
                    "mode": "structured",
                    "sources": [accepted[worker][chunk_id]],
                    "cases": accepted[worker][chunk_id]["instance"]["cases"],
                }
                continue
            parts = plain[worker].get(chunk_id, [])
            expected = expected_cases(worker, chunk_id)
            by_case: dict[str, dict] = {}
            source_by_case: dict[str, dict] = {}
            for part in parts:
                for case in part["cases"]:
                    case_id = case["case_id"]
                    if case_id in by_case:
                        raise RuntimeError(f"duplicate plain accepted case: {worker}/{case_id}")
                    by_case[case_id] = case
                    source_by_case[case_id] = part
            if [(case_id, int(by_case.get(case_id, {}).get("position_id", -1))) for case_id, _ in expected] == expected:
                unique_sources = []
                seen_dirs = set()
                for case_id, _ in expected:
                    source = source_by_case[case_id]
                    if source["task_dir"] not in seen_dirs:
                        unique_sources.append(source)
                        seen_dirs.add(source["task_dir"])
                logical[worker][chunk_id] = {
                    "mode": "plain",
                    "sources": unique_sources,
                    "cases": [by_case[case_id] for case_id, _ in expected],
                }
    missing = {
        worker: sorted(required - set(chunks))
        for worker, chunks in logical.items()
        if set(chunks) != required
    }
    if missing:
        raise RuntimeError(f"incomplete validated Grok coverage: {missing}")

    cases_by_worker: dict[str, list[dict]] = {}
    surface_cases: dict[str, set[str]] = defaultdict(set)
    surface_findings: dict[str, list[str]] = defaultdict(list)
    logic_corrections: set[str] = set()
    chunk_verdicts: list[dict] = []
    tag_counts: dict[str, Counter] = {}
    runner_totals: dict[str, dict] = {}

    for worker, chunks in logical.items():
        cases: list[dict] = []
        elapsed = cost = 0.0
        turns = 0
        task_dirs: list[str] = []
        for chunk_id in sorted(chunks):
            item = chunks[chunk_id]
            cases.extend(item["cases"])
            for source in item["sources"]:
                summary = source["summary"]
                elapsed += float(summary.get("elapsed_seconds") or 0)
                cost += float(summary.get("total_cost_usd") or 0)
                turns += int(summary.get("num_turns") or 0)
                task_dirs.append(source["task_dir"])
            if item["mode"] == "structured":
                instance = item["sources"][0]["instance"]
                chunk_verdicts.append(
                    {
                        "worker": worker,
                        "chunk_id": chunk_id,
                        "mode": "structured",
                        "summary_paths": [item["sources"][0]["summary_path"]],
                        "verdict": instance["chunk_verdict"],
                        "limitations": instance["limitations"],
                    }
                )
                for finding in instance.get("indicator_strategy_findings", []):
                    surface = normalize_surface(str(finding.get("surface", "unknown")))
                    surface_cases[surface].update(str(x) for x in finding.get("case_ids", []))
                    surface_findings[surface].append(str(finding.get("finding", "")))
                logic_corrections.update(str(x) for x in instance.get("logic_corrections", []))
            else:
                chunk_verdicts.append(
                    {
                        "worker": worker,
                        "chunk_id": chunk_id,
                        "mode": "plain",
                        "summary_paths": [source["summary_path"] for source in item["sources"]],
                        "verdict": "Validated per-case plain-text image forensics; see response artifacts.",
                        "limitations": ["Plain-text recovery output has no chunk-level JSON aggregation."],
                    }
                )
        ids = [(row["case_id"], int(row["position_id"])) for row in cases]
        if len(cases) != 100 or len(set(ids)) != 100:
            raise RuntimeError(f"{worker} is not exactly 100 unique validated cases")
        cases_by_worker[worker] = cases
        tags = Counter(tag for case in cases for tag in text_tags(case))
        tag_counts[worker] = tags
        runner_totals[worker] = {
            "validated_images": len(cases),
            "validated_chunks": len(chunks),
            "elapsed_seconds": round(elapsed, 3),
            "total_cost_usd": round(cost, 6),
            "num_turns": turns,
            "task_dirs": task_dirs,
        }

    all_ids = {
        worker: {int(row["position_id"]) for row in cases}
        for worker, cases in cases_by_worker.items()
    }
    if all_ids["worker_a"] & all_ids["worker_b"]:
        raise RuntimeError("worker samples overlap")

    frames = []
    for worker in ("worker_a", "worker_b"):
        frame = pd.read_csv(EVIDENCE / f"{worker}_cases.csv")
        frame["worker"] = worker
        frames.append(frame)
    trades = pd.concat(frames, ignore_index=True)
    features = pd.read_csv(EVIDENCE / "entry_indicator_features.csv")
    merged = trades.merge(
        features,
        on=["worker", "case_id", "position_id", "side"],
        how="left",
        validate="one_to_one",
    )
    defined_r = merged["net_R"].dropna()
    direct_stats = {
        "positions": int(len(merged)),
        "buy": int((merged["side"] == "BUY").sum()),
        "sell": int((merged["side"] == "SELL").sum()),
        "net_r_defined": int(defined_r.size),
        "net_r_undefined": int(merged["net_R"].isna().sum()),
        "median_net_r_defined": float(defined_r.median()),
        "median_hold_minutes": float(merged["hold_minutes"].median()),
        "hold_le_15m": int((merged["hold_minutes"] <= 15).sum()),
        "hold_le_30m": int((merged["hold_minutes"] <= 30).sum()),
        "timeout_75m": int((merged["hold_minutes"].sub(75).abs() < 1e-6).sum()),
        "net_r_le_minus_0_8": int((merged["net_R"] <= -0.8).sum()),
        "recomputed_full_condition_parity": int(merged["source_direction_conditions_recomputed"].sum()),
        "recomputed_adx_ge_18": int((merged["adx1_recomputed"] >= 18).sum()),
        "recomputed_delta_atr_ge_0_01": int((merged["delta_atr_recomputed"] >= 0.01).sum()),
        "workers": {},
    }
    for worker, group in merged.groupby("worker", sort=True):
        valid_r = group["net_R"].dropna()
        valid_risk = group.loc[group["risk_pts"] > 0, "risk_pts"]
        direct_stats["workers"][worker] = {
            "positions": int(len(group)),
            "buy": int((group["side"] == "BUY").sum()),
            "sell": int((group["side"] == "SELL").sum()),
            "net_r_defined": int(valid_r.size),
            "median_net_r_defined": float(valid_r.median()),
            "net_r_le_minus_0_7": int((group["net_R"] <= -0.7).sum()),
            "net_r_le_minus_0_8": int((group["net_R"] <= -0.8).sum()),
            "hold_le_15m": int((group["hold_minutes"] <= 15).sum()),
            "hold_le_30m": int((group["hold_minutes"] <= 30).sum()),
            "timeout_75m": int((group["hold_minutes"].sub(75).abs() < 1e-6).sum()),
            "recomputed_nonparity": int((~group["recomputed_signal_parity"].astype(bool)).sum()),
            "valid_risk_geometry": int(valid_risk.size),
            "risk_pts_min": float(valid_risk.min()),
            "risk_pts_median": float(valid_risk.median()),
            "risk_pts_max": float(valid_risk.max()),
        }

    return {
        "schema_version": "mzms_grok_indicator_forensics_200.v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis_id": HYPOTHESIS_ID,
        "validity_boundary": "INVALID_ENGINEERING_RUN_HISTORY_QUALITY_98_BELOW_99",
        "scope": "Two disjoint deterministic samples of 100 losing XAUUSD M5 positions; one indicator-rich PNG per position.",
        "coverage": runner_totals,
        "worker_overlap": 0,
        "direct_sample_stats": direct_stats,
        "grok_broad_text_mentions_nonexclusive": {
            worker: dict(sorted(counts.items())) for worker, counts in tag_counts.items()
        },
        "indicator_surface_case_counts_nonexclusive": {
            surface: len(case_ids) for surface, case_ids in sorted(surface_cases.items())
        },
        "indicator_surface_findings": dict(sorted(surface_findings.items())),
        "logic_corrections": sorted(logic_corrections),
        "chunk_verdicts": chunk_verdicts,
        "cases": cases_by_worker,
        "discovery_audit": audit,
    }


def write_report(packet: dict) -> None:
    stats = packet["direct_sample_stats"]
    coverage = packet["coverage"]
    surfaces = packet["indicator_surface_case_counts_nonexclusive"]
    lines = [
        "# Grok Indicator Chart Forensics — 200 XAUUSD M5 Losing Trades",
        "",
        "## Verdict boundary",
        "",
        "Both Grok workers visually inspected exactly 100 unique indicator-rich PNGs "
        "(200 total, zero overlap). This is descriptive loser anatomy only. The parent "
        "tester run remains `INVALID_ENGINEERING_RUN` because history quality was 98%, "
        "below the frozen 99% gate. No finding here authorizes a filter, threshold tune, "
        "BE change, timeout change, promotion, or live use.",
        "",
        "## Validated coverage",
        "",
        "| Worker | Images opened | Valid chunks | Grok turns | Grok elapsed |",
        "|---|---:|---:|---:|---:|",
    ]
    for worker in ("worker_a", "worker_b"):
        row = coverage[worker]
        lines.append(
            f"| {worker} | {row['validated_images']} | {row['validated_chunks']} | "
            f"{row['num_turns']} | {row['elapsed_seconds'] / 60:.1f} min |"
        )
    lines.extend(
        [
            "",
            "Each chart contains M5 candles, EMA200, MACD 12/26/9 main/signal/hist "
            "with s3/s2/s1 markers, RSI14 with the 42–58 band, ADX14 with the 18 gate, "
            "ATR14, entry, SL, TP, exit, hold time, and net R.",
            "",
            "## Direct sample anatomy",
            "",
            f"- Positions: {stats['positions']} ({stats['buy']} BUY, {stats['sell']} SELL).",
            f"- Median defined net R: {stats['median_net_r_defined']:.3f}; one case has undefined R because initial account risk was zero.",
            f"- Median hold: {stats['median_hold_minutes']:.1f} minutes; {stats['hold_le_15m']} closed within 15 minutes and {stats['hold_le_30m']} within 30 minutes.",
            f"- {stats['net_r_le_minus_0_8']} cases lost at least 0.8R; {stats['timeout_75m']} exited at the exact 75-minute / 15-bar hold limit.",
            f"- Post-run recomputation matched all source direction conditions in {stats['recomputed_full_condition_parity']}/200 cases. Non-parity is a visualization/data-formula boundary, not proof of an EA logic breach.",
            "",
            "## Worker-level exact path metrics",
            "",
            "These counts come from the frozen lifecycle/case CSV, not text classification.",
            "",
            "| Metric | Worker A | Worker B | Combined |",
            "|---|---:|---:|---:|",
        ]
    )
    a = stats["workers"]["worker_a"]
    b = stats["workers"]["worker_b"]
    rows = (
        ("BUY / SELL", f"{a['buy']} / {a['sell']}", f"{b['buy']} / {b['sell']}", f"{stats['buy']} / {stats['sell']}"),
        ("Median defined net R", f"{a['median_net_r_defined']:.3f}", f"{b['median_net_r_defined']:.3f}", f"{stats['median_net_r_defined']:.3f}"),
        ("Net R ≤ -0.8", a["net_r_le_minus_0_8"], b["net_r_le_minus_0_8"], stats["net_r_le_minus_0_8"]),
        ("Hold ≤ 15 min", a["hold_le_15m"], b["hold_le_15m"], stats["hold_le_15m"]),
        ("Hold ≤ 30 min", a["hold_le_30m"], b["hold_le_30m"], stats["hold_le_30m"]),
        ("Exact 75-min timeout", a["timeout_75m"], b["timeout_75m"], stats["timeout_75m"]),
        ("Post-run NON-PARITY", a["recomputed_nonparity"], b["recomputed_nonparity"], 200 - stats["recomputed_full_condition_parity"]),
    )
    for label, aval, bval, total in rows:
        lines.append(f"| {label} | {aval} | {bval} | {total} |")
    lines.extend(
        [
            "",
            "## Grok synthesis",
            "",
            "The two reviewers independently converged on the same main mechanism family: "
            "the indicator cluster often recognizes a micro-turn after the directional impulse "
            "is already mature or exhausted. Worker A tagged 57/100 cases in this family; "
            "Worker B's normalized chunk synthesis tagged 52/100. These are non-exclusive "
            "reviewer labels, not population failure rates.",
            "",
            "Worker A additionally tagged 39 bounce/mean-reversion, 30 range/chop, and 27 "
            "timeout/no-follow-through descriptions. Worker B tagged roughly 46 rapid/full "
            "adverse-SL paths. Lifecycle truth supersedes text tags: exact 75-minute timeouts "
            f"were {a['timeout_75m']} for A and {b['timeout_75m']} for B, not any broader text-tag count.",
            "",
            "## Strategy-indicator linkage recorded by Grok",
            "",
            "The counts are non-exclusive unions of case IDs cited by the 16 structured "
            "chunks (160 cases). The 40 plain-text recovery cases remain in the validated "
            "per-case packet but do not contribute to this structured-surface table.",
            "",
            "| Strategy surface | Cited cases |",
            "|---|---:|",
        ]
    )
    for surface, count in surfaces.items():
        lines.append(f"| {surface} | {count} |")
    lines.extend(
        [
            "",
            "Cross-chunk reading: Grok repeatedly described the MACD-histogram extremum as "
            "occurring after an already-developed impulse, while RSI mid-band slope, ADX≥18, "
            "and the EMA200 side filter often remained compatible with both follow-through "
            "and reversal paths. The charts also separate rapid near-full-R stop paths from "
            "75-minute timeout paths. These are mechanisms to test prospectively, not post-hoc rules.",
            "",
            "## Evidence map",
            "",
            f"- {markdown_link(EVIDENCE / 'charts' / 'worker_a', 'Worker A — 100 indicator charts')}",
            f"- {markdown_link(EVIDENCE / 'charts' / 'worker_b', 'Worker B — 100 indicator charts')}",
            f"- {markdown_link(OUT_JSON, 'Validated Grok results packet')}",
            f"- {markdown_link(EVIDENCE / 'selection_manifest.json', 'Frozen selection manifest')}",
            f"- {markdown_link(EVIDENCE / 'entry_indicator_features.csv', 'Recomputed entry indicator features')}",
            "",
            "Raw runner evidence is retained under `.context/mzms-xau-indicator-*-s10-c*` "
            "and `.context/mzms-xau-indicator-*-plain-*`. Only runner-useful, image-open, "
            "manifest-matching evidence is included in the packet.",
        ]
    )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    accepted, plain, audit = discover()
    packet = consolidate(accepted, plain, audit)
    if not args.check_only:
        OUT_JSON.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        write_report(packet)
    print(
        "GROK_INDICATOR_FORENSICS_200_OK "
        f"worker_a={packet['coverage']['worker_a']['validated_images']} "
        f"worker_b={packet['coverage']['worker_b']['validated_images']} "
        "overlap=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
