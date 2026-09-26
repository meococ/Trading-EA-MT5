#!/usr/bin/env python3
"""Build data-acquisition contract receipts for new symbols.

Replicates the _dataacq receipt shape used for the 12-symbol sync wave.
Data acquisition only — EA_ExecutionKernelHarness trades nothing.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EA_REL = r"03. EA Developer\EA_ExecutionKernelHarness\EA_ExecutionKernelHarness.mq5"
PREREG_REL = r"03. EA Developer\EA_ExecutionKernelHarness\research\HYP-DATAACQ_PREREG.md"
FROM, TO = "2010.01.01", "2026.09.18"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest().upper()


def git_snapshot():
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    out = subprocess.run(["git", "status", "--short",
                          "--untracked-files=all"], cwd=ROOT,
                         capture_output=True, text=True).stdout
    lines = [l for l in out.replace("\r\n", "\n").split("\n") if l]
    return commit, sha256_text("\n".join(lines))


def build(sym: str, commit: str, status_sha: str):
    is_jpy = sym.endswith("JPY")
    geom = {"digits": 3, "point": 0.001, "pip_size": 0.01} if is_jpy else \
           {"digits": 5, "point": 0.00001, "pip_size": 0.0001}
    hyp = f"HYP-DATAACQ-{sym}-001"
    d = ROOT / "02. AlphaFactory" / "runs" / "_dataacq" / sym
    d.mkdir(parents=True, exist_ok=True)
    packet = {
        "schema_version": "sonic_research_task_packet.v1",
        "hypothesis_id": hyp, "ea_name": "EA_ExecutionKernelHarness",
        "symbol": sym, "period": "M1", "from": FROM, "to": TO, "model": 2,
        "run_role": "control", "overrides": "",
        "note": "Data acquisition only; EA trades nothing.",
    }
    (d / "task_packet.json").write_text(json.dumps(packet, indent=2) + "\n",
                                        encoding="utf-8")
    prereg_p = ROOT / PREREG_REL
    (d / "prereg.json").write_text(json.dumps({
        "hypothesis_id": hyp, "prereg_path": PREREG_REL,
        "prereg_sha256": sha256_file(prereg_p), "frozen": True},
        indent=2) + "\n", encoding="utf-8")
    (d / "cost_source_manifest.json").write_text(json.dumps({
        "cost_provenance": "UNVERIFIED", "spread_policy": "tester_current",
        "commission": "unknown_not_zero", "slippage": "unknown_not_zero",
        "note": "Data acquisition; no economics."}, indent=2) + "\n",
        encoding="utf-8")
    tp_sha = sha256_file(d / "task_packet.json")
    empty_sha = sha256_text("")
    receipt = {
        "schema_version": "sonic_execution_receipt.v1",
        "hypothesis_id": hyp, "task_packet_sha256": tp_sha,
        "git_commit": commit, "git_status_sha256": status_sha,
        "binding": {
            "hypothesis_id": hyp, "run_role": "control",
            "ea_name": "EA_ExecutionKernelHarness", "symbol": sym,
            "period": "M1", "from": FROM, "to": TO, "model": 2,
            "execution_mode": 0, "fixed_delay_ms": 0, "overrides": "",
            "telemetry_tier": "off", "deposit": 10000, "leverage": 100,
            "spread": "current", "required_sidecars": [],
            "symbol_geometry": geom,
            "include_closure_sha256": empty_sha},
        "evidence": [
            {"label": "task_packet", "kind": "file",
             "path": str(d / "task_packet.json"), "sha256": tp_sha},
            {"label": "source", "kind": "file",
             "path": str(ROOT / EA_REL), "sha256": sha256_file(ROOT / EA_REL)},
            {"label": "prereg", "kind": "file", "path": str(d / "prereg.json"),
             "sha256": sha256_file(d / "prereg.json")},
            {"label": "cost_source_manifest", "kind": "file",
             "path": str(d / "cost_source_manifest.json"),
             "sha256": sha256_file(d / "cost_source_manifest.json")}],
        "generated_at_utc": "2026-09-20T00:00:00Z",
        "note": "History acquisition run; no economics authorized.",
    }
    (d / "contract_receipt.json").write_text(json.dumps(receipt, indent=2),
                                            encoding="utf-8")
    rsha = sha256_file(d / "contract_receipt.json")
    (d / "contract_receipt.sha256.txt").write_text(rsha, encoding="utf-8")
    print(sym, rsha[:16])


if __name__ == "__main__":
    commit, status_sha = git_snapshot()
    print("commit", commit[:12], "status", status_sha[:16])
    for sym in sys.argv[1:]:
        build(sym, commit, status_sha)
