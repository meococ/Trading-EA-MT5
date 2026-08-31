"""Build analysis manifest by scanning AlphaFactory run directories.

Detects existing analysis artifacts per run and writes a machine-readable
manifest to ``02. AlphaFactory/runs/.analysis_manifest.json``.

Idempotent — safe to re-run at any time.
"""

from __future__ import annotations

import json
from pathlib import Path

RUNS_DIR = Path(__file__).resolve().parent.parent / "runs"
MANIFEST_PATH = RUNS_DIR / ".analysis_manifest.json"


def _scan_run(run_dir: Path) -> dict:
    """Return artifact presence flags for a single run directory."""
    analysis = run_dir / "analysis"
    return {
        "report": (run_dir / "report.html").exists(),
        "analyzed": analysis.exists() and any(analysis.glob("enhanced_summary*.json")),
        "wfa": (run_dir / "walk_forward").exists(),
        "mc": (run_dir / "monte_carlo").exists(),
        "robustness": (run_dir / "robustness").exists(),
        "config": (run_dir / "config.ini").exists(),
        "manifest": (run_dir / "run_manifest.json").exists(),
        "datalog": (analysis / "datalog").exists() if analysis.exists() else False,
    }


def build_manifest() -> dict:
    """Walk all EA run directories and build the manifest."""
    entries: dict[str, dict] = {}

    if not RUNS_DIR.exists():
        return {"version": 1, "runs": entries}

    for ea_dir in sorted(RUNS_DIR.iterdir()):
        if not ea_dir.is_dir() or ea_dir.name.startswith("."):
            continue
        for run_dir in sorted(ea_dir.iterdir()):
            if not run_dir.is_dir():
                continue
            key = f"{ea_dir.name}/{run_dir.name}"
            artifacts = _scan_run(run_dir)
            # Count completeness
            total = sum(1 for v in artifacts.values() if v)
            artifacts["completeness"] = f"{total}/8"
            entries[key] = artifacts

    return {"version": 1, "total_runs": len(entries), "runs": entries}


def main() -> None:
    manifest = build_manifest()
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Manifest written: {MANIFEST_PATH}")
    print(f"Total runs indexed: {manifest['total_runs']}")

    # Summary stats
    complete = sum(1 for r in manifest["runs"].values() if r.get("completeness") == "8/8")
    has_wfa = sum(1 for r in manifest["runs"].values() if r.get("wfa"))
    has_mc = sum(1 for r in manifest["runs"].values() if r.get("mc"))
    has_robust = sum(1 for r in manifest["runs"].values() if r.get("robustness"))
    print(f"Fully complete: {complete} | WFA: {has_wfa} | MC: {has_mc} | Robustness: {has_robust}")


if __name__ == "__main__":
    main()
