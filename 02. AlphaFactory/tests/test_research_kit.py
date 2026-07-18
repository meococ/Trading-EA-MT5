"""Contract tests for tools/research: chart_case_render + log_triage."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

WORKSPACE = Path(__file__).resolve().parents[2]
KIT = WORKSPACE / "02. AlphaFactory" / "tools" / "research"


def _bars(tmp: Path) -> Path:
    t = pd.date_range("2021-06-01 00:00", periods=200, freq="h")
    base = 1.10 + pd.Series(range(200)) * 0.0001
    df = pd.DataFrame({
        "time_utc": t,
        "open": base,
        "high": base + 0.0004,
        "low": base - 0.0004,
        "close": base + 0.0002,
    })
    out = tmp / "bars.parquet"
    df.to_parquet(out, index=False)
    return out


def _cases(tmp: Path) -> Path:
    df = pd.DataFrame([
        {"case_id": "case_win", "entry_time_utc": "2021-06-05 12:00", "direction": 1,
         "entry": 1.1105, "sl": 1.1085, "tp": 1.1135,
         "exit_time_utc": "2021-06-06 04:00", "exit": 1.1135, "reason": "TP",
         "label": "top_win"},
        {"case_id": "case_loss", "entry_time_utc": "2021-06-07 09:00", "direction": -1,
         "entry": 1.1150, "sl": 1.1170, "tp": 1.1120,
         "exit_time_utc": "2021-06-07 20:00", "exit": 1.1170, "reason": "SL",
         "label": "top_loss"},
    ])
    out = tmp / "cases.csv"
    df.to_csv(out, index=False)
    return out


def _run_render(bars: Path, cases: Path, out_dir: Path, mode: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(KIT / "chart_case_render.py"),
         "--bars", str(bars), "--cases", str(cases),
         "--out-dir", str(out_dir), "--mode", mode, "--overlay", "sma:20"],
        capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads((out_dir / "cases_manifest.json").read_text(encoding="utf-8"))


def test_render_asof_enforces_entry_cutoff(tmp_path: Path) -> None:
    manifest = _run_render(_bars(tmp_path), _cases(tmp_path), tmp_path / "asof", "asof")
    assert len(manifest["results"]) == 2
    for r in manifest["results"]:
        assert r["status"] == "RENDERED"
        assert r["cutoff_enforced"] is True
        entry_time = {"case_win": "2021-06-05 12:00", "case_loss": "2021-06-07 09:00"}[r["case_id"]]
        assert pd.Timestamp(r["last_bar"]) < pd.Timestamp(entry_time)
        png = tmp_path / "asof" / r["png"]
        assert png.is_file() and png.stat().st_size > 5000
        assert len(r["sha256"]) == 64


def test_render_anatomy_reaches_exit(tmp_path: Path) -> None:
    manifest = _run_render(_bars(tmp_path), _cases(tmp_path), tmp_path / "anat", "anatomy")
    win = next(r for r in manifest["results"] if r["case_id"] == "case_win")
    assert win["status"] == "RENDERED"
    assert pd.Timestamp(win["last_bar"]) >= pd.Timestamp("2021-06-06 04:00")


def test_log_triage_flags_and_clean(tmp_path: Path) -> None:
    dirty = tmp_path / "dirty.log"
    dirty.write_text(
        "line ok\nTRADE_RETCODE_REQUOTE at 10:00\nnoise\n"
        "order rejected by dealer\nM2_LEDGER_FATAL boom\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(KIT / "log_triage.py"), str(dirty)],
        capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads(dirty.with_suffix(".log.triage.json").read_text(encoding="utf-8"))
    assert summary["clean"] is False
    assert summary["battery"]["requote"]["count"] == 1
    assert summary["battery"]["order_reject"]["count"] == 1
    assert summary["battery"]["ledger_fatal"]["count"] == 1
    assert summary["battery"]["requote"]["samples"][0]["line"] == 2

    clean = tmp_path / "clean.log"
    clean.write_text("all good\nnothing here\n", encoding="utf-8")
    subprocess.run([sys.executable, str(KIT / "log_triage.py"), str(clean)],
                   capture_output=True, text=True, timeout=60, check=True)
    summary2 = json.loads(clean.with_suffix(".log.triage.json").read_text(encoding="utf-8"))
    assert summary2["clean"] is True
