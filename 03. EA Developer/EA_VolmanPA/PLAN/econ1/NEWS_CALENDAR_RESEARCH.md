# NEWS_CALENDAR_RESEARCH — T-VPA-ECON-1 (SA-B, Lead decision G2)

Date 2026-09-20 · Scope: VPA lab DESIGN 2016-01-01 → 2021-12-31, EURUSD M5 · read-only repo audit

## 1. Search evidence (paths + quoted lines)

| Artifact | Path | State |
|---|---|---|
| FF EURUSD high-impact CSV, 2019-2022 | `02. AlphaFactory/data/forexfactory/EURUSD/news_events/forexfactory_high_impact_eurusd_2019_2022.csv` | **ABSENT** |
| FF weekly raw JSON (944,989 B) | same dir, `forexfactory_high_impact_eurusd_2019_2022.weekly.raw.json` | **ABSENT** |
| Manifest (metadata only) | same dir, `manifest.json` | present |
| Derived MQL5 datetime array | `00. Old File/EA_Archive/EA_VRAS_H1StructuralScalper/NewsCalendar2019_2022.mqh` (+ archive snapshot copies) | present |
| SonicR `SNR_FX_EVENTS.csv` (448 events) | FILE_COMMON per memory; no repo copy | **ABSENT** |
| Seed FOMC/BOJ CSV | `02. AlphaFactory/analysis/pre_announcement_drift_seed_events.csv` | present, 2021-2025 |
| MT5 built-in calendar query | `03. EA Developer/EA_SonicR_PVSRA/Include/SNR_News.mqh` | live terminal feed only |

- `manifest.json`: `"local_event_date_coverage": {"from": "2019-01-01","to": "2022-12-31"}`, `"timed_high_impact_events": 1282`, `"promotion_eligible": false`, `"This dataset cannot satisfy execution-cost provenance or promotion gates."`
- `.gitignore:26` = `02. AlphaFactory/data/**/*.csv`; `git log --all --name-status -- "*forexfactory_high_impact*"` and `"*weekly.raw*"` return **no commit** → CSV + raw JSON never tracked, **unrecoverable from git**.
- `NewsCalendar2019_2022.mqh:5-9`: `NEWS_CALENDAR_SOURCE_SHA256="78CB2656A27278B1DA04B2C594A2C73BB1877DBA3AB52BCCFAC36A215945EA8F"` (same sha as the raw JSON), `NEWS_CALENDAR_SOURCE_CLASS="C_DIAGNOSTIC_ONLY"`, coverage `1546300800`→`1672531199` (2019-01-01→2022-12-31 UTC), `#define NEWS_CALENDAR_COUNT 1282`.
- Local parse of the array: 1282 datetimes; per year 2019: 336, 2020: 356, 2021: 263, 2022: 327 → **955 events inside DESIGN (2019-2021); 2016-2018 has zero**.
- `04. Memory/research/20260813_SONIC_CALENDAR_RECOVERY_FRONTIER_AND_INPUT_ESCROW.md:12-16`: `FILE_COMMON/SNR_FX_EVENTS.csv`, `448 events`, coverage `2019.01.04` → `2026.12.25`, verdict `EXACT_RECOVERY_NOT_PROVEN`.
- `02. AlphaFactory/STRATEGY_LOG.md:2819`: `full historical news calendar still missing`.
- `03. EA Developer/EA_VolmanPA/research/HYP-VPA-EURUSD-M5-001_FROZEN_PREREG.md:72`: `DESIGN | 2016.01.01 → 2021.12.31`.
- `02. AlphaFactory/session_trader/examples/calendar.example.json`: `{"available": false, "asof_utc": null, "events": []}` — live-session contract stub, not a historical calendar.

## 2. Verdict

**NEWS: NOT AVAILABLE** for DESIGN 2016-2021. No repo artifact holds labeled EURUSD high-impact events across the full window: the normalized CSV + raw JSON are gone (gitignored, never tracked); the surviving derived array is unlabeled (all-high by construction, class `C_DIAGNOSTIC_ONLY`) and covers 2019-2022 only. That array is loadable from the VPA lab by a small regex parse of the `.mqh` (it lives outside AlphaFactory; no AlphaFactory code touched), but it cannot serve the full-window baseline and has no impact-level/currency columns. → use the fallback blackout below.

## 3. Fallback blackout (ready for code)

Fixed UTC minutes-of-day; `utc_min` = bar close minute (`research/lab/vpa_data.py:55`, `m5_t + 300`):

```python
BLACKOUT_UTC_MIN = ((745, 765), (805, 825))  # 12:25-12:45 UTC, 13:25-13:45 UTC
def in_fallback_blackout(utc_min):
    return any(a <= utc_min < b for a, b in BLACKOUT_UTC_MIN)
```

Apply uniformly to every DESIGN bar 2016-2021 (no event labels needed).

## 4. ASSUMPTIONS

- `NEWS: NOT AVAILABLE` = no real-event filter; the fixed windows replace it for the whole DESIGN window.
- Window mapping: `[745,765)` = 12:25-12:45 UTC = 14:25-14:45 CEST / 13:25-13:45 CET; `[805,825)` = 13:25-13:45 UTC = 14:25-14:45 CET. Together they bracket the 8:30 ET US release in both DST regimes (Volman book: peak 14:30 CET). The book's lighter 16:00 CET peak (15:00 UTC winter / 14:00 UTC summer) is **not** covered — Lead to confirm adding `(895,915)` / `(835,855)`.
- `utc_min` is the close minute, so the predicate excludes bars closing inside the window; also test `utc_min - 5` if overlap semantics are wanted.
- FOMC: **not derivable for 2016-2020** from any in-repo artifact. Only 2021 is derivable from `pre_announcement_drift_seed_events.csv` (8 dates, 18:00/19:00 UTC, outside both windows): 2021-01-27, 03-17, 04-28, 06-16, 07-28, 09-22, 11-03, 12-15. Not used (year-inconsistent) → baseline has no FOMC filter.
- Source rank C, `promotion_eligible: false`; even a restored CSV could not satisfy promotion gates.
