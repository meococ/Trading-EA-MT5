# PA-PRO zone parity — one-command runbook

Goal: prove the MQL5 engine sees what Python sees — **>= 99.5%** of
(t_epoch, gen) bars with identical armed-zone bounds at **0.1 pip**
tolerance.

## 1. Python side (heavy — takes a pa_slots slot internally)

```bash
cd "03. EA Developer/PA_Pro/mql5/parity"
python export_zones.py EURUSD out
# -> out/zones_EURUSD_py.csv
```

Data: `pa_data.load_m1(symbol, split="DESIGN", warmup_days=30)` →
resample M5/H1 → `ZoneContext` → `families/sf_ctx.run_pass` (exact
replay, SF01 D4 reference) → one row per ARMED view per bar.

## 2. MQL5 side (terminal or tester — Owner runs this; the lane cannot
launch a terminal)

Compile once:

```powershell
cd "02. AlphaFactory"; .\alpha.ps1 compile "PA_Pro_Parity"
```

Then EITHER:

- **Script run**: attach `PA_Pro_Parity` to an EURUSD M5 chart → it
  writes `zones_EURUSD.csv` and prints `PA-PARITY: ... export rows=N`.
- **EA run**: attach `PA_Pro` to EURUSD M5 with `InpExportZones=true`
  (optional `InpExportFrom/To` to bound the window).  Export covers the
  loaded history at attach time.

Output file: `MQL5\Files\PA_Pro\zones_EURUSD.csv` (or
`Common\Files\PA_Pro\zones_EURUSD.csv` when FILE_COMMON wins — the
exporter tries FILE_COMMON first, then terminal-local).

## 3. Compare

```bash
cd "03. EA Developer/PA_Pro/mql5/parity"
python compare_parity.py out/zones_EURUSD_py.csv \
    "<MT5 files dir>/PA_Pro/zones_EURUSD.csv" 0.00001 \
    --report out/diff_EURUSD.txt
```

Join key is `(t_epoch, gen)` — server epoch, so the two sides need not
share bar indexing or warmup length.

**Window coverage matters.** The verdict counts every `(epoch, gen)`
key present in only one file as a miss — so the MQL5 export must cover
the same epochs as the Python file.  The current Python export spans
**444,916 epochs, 2015-12-02 → 2021-12-31** (~6.1 years incl. warmup).

Two cases:

- **MQL5 history covers the full span** (`InpMaxBars` >= ~445k and the
  broker's M5 history reaches 2015): run the comparator with no bounds.
  Both sides share the same cold start, so warmup epochs are identical.
- **MQL5 history is shallower**: bound the comparison with `--e0/--e1`
  on BOTH files.  Zone state accumulates from each side's own history
  start, and Python zones born before the MQL5 window can still be
  alive — the margin must exceed the longest zone lifetime (~30 days):

```
python compare_parity.py out/zones_EURUSD_py.csv zones_EURUSD.csv \
    --e0 <mq_first_epoch + 2592000> --e1 <mq_last_epoch>
```

The comparator also prints an `overlap %` (identical among shared
keys only) as a diagnostic — but the PASS/FAIL verdict stays strict.

## Column contract (both sides, PA_Export.mqh / export_zones.py)

```
t_idx,t_epoch,gen,zid,kind,scale,lo,hi,strength,touches,fresh,
broken_idx,role_flip,approach_side,born_idx,end_idx
```

`armed` = `arm_zones` output only (broken zones excluded, near<=2*ATR,
center-dedupe 0.25*ATR, cap 6, strongest first) — identical filter on
both sides.
