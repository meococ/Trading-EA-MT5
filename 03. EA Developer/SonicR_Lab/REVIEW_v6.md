# REVIEW_v6 — Round 2F neutral review (fresh reviewer, read-only)

Verdict: **PASS-WITH-NOTES**. Protocol discipline holds; K1-K3/V1-V3
applied as preregistered; NOT VALIDATED verdict correctly derived.
No gate was affected by any discrepancy below.

## 1. FREEZE ORDERING — PASS

- sha256(PREREG_V6.md) = `c3e9b29205863c20f06ca76c29988a58a3de4179cf18e4cb0b01551af9418f70`
  — recomputed, exact match.
- Freeze logged LAB_LOG.md:173 @ 22:35:03Z (file mtime 22:34:55).
- First C-symbol AM/PM P/L files: `confirm_2f_years_e1.csv` 22:38:20Z,
  `confirm_2f_pooled/persym.csv` 22:38:23Z — AFTER freeze.
- VALIDATION unlock 23:54:00Z — AFTER freeze.
- `labels_2f_H0/H1.csv` headers = raw trade fields + `lon_hour`,
  `am_pm`, `lon_year` only. No split-P/L columns.
- NOTE: labels files (mtime 22:34:13, pre-freeze) do contain C-symbol
  rows with per-trade `r_x1` + `am_pm` — i.e., the join needed for a
  split existed pre-freeze, but no AM/PM P/L was computed to file
  until 22:38:20Z and T3 printed D-only stats. Gate intent holds.

## 2. DST FIX — PASS

- `src/data.py:145-157`: `days == 0 -> days = 7` in `_last_sunday`,
  documented inline. This is the claimed fix.
- `python -m pytest tests/test_dst_fix.py -x -q` rerun: **6/6 pass**.
  Covers 2012-03, 2018-03, 2015-10, 2020-10; both US/UK gap
  directions (2015-03-11 and 2015-10-28 = server-3h; summer/winter
  = server-2h); Friday-flatten bug-week.
- `out/dstfix_diff_2f.csv` is a real before/after (n_old/n_new/gone/
  new_sig/r_chg/pf_old/pf_new per sym x harness). Max share changed
  = 13/1173 = **1.108%** (EURUSD H1); all other cells lower; |PF|
  moves <=0.005.
- Cosmetic: CSV columns (`new_sig`,`r_chg`) differ from current
  `regen_2f.py` keys (`new`,`r_changed`) — file written by an earlier
  rev; values consistent with log.

## 3. INDEPENDENT LABELS — PASS

- Recomputed `am_pm` from `dm.london_parts(sig_ctm)` (AM=[7,12),
  PM=[12,16)) on 20 random rows: **20/20 match**. Full-file agreement
  30075/30075 (H0+H1 concatenated). `lon_hour` range 7-15, values
  {AM,PM}, 0 OUT — consistent with london_ext(7,16) signal window.

## 4. FIXED PATH — PASS

- `validation_2f.py:114-124` `orders_once`: cache under
  `'F2_NH_b_dstfix'` per (sym,window); on miss calls
  `runner.orders_for` once. `free_2f.py:17` imports the same helper.
- `src/runner.py:66`: `ctx.reset_zones()` is the first line of
  `orders_for` — fix enforced at call site.
- `runs/regen_2f.py:41`: one `orders_for` per sym on a fresh ctx
  (grep-confirmed; no second call in the loop).
- `runs/verify_2f.py:83-107` T7: regenerates EURUSD+AUDJPY x H0/H1,
  merges on `(sig_ctm,dir)` (inner, len-checked), `r_x1` atol=1e-9,
  identity cols (`fill_ctm,exit_ctm,sl,tp,entry`) exact — as claimed.
  Not rerun here (heavy); code + prior PASS evidence consistent.
- Minor: `order_cache._path` keys on `window[0]` only; DESIGN
  (1262563200) vs VALIDATION (1578890844) differ, so no collision
  this round.

## 5. VALIDATION DISCIPLINE — PASS (one judgment note)

- Exactly ONE "VALIDATION UNLOCKED" entry (grep -c = 1):
  LAB_LOG.md:208 @ 23:54:00Z, written inside `validation_2f.py:181-184`
  (guard test at :173-177 precedes the append). K1-K3 logged
  23:48:19Z (LAB_LOG:178-194) before it.
- Earliest `out/trades_2fval_*` mtime = 23:54:12.68Z; earliest
  VALIDATION order-cache parquet = 23:54:12Z. Nothing before unlock.
- `_check_holdout` (data.py:80-84) raises `PermissionError` —
  verified in-process (`load_m1(..., HOLDOUT_START+60, COMMON_END)`);
  `tests/test_holdout_guard.py` covers all 12 syms + slice-end case.
- Earlier validation-window access: only T6 at ~23:49Z
  (`verify_2f.py:74` generates VALIDATION-window orders, result
  discarded to `_`, equality boolean only — no P/L, no file, no
  stats), disclosed at LAB_LOG:196-199 before unlock. JUDGMENT:
  allowed code/determinism test, not a protocol violation — the
  sealed asset is outcome evaluation on the unread window; the test
  extracted one bit (orders equal/not) used to prove the A2F fix.
  Also relevant: `runner.get_ctx` loads M1 through VALIDATION_END for
  every ctx by design, so window bars are resident regardless; the
  discipline boundary is signal/outcome evaluation, which held.

## 6. FREE-RUNNING IS AM-ONLY — PASS

- `free_2f.py:34-37` and `validation_2f.py:203-205,290-293`: signal-bar
  London hour via `dm.london_parts(ctx.tf["t"][o["t"]])`; keep
  `7 <= hh < 12` BEFORE `sm.run_trades` — PM orders never placed.
  (`o["t"]` = tf bar index; `sim.py:245` emits `sig_ctm = tf["t"][t]`
  — same time basis as `label_df`.)
- AMONLY trade files: 0 non-AM rows (H1 n=3724, H0 n=4099).
- `cap_filter` (:127-143): sorts by `fill_ctm`; `london_week(fill_ctm)`
  buckets (Monday-start: `(lon//86400 - 4)//7`, epoch day0=Thu so
  Mon = idx 4 mod 7 — verified); WEEK_CAP=5, MAX_OPEN=3 concurrent
  (`open_until` = kept exits > fill); first-come by fill order.

## 7. A2F FIX REAL — PASS

- `zones.py:115-120` `_advance` only moves `_ptr` forward;
  `_confirmed` grows monotonically — so after querying a later window
  the list retains swings with `conf > t`.
- `zones.py:129-130` candidate filter is `t - i <= max_age` only — no
  `conf <= t` and no `idx <= t` filter. Future-confirmed swings leak
  into a second/backward `zones_at`. Bug mechanism real.
- T6 (`verify_2f.py:62-81`) does what it claims: fresh-subprocess
  reference (separate `python -c`, `_t6_ref.pkl`, deleted after),
  then VALIDATION-window gen then DESIGN gen on the SAME ctx,
  field-wise compare (t/dir/entry/sl/tp/expiry_ctm) for F2_NH_b and
  F0_J. T7 as in check 4. Both reported PASS (LAB_LOG:196-202).

## 8. WEEK/YEAR FIX + 2C BEFORE/AFTER — PASS (notes)

- `london_week` (validation_2f.py:102-106): Monday-start London weeks
  — verified above. `london_year` (:109-111): true calendar year via
  `pd.to_datetime` on London epoch — leap-drift gone.
- `portfolio_2c_wkfix.csv` vs `portfolio_2c.csv`: F2_NH_b capped H1
  **1.106994 -> 1.016878** (claim 1.11 -> 1.017: exact). Other capped
  moves: F2_NH_b H0 1.1726 -> 1.0307; F0_J H0 0.859 -> 0.764;
  F5_S2 H1 1.070 -> 1.022. Uncapped PF_R rows identical (only
  cap/year-dependent stats moved). Capped n 2619 -> 2608 (H1) —
  different admissions expected under Monday-start weeks.
- NOTES: (a) `validation_2f.py:322` portfolio `pos_years` still uses
  `(exit_ctm//86400)//365` — the drifted year survived in a
  reporting-only column (not a gate; `portfolio_2f.csv` affected
  column only). (b) `label_2f.py:45` `lon_year` is also the drifted
  `(lon//86400)//365+1970`; K3 per-year count was 7/10 on it and
  8/10 on corrected years — both >= 6, gate unaffected.
  `validation_2f.py` `label_df:161` uses the fixed `london_year`.

## Cross-checks

- confirm numbers reproduce: K1 sep H1 +0.1151 (LB95 +0.0376), H0
  +0.0914; K2 5/5 C syms; pooled CSV matches log.
- validation numbers reproduce from `trades_2fval_*` files: fixed H0
  AM PF_R 0.874 / exp -0.110 (V1 FAIL); free H0 0.905 / -0.081
  (V1 FAIL); fixed H1 1.125/0.080/x15 1.078; free H1 1.160/0.101/
  1.111; V2 10/12; V3 sep +0.163 LB95 +0.085. NOT VALIDATED is the
  correct preregistered outcome (V1 needs H0 AND H1, both modes).
- Sanity: `r_x1 = pnl_px_x1 / risk_px` to 6.5e-13 on EURUSD dstfix.

## Discrepancies (none gate-affecting)

1. labels_2f files pre-freeze contain C rows + r_x1 + am_pm (raw +
   labels only; first computed C split P/L file 22:38:20Z).
2. `validation_2f.py:322` pos_years column still on `//365` years.
3. `labels_2f` `lon_year` drifted; K3 passed on both counts anyway.
4. `dstfix_diff_2f.csv` column names vs current `regen_2f.py` keys.
5. T6 ran order generation over VALIDATION bars pre-unlock — judged
   an allowed, disclosed determinism test (no outcomes read).
