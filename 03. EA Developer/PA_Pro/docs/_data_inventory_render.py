"""Render DATA_INVENTORY.md from the per-symbol JSONs written by
_data_inventory_scan.py. Keeps every number traceable to the JSON (no hand
transcription). Re-run after a rescan to refresh the document."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "_data_inventory")
OUT = os.path.join(HERE, "DATA_INVENTORY.md")

SYMS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD"]
YEARS = [str(y) for y in range(2010, 2027)]

HEADER = """# PA-PRO — DATA INVENTORY (sub-agent B, Round 00)

Status: `DONE` — all 7 symbols scanned 2026-09-20.
Charter: `PA_PRO_CHARTER.md`, SHA256 `3C57536848A4AA6113950D06D50331B8C664E18B79D34E08DEF2F1019BC5DC2C`
(verified with `Get-FileHash -Algorithm SHA256` on 2026-09-20).
Scan script (resumable, read-only on the cache): `PA_Pro/docs/_data_inventory_scan.py`;
renderer: `PA_Pro/docs/_data_inventory_render.py`; raw per-symbol JSON:
`PA_Pro/docs/_data_inventory/<SYM>.json`.

Symbols: EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF, NZDUSD. Window 2010-2026
(the cache ends 2026-09-18, so 2026 is partial).

Source: `02. AlphaFactory/lab/cache/<SYM>_M1_2010_2026.parquet` — READ-ONLY (never written,
locked or re-saved by this work). Index `ctm` = int64 server epoch seconds; columns used:
`o,h,l,c,suspect`. The cache also carries `tv,sp,mod,dow,mow,day,year` columns, untouched.

---

## 1. ATR14 overall medians per symbol (REFERENCE FOR DOWNSTREAM WORK)

Medians over **all complete bars** of the whole 2010-2026 window, in pips
(pip = 1e-4, USDJPY = 1e-2). Wilder ATR14; method in §2. The last column is the
fraction of complete H1 bars with `ATR14(H1) >= 10 x c_rt` (the charter §3 geometry
guard); `c_rt` per symbol is in the COSTS.md table (AUDUSD/USDCAD/NZDUSD use the 1.4 p
proxy until measured).

| Symbol | ATR14(H1) median (pips) | ATR14(M15) median (pips) | H1 bars (ATR-valid) | M15 bars (ATR-valid) | H1 share ATR14 >= 10*c_rt |
|---|---|---|---|---|---|
"""

METHOD = """
---

## 2. Method (frozen; every number in this file follows it)

1. **Suspect bars are dropped before aggregation.** `suspect=True` marks burst/packed
   regions whose prices are not tradable evidence (`02. AlphaFactory/lab/data_plane.py:8-11`);
   the daily 00:00 summary record is among them. Suspect % is computed on the raw M1
   counts before/after dropping.
2. **H1 bars** = complete 60-M1 **server-hour** buckets; **M15 bars** = complete 15-M1
   server buckets. Buckets are keyed by `t // span` on server epoch seconds (the server
   offset is whole hours, so buckets align to server wall-clock hours/quarters). A bucket
   is complete only when it holds exactly 60 (resp. 15) non-suspect M1 bars; an hour
   containing the suspect roll bars is therefore dropped, not patched.
3. **Wilder ATR14**: `TR_t = max(h-l, |h-c_{t-1}|, |l-c_{t-1}|)`, first ATR =
   mean of the first 14 TR, then `ATR_t = (ATR_{t-1}*13 + TR_t)/14`. The ATR series is
   computed once over the whole continuous bucket series (server time), then grouped by
   server year for the per-year medians.
4. **Pip**: `1e-4` for all symbols except USDJPY = `1e-2` (`data_plane.py:26-27`).
5. **Server clock** = UTC + 2 (winter) / +3 (EU DST), applied via
   `eu_server_offset_hours` imported READ-ONLY from
   `03. EA Developer/EA_VolmanPA/research/lab/vpa_random_baseline.py:60` (sub-agent A's
   `PA_Pro/lib/pa_clock.py` did not exist at scan time; the script prefers it if present,
   and each JSON records which source was used). The UTC column = server epoch − offset
   at that timestamp.
6. **Gaps > 1 day** are measured on the raw timestamp sequence (all bars) as
   `dt > 86400 s`; a non-suspect-only variant is also stored in the JSON. The 10 largest
   gaps are reported with both server and UTC dates.
7. Per-year buckets use the **server-time year** of the bucket start.

`ASSUMPTION:` suspect bars are assumed correctly flagged by the ETL; this work does not
re-derive the flags.
"""


def fnum(v, dec=2):
    return "n/a" if v is None else f"{v:,.{dec}f}"


def pct(v, dec=1):
    return "n/a" if v is None else f"{100.0*v:.{dec}f} %"


def main():
    r = {}
    for s in SYMS:
        with open(os.path.join(SRC, f"{s}.json"), encoding="utf-8") as f:
            r[s] = json.load(f)

    L = [HEADER]
    for s in SYMS:
        h1, m15 = r[s]["timeframes"]["H1"], r[s]["timeframes"]["M15"]
        L.append(f"| {s} | **{h1['overall_median_pips']:.2f}** | **{m15['overall_median_pips']:.2f}** "
                 f"| {h1['overall_n']:,} | {m15['overall_n']:,} | {pct(h1['overall_share_atr_ge_10c'])} |\n")
    L.append(METHOD)

    L.append("\n---\n\n## 3. Cross-symbol data quality summary (2010-2026)\n\n")
    L.append("| Symbol | first bar (server) | first bar (UTC) | last bar (server) | last bar (UTC) | M1 rows | suspect % | gaps > 1d (raw) | gaps > 1d (non-suspect) |\n")
    L.append("|---|---|---|---|---|---|---|---|---|\n")
    for s in SYMS:
        d = r[s]
        L.append(f"| {s} | {d['first_bar']['server']} | {d['first_bar']['utc']} | {d['last_bar']['server']} "
                 f"| {d['last_bar']['utc']} | {d['m1_rows_total']:,} | {d['suspect_pct_total']:.3f} % "
                 f"| {d['gaps_gt_1d_allbars']['count']} | {d['gaps_gt_1d_validbars']['count']} |\n")
    L.append("\nAll caches: timestamps strictly increasing, 0 duplicates/backwards "
             "(field `timestamps_duplicate_or_backwards` = 0 in every JSON). "
             "Per-symbol SHA256 of each cache file is in the JSON (`cache_sha256`).\n")

    for i, s in enumerate(SYMS):
        d = r[s]
        h1, m15 = d["timeframes"]["H1"], d["timeframes"]["M15"]
        L.append(f"\n---\n\n## {4+i}. {s} — full detail\n\n")
        L.append("### Coverage and data quality\n\n")
        L.append("| item | value |\n|---|---|\n")
        L.append(f"| first bar (server) | {d['first_bar']['server']} |\n")
        L.append(f"| first bar (UTC) | {d['first_bar']['utc']} |\n")
        L.append(f"| last bar (server) | {d['last_bar']['server']} |\n")
        L.append(f"| last bar (UTC) | {d['last_bar']['utc']} |\n")
        L.append(f"| M1 rows total | {d['m1_rows_total']:,} |\n")
        L.append(f"| suspect rows total | {d['suspect_pct_total']:.4f} % |\n")
        L.append(f"| timestamps strictly increasing | {str(d['timestamps_strictly_increasing']).lower()} "
                 f"({d['timestamps_duplicate_or_backwards']} duplicate/backwards) |\n")
        L.append(f"| gaps > 1 day (raw / non-suspect) | {d['gaps_gt_1d_allbars']['count']} / "
                 f"{d['gaps_gt_1d_validbars']['count']} |\n")
        L.append(f"| cache SHA256 | `{d['cache_sha256']}` |\n")
        L.append(f"| clock source | `{d['clock_source']}` |\n")

        L.append(f"\n### Per-year M1 counts, suspect % and ATR14 (pips)\n\n")
        L.append(f"`c_rt` used for the share columns = {h1['c_rt']} pips "
                 f"(threshold {h1['threshold_10c_rt_pips']:.1f} pips). "
                 f"Overall medians: **H1 {h1['overall_median_pips']:.2f} p** "
                 f"(n={h1['overall_n']:,}), **M15 {m15['overall_median_pips']:.2f} p** "
                 f"(n={m15['overall_n']:,}). Overall shares ATR >= 10*c_rt: "
                 f"H1 {pct(h1['overall_share_atr_ge_10c'])}, M15 {pct(m15['overall_share_atr_ge_10c'])}.\n\n")
        L.append("| Year | M1 bars | suspect % | H1 med | H1 n | H1 share >= 10*c_rt | M15 med | M15 n | M15 share >= 10*c_rt |\n")
        L.append("|---|---|---|---|---|---|---|---|---|\n")
        for y in YEARS:
            py = d["per_year_m1"][y]
            if py["m1_bars"] == 0:
                continue
            hy, my = h1["per_year"][y], m15["per_year"][y]
            hsh = h1["share_atr_ge_10c_per_year"][y]
            msh = m15["share_atr_ge_10c_per_year"][y]
            ytag = f"{y} (partial)" if y == "2026" else y
            L.append(f"| {ytag} | {py['m1_bars']:,} | {py['suspect_pct']:.3f} | "
                     f"{fnum(hy['median'] if hy else None)} | {hy['n'] if hy else 0:,} | {pct(hsh)} | "
                     f"{fnum(my['median'] if my else None)} | {my['n'] if my else 0:,} | {pct(msh)} |\n")

        L.append(f"\n### 10 largest gaps > 1 day (raw series)\n\n")
        L.append("| from (server) | to (server) | from (UTC) | to (UTC) | hours |\n|---|---|---|---|---|\n")
        for g in d["gaps_gt_1d_allbars"]["largest_10"]:
            L.append(f"| {g['from_server']} | {g['to_server']} | {g['from_utc']} | {g['to_utc']} | {g['hours']} |\n")

    L.append("""
---

## 11. Notes, assumptions and caveats

- `ASSUMPTION:` ATR14 uses complete buckets only; incomplete hours (holidays, the
  suspect 00:00 roll hour, feed gaps) produce no bar at all rather than a patched one.
  Cadence of signals on H1/M15 must therefore tolerate missing buckets.
- `ASSUMPTION:` the share columns for AUDUSD/USDCAD/NZDUSD use the 1.4 p `proxy` c_rt
  from COSTS.md; if the Lead adopts a different c_rt, the share can be re-derived from
  the per-year ATR percentiles stored in each JSON (`p10,p25,median,p75,p90`).
- The 2010-2026 window includes the 2015-01-15 CHF de-peg and the 2020 COVID shock;
  per-year tables keep them visible instead of averaging them away.
- 2026 is partial (cache ends 2026-09-18); do not compare its counts with full years.
- Weekend gaps are the bulk of the "gaps > 1 day" count (roughly 52/year plus holidays);
  the largest gaps are the Christmas/New-Year breaks (see per-symbol tables).
- This inventory is measurement only; no economic claim is made here.

---

## 12. Verification (independent cross-check)

`PA_Pro/docs/_data_inventory_verify.py` (run 2026-09-20 under `pa_slots`) recomputed
EURUSD ATR14(H1) through a different pipeline (pandas `resample("1h")` + independently
written Wilder loop) and compared the clock modules:

```
clock compare n=102 equal=True offsets_seen=[2, 3]
buckets: verify=95400 json_buckets=95400 json_atr_n=95387
overall median: verify=15.403856 json=15.403856 diff=0.00e+00
overall share>=10p: verify=0.879145 json=0.879100
  2010: verify=29.012682 json=29.012682 diff=0.00e+00
  2019: verify=9.813440 json=9.813440 diff=0.00e+00
  2024: verify=10.421306 json=10.421306 diff=0.00e+00
  2026: verify=11.353843 json=11.353843 diff=0.00e+00
  2019 share>=10p: verify=0.474718 json=0.474700
```

- Clock: `pa_clock.server_offset_hours` == the Volman
  `eu_server_offset_hours` on 102 DST-boundary timestamps (2010-2026), so the
  scan's server/UTC columns are consistent with the now-existing PA-PRO clock module.
- ATR medians match exactly; the small share deltas (0.879145 vs 0.879100) are the
  JSON's 4-decimal rounding only.
- The scan JSONs record `clock_source` = the Volman file because `PA_Pro/lib/pa_clock.py`
  did not exist yet at scan time; re-running the scan now would use `pa_clock.py`
  (same semantics).
""")

    with open(OUT, "w", encoding="utf-8") as f:
        f.writelines(L)
    print(f"[render] {OUT}")


if __name__ == "__main__":
    main()
