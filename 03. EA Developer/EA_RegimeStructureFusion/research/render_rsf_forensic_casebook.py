#!/usr/bin/env python3
"""Render outcome-blind and anatomy charts from the real RSF replay buffers.

The outcome-blind view stops before the entry bar and never prints the result.
The anatomy view is a separate artifact that may show the exit and realized R.
Indicator rows come from the hash-bound MT5 replay; they are not recomputed in
Python.  Price candles come from the canonical EURUSD M5 parquet epoch.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont


SCHEMA = "rsf_forensic_casebook.v1"
BG = "#0d1117"
GRID = "#30363d"
TEXT = "#e6edf3"
MUTED = "#8b949e"
GREEN = "#00c853"
RED = "#ff1744"
BLUE = "#00b7ff"
ORANGE = "#f0a23b"
PURPLE = "#a371f7"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def as_num(frame: pd.DataFrame, columns: list[str]) -> None:
    for column in columns:
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")


def draw_candles(ax: plt.Axes, bars: pd.DataFrame) -> None:
    for i, row in bars.reset_index(drop=True).iterrows():
        up = row.close >= row.open
        color = "#26a69a" if up else "#ef5350"
        ax.vlines(i, row.low, row.high, color=color, linewidth=0.75, zorder=2)
        low, high = sorted((row.open, row.close))
        ax.add_patch(
            plt.Rectangle(
                (i - 0.34, low), 0.68, max(high - low, 1e-7),
                facecolor=color, edgecolor=color, linewidth=0.55, zorder=3,
            )
        )


def x_for_time(bars: pd.DataFrame, value: pd.Timestamp, side: str = "left") -> int:
    values = bars["time_utc"].to_numpy(dtype="datetime64[ns]")
    x = int(values.searchsorted(value.to_datetime64(), side=side))
    return min(max(x, 0), max(len(bars) - 1, 0))


def signal_name(row: pd.Series) -> str:
    pairs = [
        ("s1_long", "S1L"), ("s1_short", "S1S"),
        ("s2_long", "S2L"), ("s2_short", "S2S"),
        ("s3_long", "S3L"), ("s3_short", "S3S"),
    ]
    return "+".join(label for key, label in pairs if int(row.get(key, 0) or 0)) or "none"


def regime_name(value: int) -> str:
    return {0: "BULL", 1: "BEAR", 2: "RANGE", 3: "HIGHVOL"}.get(value, str(value))


def vrc_name(value: int) -> str:
    return {
        -1: "STRONG BEAR", 0: "BEAR", 1: "WEAK BEAR", 2: "MEAN REV",
        3: "RANGE", 4: "WEAK BULL", 5: "BULL", 6: "STRONG BULL",
        7: "COMPRESSION",
    }.get(value, str(value))


def style_axis(ax: plt.Axes) -> None:
    ax.set_facecolor(BG)
    ax.grid(True, color=GRID, linewidth=0.5, alpha=0.65)
    ax.tick_params(colors=MUTED, labelsize=7)
    for spine in ax.spines.values():
        spine.set_color(GRID)


def plot_level(ax: plt.Axes, ind: pd.DataFrame, bars: pd.DataFrame, column: str,
               color: str, label: str, style: str = "--", alpha: float = 0.7) -> None:
    data = ind[["source_bar_time_utc", column]].dropna()
    data = data[data[column] != 0]
    if data.empty:
        return
    xs = [x_for_time(bars, t) for t in data.source_bar_time_utc]
    ax.plot(xs, data[column], color=color, linewidth=0.9, linestyle=style,
            alpha=alpha, label=label)


def render_case(case: pd.Series, alias: str, bars_all: pd.DataFrame,
                replay: pd.DataFrame, out_dir: Path, mode: str) -> dict:
    entry = pd.Timestamp(case.entry_time_utc)
    exit_t = pd.Timestamp(case.exit_time_utc)
    if mode == "asof":
        start = entry - pd.Timedelta(hours=8)
        end = entry - pd.Timedelta(microseconds=1)
    else:
        start = entry - pd.Timedelta(hours=3)
        end = max(exit_t + pd.Timedelta(hours=1), entry + pd.Timedelta(hours=2))
    bars = bars_all[(bars_all.time_utc >= start) & (bars_all.time_utc <= end)].copy()
    bars = bars.sort_values("time_utc").reset_index(drop=True)
    if bars.empty:
        raise RuntimeError(f"no bars for {case.case_id} {mode}")
    ind = replay[
        (replay.source_bar_time_utc >= bars.time_utc.iloc[0])
        & (replay.source_bar_time_utc <= bars.time_utc.iloc[-1])
    ].copy().sort_values("source_bar_time_utc")
    decision = replay[replay.decision_time_server == case.entry_time_server]
    if len(decision) != 1:
        raise RuntimeError(f"{case.case_id}: expected one decision snapshot, got {len(decision)}")
    d = decision.iloc[0]

    fig = plt.figure(figsize=(18, 12), facecolor=BG)
    gs = fig.add_gridspec(6, 1, height_ratios=[3.8, 1.25, 1.1, 1.1, 1.1, 0.15], hspace=0.08)
    axp = fig.add_subplot(gs[0])
    axa = fig.add_subplot(gs[1], sharex=axp)
    axv = fig.add_subplot(gs[2], sharex=axp)
    axm = fig.add_subplot(gs[3], sharex=axp)
    axq = fig.add_subplot(gs[4], sharex=axp)
    for ax in (axp, axa, axv, axm, axq):
        style_axis(ax)

    draw_candles(axp, bars)
    plot_level(axp, ind, bars, "mbb_upper", BLUE, "MBB upper", "-", 0.8)
    plot_level(axp, ind, bars, "mbb_basis", "#ffffff", "MBB basis", "-", 0.85)
    plot_level(axp, ind, bars, "mbb_lower", BLUE, "MBB lower", "-", 0.8)
    plot_level(axp, ind, bars, "tb_swing_high", ORANGE, "TB swing H")
    plot_level(axp, ind, bars, "tb_swing_low", ORANGE, "TB swing L")
    plot_level(axp, ind, bars, "tb_structure_level", PURPLE, "TB structure", ":", 0.9)
    plot_level(axp, ind, bars, "tb_cell_top", "#ffcc80", "TB cell", ":", 0.55)
    plot_level(axp, ind, bars, "tb_cell_bottom", "#ffcc80", "_nolegend_", ":", 0.55)
    plot_level(axp, ind, bars, "tb_void_top", "#80deea", "TB void", ":", 0.55)
    plot_level(axp, ind, bars, "tb_void_bottom", "#80deea", "_nolegend_", ":", 0.55)

    xentry = len(bars) - 0.25 if mode == "asof" else x_for_time(bars, entry)
    direction = int(case.direction)
    marker = "^" if direction > 0 else "v"
    side_color = GREEN if direction > 0 else RED
    axp.scatter([xentry], [float(case.entry)], marker=marker, s=110, color=side_color,
                edgecolor="white", linewidth=0.8, zorder=8, label="entry")
    axp.axhline(float(case.entry), color=side_color, linewidth=0.7, alpha=0.6)
    axp.axhline(float(case.sl), color=RED, linewidth=0.8, linestyle="--", alpha=0.85, label="SL")
    axp.axhline(float(case.tp), color=GREEN, linewidth=0.8, linestyle="--", alpha=0.85, label="TP")
    if mode == "anatomy":
        xexit = x_for_time(bars, exit_t)
        axp.scatter([xexit], [float(case.exit)], marker="X", s=90, color="#ffd54f",
                    edgecolor="black", linewidth=0.7, zorder=8, label="exit")
        axp.axvspan(xentry, xexit, color=side_color, alpha=0.06)

    # TB event markers use the replay buffers directly.
    for col, mark, color, ycol in [
        ("tb_structure_up", "^", GREEN, "low"),
        ("tb_structure_down", "v", RED, "high"),
        ("tb_sweep_high", "x", RED, "high"),
        ("tb_sweep_low", "x", GREEN, "low"),
    ]:
        events = ind[ind[col] == 1]
        if not events.empty:
            xs = [x_for_time(bars, t) for t in events.source_bar_time_utc]
            ys = [float(bars.iloc[x][ycol]) for x in xs]
            axp.scatter(xs, ys, marker=mark, s=24, color=color, zorder=7, alpha=0.8)

    title = (
        f"{alias}  |  {case.engine_name} {case.direction_name}  |  decision {entry} UTC  |  OUTCOME HIDDEN"
        if mode == "asof"
        else f"{case.case_id}  |  {case.engine_name} {case.direction_name}  |  {case.net_r:+.2f}R  {case.reason}"
    )
    axp.set_title(title, color=TEXT, fontsize=12, loc="left", fontweight="bold")
    axp.set_ylabel("EURUSD", color=MUTED, fontsize=8)
    axp.legend(loc="upper left", ncol=5, fontsize=6, framealpha=0.25)

    # AIRD: probabilities are exported in percentage points, confidence is 0..1.
    if not ind.empty:
        xs = [x_for_time(bars, t) for t in ind.source_bar_time_utc]
        for col, color, label in [
            ("p_bull", GREEN, "P Bull"), ("p_bear", RED, "P Bear"),
            ("p_range", "#448aff", "P Range"), ("p_highvol", ORANGE, "P HighVol"),
        ]:
            axa.plot(xs, ind[col], color=color, linewidth=1.0, label=label)
        axa.plot(xs, ind.aird_confidence * 100.0, color="white", linewidth=1.5,
                 linestyle="--", label="held confidence")
    axa.set_ylim(0, 102)
    axa.set_ylabel("AIRD %", color=MUTED, fontsize=8)
    axa.legend(loc="upper left", ncol=5, fontsize=6, framealpha=0.25)

    if not ind.empty:
        axv.plot(xs, ind.vrc_vol_percentile, color="#00bcd4", linewidth=1.3, label="Vol percentile")
        axv.plot(xs, 50 + 25 * ind.vrc_direction, color="white", linewidth=1.0,
                 linestyle="--", label="Direction (scaled)")
        colors = ["#ff1744" if v <= 1 else "#7c4dff" if v == 2 else "#ffd600" if v == 3 else "#00c853" if v <= 6 else "#00bcd4" for v in ind.vrc_regime]
        axv.scatter(xs, np.full(len(xs), 6), c=colors, s=11, label="VRC regime")
    axv.axhline(80, color=RED, linewidth=0.6, linestyle=":")
    axv.axhline(20, color=BLUE, linewidth=0.6, linestyle=":")
    axv.set_ylim(0, 100)
    axv.set_ylabel("VRC", color=MUTED, fontsize=8)
    axv.legend(loc="upper left", ncol=3, fontsize=6, framealpha=0.25)

    if not ind.empty:
        axm.plot(xs, ind.mbb_squeeze, color=BLUE, linewidth=1.3, label="Squeeze score")
        for col, mark, color, y, label in [
            ("s1_long", "^", GREEN, 88, "S1L"), ("s1_short", "v", RED, 88, "S1S"),
            ("s2_long", "o", GREEN, 72, "S2L"), ("s2_short", "o", RED, 72, "S2S"),
            ("s3_long", "D", GREEN, 55, "S3L"), ("s3_short", "D", RED, 55, "S3S"),
        ]:
            points = ind[ind[col] == 1]
            if not points.empty:
                xp = [x_for_time(bars, t) for t in points.source_bar_time_utc]
                axm.scatter(xp, [y] * len(xp), marker=mark, s=24, color=color, label=label)
        release = ind[ind.mbb_release == 1]
        if not release.empty:
            xr = [x_for_time(bars, t) for t in release.source_bar_time_utc]
            axm.scatter(xr, [35] * len(xr), marker="*", s=40, color="#ffd54f", label="release")
    axm.axhline(20, color="#ffd54f", linewidth=0.7, linestyle=":")
    axm.set_ylim(0, 100)
    axm.set_ylabel("MBB", color=MUTED, fontsize=8)
    axm.legend(loc="upper left", ncol=8, fontsize=6, framealpha=0.25)

    if not ind.empty:
        axq.plot(xs, ind.qqe_primary, color=BLUE, linewidth=1.3, label="QQE primary")
        axq.plot(xs, ind.qqe_secondary, color="white", linewidth=1.0, label="QQE secondary")
    axq.axhline(0, color=MUTED, linewidth=0.8, linestyle=":")
    axq.axhline(3, color=GREEN, linewidth=0.6, linestyle="--")
    axq.axhline(-3, color=RED, linewidth=0.6, linestyle="--")
    axq.set_ylabel("QQE", color=MUTED, fontsize=8)
    axq.legend(loc="upper left", ncol=2, fontsize=6, framealpha=0.25)

    tick_idx = list(range(0, len(bars), max(1, len(bars) // 9)))
    axq.set_xticks(tick_idx)
    axq.set_xticklabels([bars.time_utc.iloc[i].strftime("%m-%d\n%H:%M") for i in tick_idx], color=MUTED)
    for ax in (axp, axa, axv, axm):
        plt.setp(ax.get_xticklabels(), visible=False)
    for ax in (axa, axv, axm, axq):
        ax.set_xlim(-1, len(bars))

    entry_state = (
        f"ENTRY STATE (real closed-bar buffers)\n"
        f"AIRD {regime_name(int(d.aird_regime))}  conf {d.aird_confidence*100:.1f}%  "
        f"P[B/B/R/V]={d.p_bull:.1f}/{d.p_bear:.1f}/{d.p_range:.1f}/{d.p_highvol:.1f}\n"
        f"VRC {vrc_name(int(d.vrc_regime))}  dir {d.vrc_direction:+.1f}  volP {d.vrc_vol_percentile:.0f}\n"
        f"MBB {signal_name(d)}  squeeze {d.mbb_squeeze:.1f}  release {int(d.mbb_release)}\n"
        f"TB bias {int(d.tb_bias):+d}  swing {d.tb_swing_low:.5f}..{d.tb_swing_high:.5f}  "
        f"cellSide {int(d.tb_cell_side):+d} voidSide {int(d.tb_void_side):+d}\n"
        f"QQE primary {d.qqe_primary:+.2f}  secondary {d.qqe_secondary:+.2f}  state {int(d.qqe_state)}"
    )
    fig.text(0.995, 0.012, entry_state, ha="right", va="bottom", color=TEXT,
             fontsize=8, family="monospace",
             bbox={"facecolor": "#161b22", "edgecolor": GRID, "alpha": 0.95, "pad": 6})
    fig.text(0.006, 0.006,
             "Source: MT5 forensic replay F08F...5839 includes immutable EA E40F...959D0 | indicator values are not recomputed",
             color=MUTED, fontsize=7)
    fig.subplots_adjust(left=0.055, right=0.99, top=0.96, bottom=0.11)

    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{alias}.png" if mode == "asof" else f"{case.case_id}.png"
    path = out_dir / filename
    fig.savefig(path, dpi=145, facecolor=BG)
    plt.close(fig)
    return {
        "alias": alias,
        "case_id": str(case.case_id),
        "position_id": int(case.position_id),
        "mode": mode,
        "image": str(path),
        "sha256": sha256_file(path),
        "entry_time_utc": str(entry),
        "last_bar_time_utc": str(bars.time_utc.iloc[-1]),
        "outcome_hidden": mode == "asof",
        "cutoff_enforced": bool(mode != "asof" or bars.time_utc.max() < entry),
        "decision_snapshot_rows": int(len(decision)),
    }


def contact_sheet(items: list[dict], out_path: Path, title: str, columns: int = 2) -> dict:
    images = [Image.open(item["image"]).convert("RGB") for item in items]
    thumb_w = 1200
    thumb_h = 800
    rows = math.ceil(len(images) / columns)
    header = 70
    sheet = Image.new("RGB", (columns * thumb_w, header + rows * thumb_h), (13, 17, 23))
    draw = ImageDraw.Draw(sheet)
    draw.text((24, 20), title, fill=(230, 237, 243), font=ImageFont.load_default(size=24))
    for idx, image in enumerate(images):
        image.thumbnail((thumb_w, thumb_h))
        x = (idx % columns) * thumb_w + (thumb_w - image.width) // 2
        y = header + (idx // columns) * thumb_h + (thumb_h - image.height) // 2
        sheet.paste(image, (x, y))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, quality=94)
    for image in images:
        image.close()
    return {"path": str(out_path), "sha256": sha256_file(out_path), "count": len(items)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bars", required=True, type=Path)
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--replay", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    cases = pd.read_csv(args.cases)
    replay = pd.read_csv(args.replay)
    bars = pd.read_parquet(args.bars, columns=["time_utc", "open", "high", "low", "close"])
    bars["time_utc"] = pd.to_datetime(bars.time_utc, utc=True).dt.tz_localize(None)
    replay["decision_time_server"] = replay.decision_time_server.astype(str)
    replay["decision_time_utc"] = pd.to_datetime(replay.decision_time_utc)
    replay["source_bar_time_utc"] = pd.to_datetime(replay.source_bar_time_utc)
    as_num(replay, [
        "aird_regime", "aird_confidence", "p_bull", "p_bear", "p_range", "p_highvol",
        "vrc_regime", "vrc_direction", "vrc_vol_percentile", "mbb_upper", "mbb_lower",
        "mbb_basis", "mbb_squeeze", "mbb_release", "s1_long", "s1_short", "s2_long",
        "s2_short", "s3_long", "s3_short", "tb_bias", "tb_swing_high", "tb_swing_low",
        "tb_cell_top", "tb_cell_bottom", "tb_cell_side", "tb_void_top", "tb_void_bottom",
        "tb_void_side", "tb_structure_level", "tb_sweep_high", "tb_sweep_low",
        "tb_structure_up", "tb_structure_down", "qqe_primary", "qqe_secondary", "qqe_state",
    ])

    manifest = {
        "schema_version": SCHEMA,
        "bars": str(args.bars), "bars_sha256": sha256_file(args.bars),
        "cases": str(args.cases), "cases_sha256": sha256_file(args.cases),
        "replay": str(args.replay), "replay_sha256": sha256_file(args.replay),
        "asof": [], "anatomy": [], "contact_sheets": [],
    }
    asof_dir = args.output / "asof"
    anatomy_dir = args.output / "anatomy"
    for index, case in cases.iterrows():
        alias = f"A{index + 1:02d}"
        manifest["asof"].append(render_case(case, alias, bars, replay, asof_dir, "asof"))
        manifest["anatomy"].append(render_case(case, alias, bars, replay, anatomy_dir, "anatomy"))

    losers = [
        item for item, (_, case) in zip(manifest["anatomy"], cases.iterrows())
        if float(case.net_r) < 0
    ]
    manifest["contact_sheets"].append(contact_sheet(
        losers, args.output / "RSF_C16_LOSER_INDICATOR_CONTACT_SHEET.png",
        "RSF Cell 16 losing trades — frozen sample, all five indicator panels", columns=2,
    ))
    manifest["contact_sheets"].append(contact_sheet(
        manifest["asof"], args.output / "RSF_C16_ASOF_BLIND_CONTACT_SHEET.png",
        "RSF Cell 16 as-of charts — outcomes hidden", columns=2,
    ))
    manifest_path = args.output / "casebook_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"RSF_CASEBOOK_OK cases={len(cases)} images={len(cases)*2} manifest={manifest_path}")


if __name__ == "__main__":
    main()
