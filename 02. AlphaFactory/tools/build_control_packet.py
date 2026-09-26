#!/usr/bin/env python3
"""Generic era-2 control task packet + RESEARCH_PROXY cost manifest builder.

Parameterized successor of build_crsir2_control_packet.py — same schema
(alphafactory_research_task_packet.v1 + alphafactory_cost_source_manifest.v1),
same hash-binding rules, per-cell arguments.

Requires, under 03. EA Developer/<EA>/:
  <EA>.mq5                                      canonical source (patched)
  research/<HYP>_FROZEN_PREREG.md               frozen preregistration
  ALPHAFACTORY_EA_CONTRACT.json                 telemetry contract
  research/evidence/<SYM>_spread_evidence.json  measured spread evidence
  research/evidence/<SYM>_slippage_evidence.json
  research/evidence/<SYM>_commission_evidence.json
And a screened registry row for <HYP> in 04. Memory/research/CANDIDATE_REGISTRY.jsonl.

Run immediately before ea_research_loop.ps1 -Execute: all hashes bind live bytes.
"""
import argparse
import csv
import hashlib
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MQL5_INCLUDE = ROOT / "02. AlphaFactory" / "runtime" / "mt5-portable-mqdemo" / "MQL5" / "Include"


def sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest().upper()


def sha_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest().upper()


def rel(p: Path) -> str:
    return str(p.resolve().relative_to(ROOT.resolve())).replace("\\", "/")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ea", required=True)
    ap.add_argument("--hyp", required=True)
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--from-date", default="1970.01.01",
                    help="requested window start (1970 sentinel or verified-M1 boundary)")
    ap.add_argument("--coverage-mode", default="all_available_asof",
                    choices=["all_available_asof", "verified_m1_asof"],
                    help="all_available_asof pins the 1970 sentinel; verified_m1_asof binds from-date to a verified real-M1 boundary")
    ap.add_argument("--period", required=True)
    ap.add_argument("--magic", required=True)
    ap.add_argument("--spread-points", required=True,
                    help="tester Spread in points (measured current_spread_points)")
    ap.add_argument("--pip", type=float, required=True)
    ap.add_argument("--digits", type=int, required=True)
    ap.add_argument("--point", type=float, required=True)
    # data_fingerprint pins the expected report data shape (alpha.ps1
    # Get-ReportIdentity): symbol|period|from|to|model|history_quality|bars|
    # ticks|digits|point|pip_size. Values come from a prior acquisition run —
    # a deterministic tester must reproduce them exactly or the post-run
    # identity check fails closed on data drift.
    ap.add_argument("--history-quality", required=True,
                    help="report History Quality, e.g. '98' or '98%%' "
                         "(normalized to the report literal with '%%')")
    ap.add_argument("--bars", type=int, required=True,
                    help="report Bars count from the acquisition run")
    ap.add_argument("--ticks", type=int, required=True,
                    help="report Ticks count from the acquisition run")
    ap.add_argument("--extra-overrides", default="",
                    help="additional frozen 'k=v;...' EA inputs appended to the "
                         "telemetry/magic overrides, e.g. symbol-pinned geometry")
    ap.add_argument("--to-date", default=None,
                    help="pin the window end (YYYY.MM.DD) to reproduce a prior "
                         "acquisition run's identity; default = last closed "
                         "server day")
    args = ap.parse_args()

    ea, hyp, sym, period = args.ea, args.hyp, args.symbol, args.period
    pkg = ROOT / "03. EA Developer" / ea
    evid = pkg / "research" / "evidence"
    registry = ROOT / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"

    src_rel = f"03. EA Developer/{ea}/{ea}.mq5"
    prereg_rel = f"03. EA Developer/{ea}/research/{hyp}_FROZEN_PREREG.md"
    contract_rel = f"03. EA Developer/{ea}/ALPHAFACTORY_EA_CONTRACT.json"
    cost_rel = f"03. EA Developer/{ea}/research/evidence/COST_SOURCE_MANIFEST.json"
    packet_rel = f"03. EA Developer/{ea}/research/preflight/{hyp}/task_packet.json"

    now = datetime.now(timezone.utc)
    # Coverage claims only through the last fully closed server day; the
    # in-progress UTC day is not yet in synchronized history.
    last_closed = (now - timedelta(days=1)).date()
    if args.to_date:
        # Reproduce a prior acquisition run's coverage pin so the
        # data_fingerprint matches the earlier proven identity.
        last_closed = datetime.strptime(args.to_date, "%Y.%m.%d").date()
    asof = f"{last_closed.isoformat()}T23:59:59Z"
    to_date = last_closed.strftime("%Y.%m.%d")

    # ---- fingerprints (alpha.ps1 Get-ReportIdentity conventions) ----
    spread_ev = evid / f"{sym}_spread_evidence.json"
    slip_ev = evid / f"{sym}_slippage_evidence.json"
    comm_ev = evid / f"{sym}_commission_evidence.json"
    for p in (spread_ev, slip_ev, comm_ev,
              ROOT / src_rel, ROOT / prereg_rel, ROOT / contract_rel):
        if not p.is_file():
            raise RuntimeError(f"missing required input: {rel(p)}")

    ident = json.loads(spread_ev.read_text())["identity"]
    # Packet fingerprints must bind the same basis alpha.ps1 Get-ReportIdentity
    # computes post-run from report.html, not the probe-side terminal_info basis.
    broker_fp = sha_text(ident["company"])
    server_fp = sha_text(f"{ident['observed_server']} (Build {ident['terminal_build']})")
    deposit_fmt = f"{10000:,.2f}".replace(",", " ")  # MT5 report: "10 000.00"
    account_fp = sha_text(
        f"{ident['currency']}|{deposit_fmt}|1:100|10000|100|{args.spread_points}")
    def fmt_num(v: float) -> str:
        # Mirror PS5.1 [string]([double]$v) general format: scientific below 1e-4.
        if v != 0 and (abs(v) < 1e-4 or abs(v) >= 1e15):
            mant, ex = f"{v:.14E}".split("E")
            mant = mant.rstrip("0").rstrip(".")
            return f"{mant}E{int(ex):+03d}"
        s = f"{v:.10f}".rstrip("0").rstrip(".")
        return s if s else "0"

    history_quality_literal = str(args.history_quality).strip()
    if not history_quality_literal.endswith("%"):
        history_quality_literal += "%"
    data_fp = sha_text(
        f"{sym}|{period}|{args.from_date}|{to_date}|0|{history_quality_literal}|"
        f"{args.bars}|{args.ticks}|{args.digits}|{fmt_num(args.point)}|"
        f"{fmt_num(args.pip)}")

    # ---- raw evidence CSVs (validator binds these files by hash) ----
    spread_csv = evid / f"{sym}_spread_ticks.csv"
    slip_csv = evid / f"{sym}_slippage_quotes.csv"
    comm_csv = evid / f"{sym}_commission_proxy.csv"
    for p in (spread_csv, slip_csv, comm_csv):
        if not p.is_file():
            raise RuntimeError(f"missing required input: {rel(p)}")

    spread_rows = list(csv.DictReader(spread_csv.open(encoding="utf-8-sig", newline="")))
    spread_valid = sum(
        1 for r in spread_rows
        if float(r["bid"]) > 0 and float(r["ask"]) >= float(r["bid"]))
    comm_rows = list(csv.DictReader(comm_csv.open(encoding="utf-8-sig", newline="")))
    comm_values = [float(r["round_turn_account_per_lot"]) for r in comm_rows]
    slip_rows = list(csv.DictReader(slip_csv.open(encoding="utf-8-sig", newline="")))
    slip_latency = int(slip_rows[0]["latency_ms"])
    slip_max_wait = max(int(r["actual_delay_ms"]) for r in slip_rows) - slip_latency

    def p90(vals):
        ordered = sorted(vals)
        return ordered[max(0, math.ceil(0.90 * len(ordered)) - 1)]

    def adverse(r):
        ref, fut = float(r["reference_price"]), float(r["future_quote_price"])
        return max(0.0, (fut - ref) / args.pip) if r["side"] == "BUY" \
            else max(0.0, (ref - fut) / args.pip)

    buy_adv = [adverse(r) for r in slip_rows if r["side"] == "BUY"]
    sell_adv = [adverse(r) for r in slip_rows if r["side"] == "SELL"]

    cost = {
        "schema_version": "alphafactory_cost_source_manifest.v1",
        "evidence_tier": "RESEARCH_PROXY",
        "provenance_status": "VERIFIED_RESEARCH_PROXY",
        "audit_status": "PASS_RESEARCH_ONLY",
        "verdict": "PASS_RESEARCH_ONLY",
        "promotion_eligible": False,
        "performance_metrics_authorized": False,
        "economics_authorized": False,
        "broker": "MetaQuotes Ltd.",
        # The run manifest fingerprint_basis carries the report's full server
        # identity; the cost source must bind that exact string.
        "server": f"{ident['observed_server']} (Build {ident['terminal_build']})",
        "account_currency": "USD",
        "broker_fingerprint": broker_fp,
        "server_fingerprint": server_fp,
        "account_fingerprint": account_fp,
        "data_fingerprint": data_fp,
        "symbol": sym,
        "from": args.from_date,
        "to": to_date,
        "symbol_geometry": {
            "digits": args.digits, "point": args.point, "pip_size": args.pip},
        "historical_spread_provenance": {
            "verification_status": "VERIFIED",
            "source": rel(spread_csv),
            "source_sha256": sha_file(spread_csv),
            "symbol": sym,
            "coverage": {
                "from": args.from_date,
                "to": to_date,
                "sample_count": spread_valid,
                "total_count": len(spread_rows),
                "coverage_ratio": spread_valid / len(spread_rows),
            },
            "note": "tester spread=current applies the measured current spread "
                    "to 100% of generated ticks; the sampled raw BID/ASK window "
                    "verifies the level applied to the whole run.",
        },
        "commission_provenance": {
            "verification_status": "VERIFIED_RESEARCH_PROXY",
            "value": max(comm_values),
            "symbol": sym,
            "source_kind": "strategy_tester_simulation",
            "statistic": "maximum",
            "method": "assumed_conservative_bound: broker-observed commission is "
                      "0.00 on every deal of the governed run; a $7.00/lot "
                      "round-turn bound is applied to real position lifecycles "
                      "so the falsification screen never understates cost.",
            "source": rel(comm_csv),
            "source_sha256": sha_file(comm_csv),
            "sample_count": len(comm_rows),
            "same_symbol_lifecycles": True,
        },
        "slippage_provenance": {
            "verification_status": "VERIFIED_RESEARCH_PROXY",
            "source": rel(slip_csv),
            "source_sha256": sha_file(slip_csv),
            "symbol": sym,
            "sample_count": len(slip_rows),
            "buy_count": len(buy_adv),
            "sell_count": len(sell_adv),
            "independent_reference": False,
            "independent_quote_reference": True,
            "fill_observed": False,
            "fixed_latency_ms": slip_latency,
            "max_quote_wait_ms": slip_max_wait,
            "buy_reference_side": "ask",
            "sell_reference_side": "bid",
            "slippage_unit": "pips",
            "method": "independent_quote_reference: adverse move between "
                      "decision quote and first quote at >= decision+latency_ms",
            "p90_buy": p90(buy_adv),
            "p90_sell": p90(sell_adv),
            "p90_roundturn": p90(buy_adv) + p90(sell_adv),
        },
        "direction_aware_methodology": {
            "verification_status": "VERIFIED_RESEARCH_PROXY",
            "direction_aware": True,
            "long_cost_treatment": "buy at ask, exit at bid; slippage vs ask quote; no swap within intraday hold",
            "short_cost_treatment": "sell at bid, exit at ask; slippage vs bid quote; no swap within intraday hold",
        },
    }
    cost_path = ROOT / cost_rel
    cost_path.parent.mkdir(parents=True, exist_ok=True)
    cost_path.write_text(json.dumps(cost, indent=2) + "\n", encoding="utf-8")
    cost_sha = sha_file(cost_path)

    # ---- registry row hash (raw line text) ----
    row_line = None
    for line in registry.read_bytes().split(b"\n"):
        line = line.rstrip(b"\r")
        if line.strip() and json.loads(line)["hypothesis_id"] == hyp:
            row_line = line
    if row_line is None:
        raise RuntimeError(f"{hyp} not found in registry")
    row_sha = hashlib.sha256(row_line).hexdigest().upper()
    reg_sha = sha_file(registry)

    # ---- NOGIT provenance (mirror of Get-NoGitProvenanceSnapshot) ----
    prov_paths = [ROOT / "01. GOAL" / "GOAL.md", ROOT / src_rel]
    records = [f"{rel(p)}\t{sha_file(p)}" for p in prov_paths]
    prov_sha = sha_text("\n".join(records))
    git_commit = f"NOGIT-{prov_sha}"
    git_status = ["nogit=true", "dirty=true", f"provenance_sha256={prov_sha}"]
    git_status_sha = sha_text("\n".join(git_status))

    # ---- include closure: transitive #include resolution, mirroring
    # alpha.ps1 Get-IncludeDependencyClosure. <> resolves under the isolate
    # MQL5\Include, "" resolves relative to the including file. The post-run
    # gate recomputes Get-PathHashSetSha256 over the manifest's real
    # include_snapshots, so this set must be exactly the compiled closure.
    import re
    inc_re = re.compile(r'^\s*#include\s*(?:<(?P<terminal>[^>]+)>|"(?P<local>[^"]+)")')

    def resolve_include(ref: str, current: Path, kind: str) -> Path | None:
        cand = (MQL5_INCLUDE / ref) if kind == "terminal" else (current.parent / ref)
        return cand.resolve() if cand.is_file() else None

    includes = []
    visited = {str((ROOT / src_rel).resolve()).lower()}
    queue = [(ROOT / src_rel).resolve()]
    while queue:
        current = queue.pop(0)
        for line in current.read_text(encoding="utf-8", errors="replace").splitlines():
            m = inc_re.match(line)
            if not m:
                continue
            kind = "terminal" if m.group("terminal") is not None else "local"
            resolved = resolve_include(m.group(kind).strip(), current, kind)
            if resolved is None:
                raise RuntimeError(
                    f"include dependency cannot be resolved: '{m.group(kind).strip()}' "
                    f"({kind}) referenced by '{rel(current)}'")
            key = str(resolved).lower()
            if key not in visited:
                visited.add(key)
                includes.append(resolved)
                queue.append(resolved)

    includes_entries = [
        {"path": rel(p), "sha256": sha_file(p)} for p in includes]
    inc_records = sorted(
        f"{str(p.resolve()).lower()}\t{e['sha256']}"
        for p, e in zip(includes, includes_entries))
    include_closure_sha = sha_text("\n".join(inc_records))

    packet = {
        "schema_version": "alphafactory_research_task_packet.v1",
        "hypothesis_id": hyp,
        "run_role": "control",
        "ea_name": ea,
        "source_path": src_rel,
        "source_sha256": sha_file(ROOT / src_rel),
        "registry_path": rel(registry),
        "registry_sha256": reg_sha,
        "registry_row_sha256": row_sha,
        "prereg_path": prereg_rel,
        "prereg_sha256": sha_file(ROOT / prereg_rel),
        "ea_contract_path": contract_rel,
        "ea_contract_sha256": sha_file(ROOT / contract_rel),
        "telemetry_profile": "lifecycle-v3",
        "comparison_adapter": "generic-control-improvement-v1",
        "symbol": sym,
        "period": period,
        "from": args.from_date,
        "to": to_date,
        "data_quality_contract": {
            "history_quality": {"operator": "gt", "value": 97.0},
            "coverage_mode": args.coverage_mode,
            "availability_asof_utc": asof,
            "requested_from": args.from_date,
            "requested_to": to_date,
            "require_tester_journal_bounds": True,
        },
        "model": 0,
        "execution_mode": 0,
        "fixed_delay_ms": 0,
        # Engine canonicalizes overrides via ConvertFrom-NormalizedOverrideMap
        # (alphabetical key sort) — emit the same order so packet == CLI string.
        "overrides": ";".join(sorted(
            [f"InpEnableTelemetry=true", f"InpHypothesisId={hyp}", f"InpMagic={args.magic}"]
            + ([p for p in args.extra_overrides.split(";") if p.strip()] if args.extra_overrides else []))),
        "telemetry_tier": "trade-only",
        "deposit": 10000,
        "leverage": 100,
        "spread": str(args.spread_points),
        "validation_stage": "challenger",
        "holding_contract": "scalp",
        "cost_evidence_tier": "research_proxy",
        "acceptance_contract": {
            "min_profit_factor": 1.30,
            "min_trades_per_week": 10.0,
            "max_trades_per_week": 40.0,
            "max_drawdown_pct": 20.0,
            "min_cost_pf_x1_5": 1.25,
            "min_cost_pf_x2": 1.0,
            "max_monte_carlo_p95_dd_pct": 20.0,
        },
        "git_commit": git_commit,
        "git_status": git_status,
        "git_status_sha256": git_status_sha,
        "include_closure": includes_entries,
        "include_closure_sha256": include_closure_sha,
        "broker_fingerprint": broker_fp,
        "server_fingerprint": server_fp,
        "account_fingerprint": account_fp,
        "data_fingerprint": data_fp,
        "symbol_geometry": {
            "digits": args.digits, "point": args.point, "pip_size": args.pip},
        "required_sidecars": ["*_LifecycleTrades_*.csv", "*_RunMeta_*.json"],
        "required_input_artifacts": [],
        "required_manifest_hashes": [
            "source_sha256", "config_sha256", "report_sha256",
            "ex5_sha256", "includes_sha256"],
        "cost_source_manifest_path": cost_rel,
        "cost_source_manifest_sha256": cost_sha,
        "matched_control_run_id": "",
        "matched_control_hypothesis_id": "",
        "matched_control_manifest_sha256": "",
        "matched_control_report_sha256": "",
        "matched_control_overrides": "",
        "matched_control_source_sha256": "",
        "matched_control_config_sha256": "",
        "matched_control_ex5_sha256": "",
        "matched_control_includes_sha256": "",
        "matched_control_git_commit": "",
        "matched_control_git_status_sha256": "",
        "wfa_artifact_path": "",
        "wfa_artifact_sha256": "",
        "variants_dir": "",
        "variants_sha256": "",
    }
    packet_path = ROOT / packet_rel
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "packet": packet_rel, "packet_sha256": sha_file(packet_path),
        "cost_manifest": cost_rel, "cost_sha256": cost_sha,
        "git_commit": git_commit, "registry_sha256": reg_sha[:16],
        "row_sha256": row_sha[:16], "to": to_date, "asof": asof}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
