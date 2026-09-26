# SF01 FACTORY LOG — append-only

## SUMMARY

| family | stage | census (sig/wk basket) | screen x1 headline | verdict |
|---|---|---|---|---|
| F1 ZONE REJECTION | done | 40.5/wk (12,720 sig) | best PF 0.983; all 20 PF<1, t<0; no lift | **DEAD** |
| F2 BREAK-AND-RETEST | done | 6.2/wk (1,950 sig) | best PF 1.103 but N=139, t=0.50, lift CI [-7.6,9.2] | **DEAD** |
| F3 FAILED BREAKOUT / TRAP | done | ~90/wk (~28k sig) | best PF 1.259 N=170 t=1.4 lift CI<=0; S32 N=3050 PF 1.025 | **DEAD** |
| F4 TREND PULLBACK TO ZONE | done | ~125/wk (~39k sig) | ALL 20 cells PF<1.0 (0.73-0.93), t all <0 | **DEAD** |
| F5 SECOND ENTRY | done | ~2.6/wk best cell | best PF 1.33 (S24/h4) N=255 t=1.99, lift CI<=0 | **DEAD** |
| F6 VOLMAN BOX BREAK | done | ~4.7/wk best cell | sd_base cells lift>0 but N<=81; thick cells flat | **DEAD** |

FACTORY COMPLETE — all 6 families screened on DESIGN via referee only;
0 survivors. F5 best cell N=255 just under the N gate with t=1.99 and
lift CI including 0. F6 sd_base box breaks show the round's only
positive-lift CI (+14.6pp [+3.1,+26.1]) at N=77 — real signal direction
but unscreenable sample; recorded as a hint for a future lane.
All ROUND_REPORT.md files written under rounds/SF01/<family>/.
Open issue: none.

## LOG

- 2026-09-21T02:15Z | RECON complete: `rounds/SF01/RECON.md`. Referee contract
  verified (fixed S_pips/tp_mult per spec; entries via entries_fn; matched
  random K=20 in-session cells; intraday-only exits). Six generators
  inspected; chose line1_cluster + sd_base for zone families. Infra build
  started under `families/`.

- 2026-09-21T03:14Z | F1: warm-up crash root-caused to random baseline
  (pa_data.frame lacks utc_start -> live_cut=0 -> warmup picks reach pa_fill).
  Fixed via families/sf_provider.py wrapper (D7). Smoke cfg7 OK: N=1837,
  PF_x1=0.895. SPEC v2 wording amended per Lead Review 2 (approach-side gate
  admits 2-bar rejections; formula unchanged). Full 20-config screen launched.

- 2026-09-21T03:40Z | F1 screen complete: 20/20 configs PF_x1<1.0 (0.794-0.983), t<=-0.20,
  lift CI never >0, years 0-3/6, symbols 0-3/4 -> DEAD, no revision
  justified (uniform failure, nothing to rescue). ROUND_REPORT written.
- 2026-09-21T03:40Z | F2: v1 census 5.3/wk too thin -> pre-outcome revision to v2
  (anchor=break bar, spans break->reclaim|flip; D8, T000089). v2 census
  6.2/wk; 12 snapshots rendered; tests pass; screen launched.

- 2026-09-21T04:30Z | Tag-contract bug found (D9): detectors used tag=zid but
  pa_eval expects tag = index into per-symbol entries list -> matched-random
  subsets were empty/garbage. Patched F1-F4 (tag=i, zid kept separately),
  sf_snap reads zid. Signal populations unchanged; spec hashes stand.
  F2/F3 screens rerun with correct tags.

- 2026-09-21T04:55Z | F2 rerun DEAD: best PF 1.103 (S24/line1) at N=139,
  t=0.50, lift CI [-7.6,9.2]; all cells fail N>=300 or PF. Report written.

- 2026-09-21T05:10Z | F3 rerun DEAD: 90/wk population but no edge —
  S11/sd_base PF 1.25 N=170 t~1.4 lift CI<=0; thick cells S32/line1
  N=3050 PF 1.025 lift ~0; no plateau. Report written.

- 2026-09-21T05:15Z | F4: census ~125/wk (~39k sig), 12 snapshots rendered
  and visually verified; full 20-config screen launched (corrected tags).
  F5 spec+detector+tests complete, prereg T000143 (sha 1e85a227).
  F6 spec+detector+tests complete, prereg T000159 (sha 4aa823b7).

- 2026-09-21T05:50Z | F4 screen DEAD: 20/20 cells PF_x1<1.0 (0.73-0.93),
  all t<0, N up to 7,200 — precise and negative. Report written.

- 2026-09-21T05:55Z | F5 v1 census 0.19-1.85/wk (s_struct floor killed
  84%) -> pre-outcome v2 (D10): inv = deepest point of two-legged
  pullback; prereg T000181 (sha b923336e); v2 census up to 2.6/wk
  (S14/h1 824 sig). Tests re-pass. 12 snapshots rendered+verified.

- 2026-09-21T06:05Z | F6 v1 census 0 signals — box_atr mis-scaled
  (per-bar width vs 12-bar window height) -> v2 box_atr {2.5,4.0} (D11);
  prereg T000185 (sha 44aafe84). v2 census up to 4.7/wk. 12 snapshots
  rendered+verified (textbook box-press-break geometry).

- 2026-09-21T06:40Z | F5 screen DEAD: best S24/tol1.0/h4 PF 1.33 t=1.99
  N=255 (fails N,t,lift). F6 screen DEAD: sd_base positive-lift cells
  N<=81; line1 thick cells PF 0.88-1.08. Reports written. Factory
  complete: 0/6 survivors.

- 2026-09-21T04:47Z | Q0 (SF02 hygiene): F1 screen re-run with the D9 tag
  fix (Lead Review 3 caught it was never re-run). New ledger trials
  T000226-T000246 (T000229 = SF02 autopsy prereg). Verified: all 20 cells
  produce IDENTICAL N/PF_x1/t_x1 vs the superseded pre-fix screen
  (backup SCREEN_v1tags_backup.json); lift fields now valid. Verdict
  unchanged: DEAD. See DECISIONS D9-bis.
