# NOTEBOOK.md — PA-ATLAS NotebookLM state

## Notebook

- Name: **Price Action**
- id: `de998a77-59d0-4a00-bab0-b3b53d4632e4`
- URL: https://notebooklm.google.com/notebook/de998a77-59d0-4a00-bab0-b3b53d4632e4
- Alias: `pa`
- Created: 2026-09-23 ~06:40Z by lane PA-ATLAS (fresh, no pre-existing notebook of that name).
- Sharing: private (never shared publicly — R74 wall).

## Account / auth

- `nlm login --check` at 06:38Z: ✓ Authentication valid (profile `default`, toilatruc999@gmail.com, 18 notebooks).
- Owner logged in himself at ~06:34Z (R74 §74.3). This lane never touches credentials.
- Re-check cadence: every ~30 min or before each query batch.

## Plan limits (nlm usage, 06:39Z)

- Plan tier: `NOTEBOOKLM_TIER_PRO_CONSUMER_USER`.
- Rolling window (~5h): 0.0% used, resets 2026-09-23 14:15 local (SE Asia).
- Weekly limit: 0.0% used, resets 2026-09-27 17:15 local.
- Absolute per-day query counts are not reported; lane cap applied anyway:
  **at most 40 NotebookLM queries today, ≥10 left for the Owner** (R74 §74.4).
- Query counter (this lane): 0 used so far.

## Source budget

- NotebookLM consumer limit ≈ 50 sources/notebook (typical); verify on approach.
- Add order: Tier 1 → best Tier 2 → Tier 3 (indicator/code material may go to a
  second notebook "Price Action - Indicators & Code" if the cap is hit).

## Sources added (NLM source_id ↔ SOURCES.csv row)

| csv | nlm source_id | note |
|---|---|---|
| S01 | 65c415d9-576b-43cd-b52b-40ee996f829a | Grimes Trendlines 101 |
| S02 | cb3c4375-b981-4665-94ab-336e6f1f87e0 | Grimes DJIA trendlines |
| S03 | 23843c89-1ae4-4d0b-af26-dc91b7c71f22 | Grimes most important things |
| S05 | 216c23c3-73b8-400d-b882-068b2e2cd0e2 | Brandt gold trendline |
| S06 | 3868e6a1-5f6b-4417-abce-dd9ec8f1e3c2 | Brandt MTA 1989 PDF |
| S07 | cc06b1a5-a69d-4342-98b5-784155be5fa8 | Brandt YT classical charting |
| S10 | 7360ee4d-d55e-46fd-b016-d7697df264b1 | Bulkowski Adam&Eve DB |
| S12 | 8224f447-8582-47a6-8c21-4d26240a3892 | Fraser reaccumulation ranges |
| S14 | fa505d90-e36d-45d2-a1e2-75b589a4ebf0 | Fraser YT distribution watch |
| S17 | 283dd470-a3d1-4134-8024-282191338c10 | Aspenres TD Lines doc |
| S18 | 84388829-d0c8-4c43-ae19-f566d8ab5053 | Osler 2000 NY Fed PDF |
| S20 | 1a586e7f-5e85-4125-b4ef-5de2025704b7 | Lo-Mamaysky-Wang 2000 PDF |
| S24 | e544c5e4-50d7-4d63-9cfc-088bb52f840e | Brooks YT ch2 trendlines |
| S28 | 84749529-84c8-4c7a-9909-4ee7b1b756cb | Brooks YT no indicators |
| S29 | f6bf50f2-19dd-4c4b-80fb-4b67fab82184 | Brooks YT spike & channel |
| S30 | 72704e69-044f-496c-ba36-6a645113b541 | Raschke Holy Grail explainer |
| S31 | b57d5fff-ffe1-4bf2-8a5c-1f54b0b0774f | Raschke interview pt2 |
| S35 | 19b055cc-66b7-436a-9154-cc98d0df44be | Trade2Win Volman thread |
| S36 | e95edc36-36c1-4bb1-a44f-51877eeced95 | YTC S/R greatest tool |
| S37 | 99abc436-6964-4641-ab4d-44922b73c44a | YTC how S/R created |
| S38 | a3b7add9-bfc6-4385-b9ab-0cbf844786f3 | YTC layered levels |
| S39 | 69dd79e7-ecc3-46ce-af5e-5dabe2984be0 | YTC stretch to level |
| S40 | 15bb7a83-fc71-43c6-858d-0c4a8abdbcec | YTC structure in structure |
| S42 | 35993b7d-f788-421a-acbc-f540d2373fd5 | Rayner draw S/R |
| S43 | a45cd69d-f030-439c-aee6-a757201e57ac | Rayner PA guide |
| S44 | 8acdb9ad-dfb6-4a56-be4b-77fd47937833 | AntiVestor S/R guide |
| S45 | 2ae36cf5-eb4d-466c-a9b9-1e3f6fa8f04a | PropTradingVibes S/R |
| S46 | 7e0b3a3d-9d73-47f4-a72d-65b1fee853e9 | ChartMini zones |
| S47 | 91c7353f-c3b7-43d5-b3d0-51f4d144a896 | EliteTrader Trader Vic TL |
| S53 | 3726d651-2b1f-4a31-9ab6-64457c7ce70f | LuxAlgo market-structure docs |
| S54 | 597c72cf-57a2-4f17-b407-d0b51b77d11c | LuxAlgo SMC page |
| S55 | 5c67f357-ef0b-46ae-b18a-eb61b26e2f88 | StoicFX Wyckoff accumulation |
| S57 | b0799ea5-221a-454a-9f96-083966104b14 | Investopedia Wyckoff |
| S59 | 9d618c07-1f7d-4f96-838f-5973aa136077 | AmiBroker trendlines guide |
| S60 | 7853e888-0e2f-4530-966f-5d02d1315e60 | forexmt4systems candles@S/R |
| S04 | 227ef3bf-ff2c-4273-a1d2-4b8f2cee0f32 | Grimes quant-101 |
| S22 | f46f6efd-575e-4c4d-b947-72b613b7e891 | arXiv 2101.07410 S/R |
| S62 | e3faf7df-0a72-4099-91b2-29352bcae11d | GitHub backtesting.py #395 |

Total in notebook: **39 sources** (limit ~50, headroom kept).

### Ingest failures (kept in SOURCES.csv, added_to_notebook=fail)

- S25, S26, S27 brookstradingcourse.com ×3 — crawler blocked/paywall.
- S32, S33, S34 forexfactory.com ×3 — Cloudflare block (both webfetch and NLM).
- S23 Kavajecz&Odders-White PDF — NLM could not fetch (HTTP source).
- S49 babypips.com — NLM could not fetch.
- Reddit (S61): old.reddit + reddit.com both 403 to webfetch — not added.
- X/Twitter: no public fetch path without account — documented limitation only.

## Studio artifacts (ids recorded here when created)

- Briefing report: `b038d36c-6a12-43fe-bfff-d80044417351` (Briefing Doc, started 07:2xZ)
- Mind map: FAILED — `nlm mindmap create` returns API INVALID_ARGUMENT ×2 (07:2xZ); retry logged, may be unsupported for this account/plan
- Data table "rule x expert": `d762a6c6-3307-4904-a841-3ff558b7462d` (started 07:2xZ)
- Audio overview (Vietnamese, brief/short): `a11aa334-a016-403a-bb14-fa972095de7a` (started 07:2xZ)

## Chat sessions (conversation ids, one per object type)

- range/box: `1107f965-8ab1-4a95-984e-752d2116c2a9` (6 queries: Q1Q8, Q2Q3, Q4Q5, Q6, Q7, Q9Q10)
- sloped line: `b0537405-92f4-42a7-95fa-e2991a441760` (5 queries: Q1Q8, Q2Q3, Q4Q5, Q6Q9Q10, Q7auto)
- horizontal level/zone: `575b681d-b23b-4e75-bdc7-33bf21dddc90` (5 queries: Q1Q8, Q2Q3, Q4Q5, Q6Q9Q10, Q7auto)
- pattern marks: `4e6ea719-6908-4f28-80a4-e7a34d5d76fe` (4 queries: Q1Q7, Q4Q5, Q6Q9, Q10auto)
- Queries used this lane: 20/40 cap. Raw answers with citations: `nlm_raw/*.json` (+ readable `.md` mirrors).

## Baselines (Step 4, optional — time permitted)

Implemented under `baselines/`, all causal, emit per-panel objects:
- `b_darvas.py` — Darvas 4-state range machine (BOX), N=7, height>=0.4*ABR, close-break death.
- `b_tdlines.py` — DeMark TD Lines k=2 (PATTERN_LINE), pair-revision = old dies + new ink, qualified-break death.
- `b_donchian.py` — Donchian-alternating swing levels (LEVEL_CARRIED), d=1.0*ABR reversal confirm, keep=3/side.
- `bl_common.py` — object contract, tau-slice, match wrappers around evalcheck/eval_v2.py (imported, not copied).
- `run_all.py` — TUNE scoring runner (via heavy_run.py, lane pa-atlas).

### Baseline TUNE scores (198 panels, via heavy_run lane pa-atlas, 07:43Z)

- `bl_darvas_n7`: box@1 2/119, clutter 0.67 — containment-state boxes barely match touch-based golden ink.
- `bl_tdlines_k2`: line@2 29/193 (engine v0: 20/193), clutter 6.67 — objective anchors alone beat v0 reach.
- `bl_donchian_alt`: level@1 16/76 (engine v0: 7/76), clutter 10.33 — reversal-confirmed extremes reach 2.3x v0.
- Single-family emitters: other-family zeros are structural. Rows: `result_row.py show --lane pa-atlas`.
