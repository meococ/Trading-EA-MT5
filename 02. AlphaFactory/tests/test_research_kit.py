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
    assert manifest["time_col"] == "time_utc"
    assert len(manifest["results"]) == 2
    for r in manifest["results"]:
        assert r["status"] == "RENDERED"
        assert r["cutoff_enforced"] is True
        assert r["outcome_hidden"] is True
        assert r["net_r_hidden"] is True
        assert r["label_hidden_in_image"] is True
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
    assert win["outcome_hidden"] is False
    assert win["net_r_hidden"] is False
    assert win["label_hidden_in_image"] is False


def test_render_forensic_context_panel_and_trade_markers(tmp_path: Path) -> None:
    bars = _bars(tmp_path)
    cases = _cases(tmp_path)
    out_dir = tmp_path / "forensic"
    result = subprocess.run(
        [
            sys.executable,
            str(KIT / "chart_case_render.py"),
            "--bars", str(bars),
            "--cases", str(cases),
            "--out-dir", str(out_dir),
            "--mode", "anatomy",
            "--overlay", "ema:20",
            "--context-timeframe", "H4",
            "--context-bars", "24",
            "--context-overlay", "ema:20",
            "--context-overlay", "ema:50",
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    manifest = json.loads((out_dir / "cases_manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "chart_case_render.v2"
    assert manifest["context_timeframe"] == "H4"
    win = next(row for row in manifest["results"] if row["case_id"] == "case_win")
    assert win["entry_marker_rendered"] is True
    assert win["sl_line_rendered"] is True
    assert win["tp_line_rendered"] is True
    assert win["exit_marker_rendered"] is True
    assert win["label"] == "top_win"
    assert win["direction"] == 1
    assert win["context"]["timeframe"] == "H4"
    assert win["context"]["cutoff_enforced"] is True
    assert pd.Timestamp(win["context"]["last_bar_close"]) <= pd.Timestamp(
        "2021-06-05 12:00"
    )
    assert win["context"]["bars_drawn"] == 24
    png = out_dir / win["png"]
    assert png.name.endswith("_anatomy_h4.png")
    assert png.is_file() and png.stat().st_size > 10_000


def test_htf_panel_places_entry_on_partial_asof_bar_without_future(tmp_path: Path) -> None:
    times = pd.date_range("2024-06-10 00:00", periods=700, freq="5min")
    base = 1.0700 + pd.Series(range(len(times))) * 0.000002
    bars = pd.DataFrame(
        {
            "time_utc": times,
            "open": base,
            "high": base + 0.00020,
            "low": base - 0.00020,
            "close": base + 0.00005,
        }
    )
    bars_path = tmp_path / "m5.parquet"
    bars.to_parquet(bars_path, index=False)
    entry_time = pd.Timestamp("2024-06-12 08:45:00")
    cases = pd.DataFrame(
        [
            {
                "case_id": "partial_h1",
                "entry_time_utc": entry_time,
                "direction": -1,
                "entry": 1.0750,
                "sl": 1.0755,
                "tp": 1.0740,
                "exit_time_utc": "2024-06-12 09:05:00",
                "exit": 1.0747,
                "reason": "test",
                "sweep_time_utc": "2024-06-12 08:30:00",
                "pivot": 1.0752,
                "sweep_high": 1.0753,
                "sweep_low": 1.0750,
                "sweep_close": 1.0751,
                "sweep_depth_pips": 1.0,
                "sweep_reclaim_pips": 1.0,
                "confirmation_time_utc": "2024-06-12 08:40:00",
                "confirmation_close": 1.0750,
                "confirmation_body_vs_prior20": 1.2,
                "confirmation_directional_close_location": 0.8,
                "bars_after_sweep": 2,
            }
        ]
    )
    cases_path = tmp_path / "partial_cases.csv"
    cases.to_csv(cases_path, index=False)
    out_dir = tmp_path / "partial_h1_out"
    result = subprocess.run(
        [
            sys.executable,
            str(KIT / "chart_case_render.py"),
            "--bars", str(bars_path),
            "--cases", str(cases_path),
            "--out-dir", str(out_dir),
            "--mode", "anatomy",
            "--context-timeframe", "H1",
            "--context-bars", "24",
            "--context-entry-position", "center",
            "--context-overlay", "ema:20",
            "--context-overlay", "ema:50",
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    manifest = json.loads((out_dir / "cases_manifest.json").read_text(encoding="utf-8"))
    row = manifest["results"][0]
    context = row["context"]
    assert context["partial_bar_included"] is True
    assert pd.Timestamp(context["partial_bar_start"]) == pd.Timestamp("2024-06-12 08:00:00")
    assert pd.Timestamp(context["partial_available_through"]) == entry_time
    assert pd.Timestamp(context["partial_scheduled_close"]) == pd.Timestamp(
        "2024-06-12 09:00:00"
    )
    assert context["entry_marker_on_partial_bar"] is True
    assert context["cutoff_enforced"] is True
    assert context["entry_position"] == "center"
    assert context["future_region_hidden"] is True
    assert abs(context["entry_anchor_fraction"] - 0.5) <= 0.02
    setup_chain = row["setup_chain"]
    assert setup_chain["rendered"] is True
    assert setup_chain["sequence_valid"] is True
    assert pd.Timestamp(setup_chain["sweep_time"]) == pd.Timestamp(
        "2024-06-12 08:30:00"
    )
    assert pd.Timestamp(setup_chain["confirmation_time"]) == pd.Timestamp(
        "2024-06-12 08:40:00"
    )
    assert setup_chain["pivot_price"] == 1.0752

    anatomy_out = tmp_path / "partial_h1_anatomy_out"
    anatomy_result = subprocess.run(
        [
            sys.executable,
            str(KIT / "chart_case_render.py"),
            "--bars", str(bars_path),
            "--cases", str(cases_path),
            "--out-dir", str(anatomy_out),
            "--mode", "anatomy",
            "--context-timeframe", "H1",
            "--context-bars", "24",
            "--context-entry-position", "center",
            "--context-post-bars", "6",
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert anatomy_result.returncode == 0, anatomy_result.stdout + anatomy_result.stderr
    anatomy_manifest = json.loads(
        (anatomy_out / "cases_manifest.json").read_text(encoding="utf-8")
    )
    anatomy_context = anatomy_manifest["results"][0]["context"]
    assert anatomy_context["view"] == "anatomy"
    assert anatomy_context["post_entry_bars_drawn"] >= 1
    assert anatomy_context["post_entry_outcome_region"] is True
    assert anatomy_context["future_region_hidden"] is False
    assert anatomy_context["entry_bar_full_outcome"] is True
    assert anatomy_context["decision_state_cutoff_enforced"] is True
    assert abs(anatomy_context["entry_anchor_fraction"] - 0.5) <= 0.02


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
