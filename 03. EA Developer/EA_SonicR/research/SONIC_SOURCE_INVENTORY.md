# Sonic R Source Inventory

## Local source status
- Original Sonic R / PVSRA indicator source was not found under this workspace or `MQL5/Indicators`.
- Current executable truth is therefore a reconstructed parity spec, not a byte-for-byte clone of the original indicator pack.
- Any future `.mq4`, `.mq5`, `.tpl`, PDF, or screenshot pack must be added here before changing EA parity logic.
- 2026-05-09 recovery changed this status: canonical public ForexFactory `.mq4/.tpl` source was retrieved into quarantine only. It is source evidence, not installed runtime code.

## Quarantine recovery 2026-05-09

- Canonical quarantine path: `03. EA Developer/EA_SonicR/source_quarantine/forexfactory/20260509_232500/`
- Retrieval manifest: `retrieval_manifest.json`
- Retrieval readout: `retrieval_readout.md`
- Script: `03. EA Developer/EA_SonicR/research/sonic_source_parity_retrieval.py`
- Handling: static quarantine only; no MT4/MT5 install, load, compile, or execution of external code.
- Result: `14/14` targets retrieved. Two 2014 zip files were hashed and only `.mq4/.tpl` static files were extracted.
- Primary zip hashes:
  - `TAH_03-17-2014_Revised.zip`: `DB2F0FD60BE6647E22FCA1F80425F6795F7895DC90ABA61893B5AFD19ADDDEC5`
  - `2014_SonicR_Indys_Tmpls.zip`: `A52CE2608BEE79E6E05F886702BFDEBD1B46A67603243B001867E1382494302D`

## Source-authenticated deltas

| Priority | Delta | Source evidence | EA status |
| ---: | --- | --- | --- |
| 1 | PVA candle-volume event parity | `Sonic_2 PVA Candles` / `Sonic_6 PVA Volumes` User Notes and code: previous-10-bar average, `150%` rising, `200%` or highest `spread * volume` climax. | Implemented default-off as `InpUseSourcePvaParityV1=false` with `source_pva_*` telemetry. |
| 2 | S/R whole-half-quarter interaction | `Sonic_4 Access Panel` source defines 00/25/50/75 level grid; mirror doctrine corroborates whole/half/quarter S/R priority. Trade Levels is EP/TP/SL drawing utility, not S/R logic. | Implemented as telemetry-only `InpUseSourceSrInteractionV1=false` with `source_sr_*`; first probe parked any decision/qualifier patch. |
| 3 | Classic wave/Dragon trigger | FF post #1, post 8127640, and Dragon source confirm PA wave plus Dragon/Trend context. | Implemented as telemetry-only `source_classic_*`; first probe parked any decision/qualifier patch. |
| 4 | Trader-state story reader | FF post #1, post 8127640, and PVSRA run/build doctrine support reading Classic wave/Dragon/PVSRA/S&R as a pre-entry story instead of a standalone trigger. | Implemented as telemetry-only `sonic_*` labels and 20/60-bar replay metrics; smoke passed, decision patch not authorized. |
| 5 | Session/timezone assumptions | Access Panel source contains market-session and pivot/timezone logic. | Documented only; no new EA behavior patch yet. |

## Primary sources
| Source | Use | Confidence |
| --- | --- | --- |
| Forex Factory Sonic R. System thread, post #1: https://www.forexfactory.com/thread/114792-sonic-r-system | Canonical thread and rule anchor. | High |
| Classic / PVSRA discussion: https://www.forexfactory.com/thread/post/8127640 | Confirms M15 Classic core, Dragon angle, PA wave, Trend 89 EMA, volume replacing older indicators. | High |
| PVSRA / Scout examples: https://www.forexfactory.com/thread/114792-sonic-r-system?page=2483 | Explains PVSRA as context and Scout as support, not standalone trigger. | Medium |
| Classic + PVSR supporting evidence: https://www.forexfactory.com/thread/post/7827888 | Shows Classic entries supported by price, volume, S/R analysis. | Medium |
| PVSRA whole/half number discussion: https://www.forexfactory.com/thread/114792-sonic-r-system?page=2634 | Supports whole/half/quarter level interpretation and MM build logic. | Medium |
| Sonic R System PDF mirror: https://s2e2ea4a9b3965dd1.jimcontent.com/download/version/1507606613/module/5756833280/name/Sonic%20R%20System%20by%20Fratelli.pdf | Secondary manual-style reference. | Medium |

## Indicator names to keep searching for
- SonicR Dragon Trend
- SonicR PVA / PVSRA candles
- SonicR Control Panel
- SonicR Clock / Sessions
- SonicR Levels / whole half quarter SR
- SonicR Volume Suite

## Current parity risk
- Dragon and Trend are now supported by quarantined public `.mq4` source; Classic Wave/Dragon V1 telemetry passed sidecar/header checks but did not validate a decision or qualifier layer.
- Trader-State Reader V1 adds `sonic_*` label infrastructure for locked casebooks, but it is not a source-parity decision layer.
- PVSRA candle colors were previously reconstructed from tick-volume percentile, candle spread/body, S/R location, and accumulation bias. `InpUseSourcePvaParityV1` now provides a default-off source-authenticated PVA event path.
- S/R WHQ interaction now has source-authenticated telemetry fields, but the first probe did not validate a decision or qualifier layer.
- Scout logic remains conservative because original Scout rules are partly discretionary.
- `EA_SonicR` remains research-only. Source parity is not deploy-readiness.
