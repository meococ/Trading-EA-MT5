# Do Not Repeat — Failed Strategies / Approaches

- Free public software vulnerability / security-advisory first-public
  design screen 2026-07-18 (`cron_20260718_1001`) sealed
  `NO_LEGAL_CANDIDATE — ZERO_KEEP_SOFTWARE_VULNERABILITY_SECURITY_ADVISORY`.
  Codex temporary refs **F1–F12 all REJECT** (design-only; **no probe**):
  NIST NVD CVE first-public (F1); MITRE/CVE Program assignment (F2);
  CISA KEV catalog addition (F3); GitHub GHSA (F4); CERT/CC Vulnerability
  Notes (F5); Microsoft MSRC / CVRF (F6); OSV.dev records (F7); Red Hat
  RHSA (F8); Ubuntu USN (F9); Debian DSA announce archive (F10); FIRST /
  national CSIRT coordinated advisory (F11); EPSS score first-public (F12).
  Dominant fails: **G5 firehose** (F1/F4/F6/F8), **G2 clocks** (F2/F5/F9),
  **G1 archive/era** (F3/F7/F11/F12), **G6** near-miss F10 Debian DSA vs
  sealed **#32** CISA ICS / coordinated advisory mechanism (also V10
  incident densify risk on KEV). Do **not** invent F13 densify of these
  objects; free Wave-H / O13 / I13 / N13 / S13 / L13 / X13 / Y13 / Z13 /
  T13 / U13 / V13 / W13 / A13 / B13 / C13 / D13 / E13 densify remain
  separately forbidden. Evidence:
  `.context/cron_20260718_1001/{TASK,PLAN,CANDIDATE_MEMO,REPORT,HERMES_VERIFY}`
  PLAN SHA `1a429efefd5987456571665b1b0f45e0ff0fdc7a81c4ec86365cecb82cf48203`.

- Free public weather NWP model-run / official meteorological bulletin
  first-public design screen 2026-07-18 (`cron_20260718_0921`) sealed
  `NO_LEGAL_CANDIDATE — ZERO_KEEP_WEATHER_NWP_MET_BULLETIN`.
  Codex temporary refs **E1–E12 all REJECT** (design-only; **no probe**):
  NOAA GFS cycle availability (E1); ECMWF open-data forecast cycle (E2);
  UK Met Office Shipping Forecast edition (E3); DWD ICON model cycle (E4);
  JMA regular meteorological XML / NWP bulletin (E5); ECCC GEM/MSC Datamart
  cycle (E6); BoM ACCESS / official forecast feed (E7); NOAA CPC monthly/
  seasonal outlook (E8); NWS Area Forecast Discussion AFD (E9); NOAA
  HRRR/RAP rapid-refresh (E10); NOAA SPC convective outlook (E11); WMO/WIS
  multi-centre model-status bulletin (E12). Dominant fails: **G2
  first-public published_at+TZ** (analysis/init/valid/mtime ≠ first-public
  for E1–E8/E10/E12) and **G5 cadence** (all 12: firehose ~14–168/wk or
  sparse CPC/WMO). Near-miss clocks E9 `issuanceTime` and E11 `ISSUED … UTC`
  still REJECT (E9 G1/G3/G5; E11 G3/G5/G6 vs sealed `#28`/`P12`). Secondary
  G1 rolling/current archives; G6 after noun strip vs T*/U*/#28/#30/C*/P12.
  Do **not** invent E13 densify of these objects; free Wave-H / O13 / I13 /
  N13 / S13 / L13 / X13 / Y13 / Z13 / T13 / U13 / V13 / W13 / A13 / B13 /
  C13 / D13 densify remain separately forbidden. Evidence:
  `.context/cron_20260718_0921/{TASK,PLAN,CANDIDATE_MEMO,REPORT,HERMES_VERIFY}`
  PLAN SHA `efcc2cba156bbf79a4d2e4e86302a2a906a8bcf2a3d5b04a3e64c5e126231bf8`.

- Free public pharmaceutical / FDA / EMA drug-device regulatory first-public
  design screen 2026-07-18 (`cron_20260718_0843`) sealed
  `NO_LEGAL_CANDIDATE — ZERO_KEEP_PHARMACEUTICAL_FDA_EMA_REGULATORY`.
  Codex temporary refs **D1–D12 all REJECT** (design-only; **no probe**):
  FDA CDER NDA/BLA approval package (D1); FDA Drug Safety Communication /
  MedWatch (D2); FDA Warning Letters (D3); FDA Orange Book updates (D4);
  EMA CHMP/EPAR (D5); FDA 510(k)/De Novo/PMA (D6); FDA drug shortages (D7);
  FDA import alerts (D8); FDA Class I recalls (D9); MHRA authorization (D10);
  Health Canada NOC (D11); WHO PQ decisions (D12). Dominant fails: **G2
  first-public published_at+TZ** (D1–D3, D5–D6, D9–D10) or **G1 free
  retainable 2017–2024 root/change archive** (D4, D7–D8, D11–D12). Secondary
  G6 collisions with CAP/alert `P12`/`V*`, enforcement `X10`/`X*`/`Z*`,
  health/IP `X*`, ClinicalTrials.gov `X7`. Strongest paper lead D1 still
  REJECT on G2. Do **not** invent D13 densify of these objects; free Wave-H /
  O13 / I13 / N13 / S13 / L13 / X13 / Y13 / Z13 / T13 / U13 / V13 / W13 /
  A13 / B13 / C13 densify remain separately forbidden. Evidence:
  `.context/cron_20260718_0843/{TASK,PLAN,CANDIDATE_MEMO,REPORT,HERMES_VERIFY}`
  PLAN SHA `0e678b319338b45d35335ab2e1cb02d3432d9845f4f8aed600358b50ad6fe436`.

- `HYP-BR-SESSDRIFT-EURUSD-H1-001` is terminal at offline probe (2026-07-18).
  Breedon-Ranaldo unconditional intraday drift (daily SHORT EURUSD 07:00→11:00
  UTC + LONG 13:00→17:00 UTC, Owner-approved standalone probe of the last
  untested MR-v3-spec branch): pooled 2015-2022 N=4146, gross PF 1.036
  (microscopic residual drift), PF@x1 0.889, only 2/8 positive years with
  2018–2022 all negative — the published anomaly (sample 1997–2007) has
  decayed away. Both arms (no-stop and 2×ATR SL) and both direction
  partitions dead. Do not tune windows/local-time variants, flip directions,
  or add conditioning (that becomes the separately killed conditional
  London→NY family, S528/S588/S622-623). With this, EVERY branch of the Owner
  MR v3 spec is evidence-terminal: Variant A (HYP-MR-REGIME-…-001), the full
  variant grid (HYP-MR-GRID-…-002, 8100 sims), and the B-R overlay (this);
  Variant B (OB confluence) is moot as a filter on a dead base object.
  Evidence:
  `03. EA Developer/EA_EURSessionDrift/research/HYP-BR-SESSDRIFT-EURUSD-H1-001_READOUT.md`.

- Free public payment-systems / retail clearing / settlement statistics
  first-public design screen 2026-07-18 (`cron_20260718_0727`) sealed
  `NO_LEGAL_CANDIDATE — ZERO_KEEP_PAYMENT_SYSTEMS_RETAIL_CLEARING_SETTLEMENT`.
  Codex temporary refs **B1–B12 all REJECT** (design-only; **no probe**):
  Fedwire Funds daily throughput (B1); FedACH batch clearing (B2); FedNow
  instant stats (B3); ECB TARGET2/TARGET traffic (B4); BoE CHAPS (B5); BoJ
  payment/settlement bulletin (B6); BIS CPMI/Red Book (B7); DTCC/NSCC
  securities CCP throughput (B8); Euroclear CSD settlement (B9); non-FedNow
  instant-payment public stats TIPS/SCT Inst-style (B10); card-network public
  volume reports (B11); RTGS/payment-system operational contingency notice
  (B12). Dominant fails: **G1 free retainable 2017–2024 root print archive**
  (B1–B5, B8–B12) or **G2 first-public published_at+TZ** (B6/B7). Secondary
  G5 monthly/annual sparse or transaction firehose; G6 collisions with CLS
  `#11`, ON RRP `#24`, SOFR/funding `#6`, CB ops `#5`, H.4.1, CHADV `#17`,
  securities market-structure `S*`, market status `#35`, outage `V*`. Do
  **not** invent B13 densify of these objects; free Wave-H / O13 / I13 / N13 /
  S13 / L13 / X13 / Y13 / Z13 / T13 / U13 / V13 / W13 / A13 densify remain
  separately forbidden. Evidence:
  `.context/cron_20260718_0727/{TASK,PLAN,CANDIDATE_MEMO,REPORT,HERMES_VERIFY}`
  PLAN SHA `e62f9c5a3d6aae37a7e1ffe88d2b5d698283edc54d89f3b972d97bd9a533442d`.

- Free public public-procurement award / lobbying / campaign-finance / civic
  open-data first-public design screen 2026-07-18 (`cron_20260718_0649`) sealed
  `NO_LEGAL_CANDIDATE — ZERO_KEEP_PUBLIC_PROCUREMENT_LOBBYING_CIVIC_OPEN_DATA`.
  Codex temporary refs **A1–A12 all REJECT** (design-only; **no probe**):
  US SAM/FPDS federal contract awards (A1); EU TED/eForms awards (A2); UK
  Contracts Finder / Find a Tender (A3); US FEC electronic campaign-finance
  filings (A4); US Senate LDA lobbying disclosures (A5); USAspending /
  Grants.gov award obligations (A6); NYC DOB building permits (A7); NYC 311
  service requests (A8); agency FOIA logs / reading-room (A9); California
  eProcure/FI$Cal state awards (A10); CalPERS board investment materials
  (A11); UK Companies House PSC beneficial-ownership registry (A12). Dominant
  fails: **G1 free retainable 2017–2024 root archive** (A1/A3/A6/A7/A8/A9/
  A10/A12) or **G2 first-public published_at+TZ** (A2/A4/A5/A11). Secondary
  G5 firehose or sparse; G6 collisions with SAM/grants `#*`, EDGAR `#19`/
  CURE, official-text `Z*`, CAP/alert `P12`/`V*`. Do **not** invent A13
  densify of these objects; free Wave-H / O13 / I13 / N13 / S13 / L13 / X13 /
  Y13 / Z13 / T13 / U13 / V13 / W13 densify remain separately forbidden.
  Evidence:
  `.context/cron_20260718_0649/{TASK,PLAN,CANDIDATE_MEMO,REPORT,HERMES_VERIFY}`
  PLAN SHA `094eb253f7b1c24e61e8dd94daa4d9a8cbbbc211079d0a9f08542b0ca59e0b2f`.

- Free public commodity physical inventory / customs–trade / energy storage /
  port–logistics primary-print design screen 2026-07-18 (`cron_20260718_0612`)
  sealed
  `NO_LEGAL_CANDIDATE — ZERO_KEEP_COMMODITY_PHYSICAL_INVENTORY_CUSTOMS_TRADE`.
  Codex temporary refs **W1–W12 all REJECT** (design-only; **no probe**):
  US Census/BEA FT900 goods trade (W1); China GACC customs monthly (W2); JODI
  World Oil Database (W3); OPEC MOMR (W4); GIE AGSI+ EU underground gas
  storage (W5); GIE ALSI LNG stock/send-out (W6); CME/COMEX registered–
  eligible metal warehouse stocks (W7); World Steel monthly crude steel (W8);
  Port of LA container throughput (W9); Singapore MPA bunker sales (W10);
  ABS Australia goods trade (W11); USDA NASS Cold Storage livestock (W12).
  Dominant fails: **G2 first-public published_at+TZ** (W1/W3/W4/W5/W8/W9/
  W10/W11/W12) or **G1 free retainable 2017–2024 archive** (W2/W6/W7).
  Secondary G5 monthly ~0.23/wk or daily ~7/wk; G6 collisions with principal
  statistics `#14`/`X5`, warehouse `#2/#8/I3`+GLD adjacency, EIA `#16`/
  `N11`/`X3`+capacity `#25`/`V4`, USDA `X2`, freight `#12`/`N*`/Wave-G `R4`.
  Do **not** invent W13 densify of these objects; free Wave-H / O13 / I13 /
  N13 / S13 / L13 / X13 / Y13 / Z13 / T13 / U13 / V13 densify remain
  separately forbidden. Evidence:
  `.context/cron_20260718_0612/{TASK,PLAN,CANDIDATE_MEMO,REPORT,HERMES_VERIFY}`
  PLAN SHA `066331c12897dc83d1d62871e567bbbffb3c25f63c7ec2eaed4f6904082297d0`.

- Free public critical-infrastructure operational emergency / outage first-public
  design screen 2026-07-18 (`cron_20260718_0535`) sealed
  `NO_LEGAL_CANDIDATE — ZERO_KEEP_CRITICAL_INFRASTRUCTURE_OPERATIONAL_EMERGENCY_OUTAGE`.
  Codex temporary refs **V1–V12 all REJECT** (design-only; **no probe**):
  DOE OE-417 electric emergency/disturbance (V1); ISO/RTO EEA / emergency
  operating procedure (V2); FCC NORS major network outage public report (V3);
  gas pipeline critical notice OFO/force-majeure/constraint (V4); community
  water emergency / boil-water notice (V5); NERC Level 1–3 reliability alert
  (V6); FAA NAS/ATC system emergency status (V7); Class-I freight rail system
  emergency notice (V8); USCG port/MSI system notice (V9); major public
  cyber-incident advisory non-ICS/KEV-only (V10); carrier/NOC/peering major-
  outage status (V11); nuclear unusual-event/alert/SAE/GE classification (V12).
  Dominant fails: **G1 free retainable 2017–2024 single-source root archive**
  (V2/V3/V4/V5/V7/V8/V9/V11; dashboard/aggregate/federation/rolling insufficient)
  or **G2 first-public published_at+TZ** (V1/V6/V10/V12; incident/receipt/
  effective/update clocks ≠ official first-public). Secondary G6 collisions
  with sealed `#25` gas/power capacity-interruption, CAP `#28`, SWPC `#30`,
  NGA MSI `#31`, CISA ICS `#32` / CSIRT `#41`, NRC EN `#37`, PHMSA `#39`,
  FRA `#40`, `P5–P9`/`P12`, continuous `T*`, `L*`, geophysical `U*`, `Z*`.
  Do **not** invent V13 densify of these objects; free Wave-H / O13 / I13 /
  N13 / S13 / L13 / X13 / Y13 / Z13 / T13 / U13 densify remain separately
  forbidden. Evidence:
  `.context/cron_20260718_0535/{TASK,PLAN,CANDIDATE_MEMO,REPORT,HERMES_VERIFY}`
  PLAN SHA `14c3bee8c06cadb561e4dbd21e5cd823c85466f89bc345689befb76495c99319`.

- Free public geophysical first-public bulletin design screen 2026-07-18
  (`cron_20260718_0456`) sealed
  `NO_LEGAL_CANDIDATE — ZERO_KEEP_GEOPHYSICAL_FIRST_PUBLIC_BULLETINS`.
  Codex temporary refs **U1–U12 all REJECT** (design-only; **no probe**):
  USGS earthquake product-version clock (U1); USGS volcano/VONA notices (U2);
  PTWC/NTWC tsunami messages (U3); USGS WaterAlert/streamgage alerts (U4);
  EMSC earthquake public feed (U5); Global CMT/ISC solutions (U6);
  Smithsonian GVP weekly volcanic report (U7); USGS landslide/debris-flow
  products (U8); IRIS/EarthScope FDSN bulletins (U9); JMA intensity XML (U10);
  US Drought Monitor weekly (U11); NCEI tsunami runup catalog (U12). Dominant
  fails: **G2 first-public bulletin clock** (U1/U5/U6/U7/U9/U11/U12;
  origin/update/solution/week/mod times ≠ official `published_at`+TZ) or **G1
  free retainable 2017–2024 archive** (U2/U3/U4/U8/U10). Secondary: G5
  flood/sparse; G6 collisions with sealed `#20` earthquake primitive,
  continuous `T*`, automated `P12`, CAP `#28`, and `L7/L8` impact/runup.
  Do **not** invent U13 densify of these objects; free Wave-H / O13 / I13 /
  N13 / S13 / L13 / X13 / Y13 / Z13 / T13 densify remain separately forbidden.
  Evidence:
  `.context/cron_20260718_0456/{TASK,PLAN,CANDIDATE_MEMO,REPORT,HERMES_VERIFY}`
  PLAN SHA `16a56992b343e957bce515c66345ae5eb2b0a699add14d2e7484fc2aa79f1ae0`.

- Free public remote-sensing / Earth-observation / continuous environmental
  sensor **product-release** design screen 2026-07-18 (`cron_20260718_0415`)
  sealed `NO_LEGAL_CANDIDATE — ZERO_KEEP_REMOTE_SENSING_EARTH_OBSERVATION`.
  Codex temporary refs **T1–T12 all REJECT** (design-only; **no probe**):
  daily global SST analysis (T1); daily sea-ice analysis (T2); daily
  snow-and-ice analysis (T3); half-hourly precipitation estimate (T4); daily
  soil-moisture retrieval (T5); weekly vegetation-health composite (T6);
  orbit-level trace-gas retrieval (T7); daily aerosol optical-depth analysis
  (T8); daily ocean-color chlorophyll analysis (T9); daily land-surface-
  temperature CDR (T10); daily gridded satellite-altimetry sea level (T11);
  hourly air-quality sensor-network product (T12). Dominant fails: **G2
  first-public product-release clock** (T1–T6, T8–T12; analysis/observation/
  catalog times ≠ official `published_at`+TZ) or **G1 incomplete 2017–2024
  archive** (T7 Sentinel-5P operational history starts 2018). Secondary: G4
  Earthdata/Copernicus account walls; G5 weekly or orbit-flood; G6 if
  thresholded into CAP/SWPC/P12 hazard alerts. Do **not** invent T13 densify
  of these objects; free Wave-H / O13 / I13 / N13 / S13 / L13 / X13 / Y13 /
  Z13 densify remain separately forbidden. Evidence:
  `.context/cron_20260718_0415/{TASK,PLAN,CANDIDATE_MEMO,REPORT,HERMES_VERIFY}`
  PLAN SHA `a4844d09118012aec0e102f2d71e6d8cf5ba7869f42dbc31c789b2048d072f01`.

- Free public official-text / policy / speech / legislative / court design
  screen 2026-07-18 (`cron_20260718_0336`) sealed
  `NO_LEGAL_CANDIDATE — ZERO_KEEP_OFFICIAL_TEXT_POLICY_SPEECH_LEGISLATIVE_COURT`.
  Codex temporary refs **Z1–Z12 all REJECT** (design-only; **no probe**):
  CB policy speeches/testimony (Z1); policy minutes/accounts (Z2); legislative
  bill intro/text versions (Z3); enacted statutes/public law (Z4); committee
  hearing transcripts (Z5); CBO cost estimates (Z6); executive orders /
  proclamations (Z7); regulator interpretive guidance (Z8); SCOTUS opinions /
  orders (Z9); federal civil complaints/dockets (Z10); sanctions /
  export-control actions (Z11); civil/criminal enforcement releases (Z12).
  Dominant fails: **G2 first-public published_at+TZ** (Z1/Z3/Z5/Z6) or **G6
  rebrand** after proper-noun strip (Z2/Z4/Z7–Z12 collide with FR #18/CURE,
  OFAC S6, CourtListener X12, enforcement X10, CB/rates publication, Wave-G
  legal-action). Do **not** invent Z13 densify of these objects; free
  Wave-H / O13 / I13 / N13 / S13 / L13 / X13 / Y13 densify remain separately
  forbidden. Evidence:
  `.context/cron_20260718_0336/{TASK,PLAN,CANDIDATE_MEMO,REPORT,HERMES_VERIFY}`
  PLAN SHA `4805837211602d934de564e1292688b52838567e77af5e447ea9fae0ff722836`.

- Y5 Kalshi macro Economics-print offline economic probe 2026-07-18
  (`cron_20260718_0211`, `HYP-KALSHI-MACRO-PRINT-H1-XAU-001`) terminal
  **`KILL_AT_OFFLINE_PROBE`**. Series-scoped complete archive (318,579 trades,
  world=0 allowlist SHA `02ba66af…`, prereg `d62bf4f7…`): train N=616 / val
  N=259, gross PF 0.941/0.947 (dead before cost), PF@x1 0.744/0.796, x1.5
  0.664/0.731, x2 0.594/0.673, all years 2021–2024 negative, challenger worse
  than matched H1 momentum control, combined maxDD@x1 51.7%, bootstrap P95 DD
  64.7%. **Do not** densify World weather, thresholds, session/hour vetoes,
  year filters, Polymarket/on-chain rebrand, or Y13 of this object. No `.mq5` /
  Model 0 / holdout reopen without a materially different PIT infoset + new
  hyp ID. Evidence:
  `.context/cron_20260718_0211/{ECONOMIC_PROBE_RAW,REPORT,CANDIDATE_MEMO}` +
  `03. EA Developer/EA_KalshiMacroPrint/research/HYP-KALSHI-MACRO-PRINT-H1-XAU-001_READOUT.md`.

- Free public digital-alt / CEX microstructure / prediction / free-vol design
  screen 2026-07-18 (`cron_20260718_0122`) sealed with mixed result:
  **Y1–Y4 and Y6–Y12 REJECT** (design); **Y5 Kalshi macro prediction trade
  prints `PROBE_PASS_SOURCE_FEASIBILITY`** (source only — economics later
  **killed** at `cron_20260718_0211`). Rejects (do **not** densify as Y13+): Y1 CEX perpetual
  funding (G2 settlement≠published_at); Y2 CEX forced-liquidation WS (G1 no
  free archive); Y3 CEX aggregate OI (G1 ~1-month history only); Y4 stablecoin
  CEX premium from klines (G6 OHLC residual densify O5/O6); Y6 Polymarket /
  on-chain prediction (G6 dup of Y5 or P1–P4 rebrand); Y7 free Cboe VIX/VVIX
  daily (G2 date/close only); Y8 free CME daily FX/options bulletin (G6 densify
  CME/CFTC participation); Y9 crypto ETF primary shares (G6 GLD primary-flow
  rebrand); Y10 free retail equity-flow top-list (G2 no row published_at);
  Y11 Google Trends / search intensity (G2/G1/G3 mutable normalized); Y12 AWS
  EC2 spot (G1 90-day only). **Y5 survivor caveats (source-only):** World category impure
  (weather); freeze required Economics allowlist before economic probe. Do **not** invent Y13
  densify of rejected digital-alt objects. Evidence:
  `.context/cron_20260718_0122/{TASK,PLAN,CANDIDATE_MEMO,REPORT,SOURCE_PROBE_RAW,HERMES_VERIFY,raw_samples/kalshi/}`
  PLAN SHA `1b3e6f758b9a234880a9225189dcb770165d838c8f262c75a4b693c7faecd035`.

- Free public hard real-activity / health-epidemiology / IP-patent / civil-
  enforcement design screen 2026-07-18 (`cron_20260718_0040`) sealed
  `NO_LEGAL_CANDIDATE — ZERO_KEEP_HARD_REAL_ACTIVITY_HEALTH_IP_ENFORCEMENT`.
  Codex temporary refs **X1–X12 all REJECT** (design-only; **no probe**):
  Baker Hughes North America rotary rig-count weekly; USDA Crop Progress /
  WASDE; EIA WPSR product-supplied / implied-demand field densify; University
  of Michigan consumer-sentiment prelim/final; Census New Residential
  Construction housing-starts; Redfin weekly pending/listings + NAR monthly
  housing demand; ClinicalTrials.gov protocol/results first-post; CDC FluView
  weekly + NWSS wastewater; USPTO weekly patent-grant + PGPub union; DOJ/FTC
  civil antitrust / consumer-protection first-public press; SEMI North America
  semiconductor equipment billings/book-to-bill; CourtListener RECAP federal
  civil antitrust first appearance. Dominant fails: **G2 first-public
  published_at+TZ** (standing schedule, “after/by N:00”, date-only, rolling
  RSS), **G5 cadence** (weekly/monthly below 2–5/elapsed-week), **G1 free
  retainable archive** (mutable Redfin panel, SEMI paid/gap, RECAP incomplete
  contemporaneous archive), or **G6 densify/channel-swap** (X3 = EIA `#16`;
  X5 = Census/BLS/BEA principal-stats `#14`; X12 = publisher swap of X10).
  Near-miss paper only: X5 G2–G4 PASS still G5+G6 REJECT; X9 G5 PASS still
  G2/G4 REJECT. Do **not** invent X13 densify of these objects; free Wave-H,
  O13 OHLC, I13 auction/warehouse, N13 nowcast, S13 credit, L13 labor densify
  remain separately forbidden. Evidence:
  `.context/cron_20260718_0040/{TASK,PLAN,CANDIDATE_MEMO,REPORT,HERMES_VERIFY}`
  PLAN SHA `6da02465a0bf18f45c3cba2c22f8c54714368d852b5b8dd5bf2c73b658281768`.

- Free public labor / transport / bank-failure / catastrophe design screen
  2026-07-18 (`cron_20260717_2357`) sealed
  `NO_LEGAL_CANDIDATE — ZERO_KEEP_LABOR_TRANSPORT_BANKFAIL_CATASTROPHE`. Codex
  temporary refs **L1–L12 all REJECT** (design-only; **no probe**): TSA daily
  passenger checkpoint throughput; ADP National Employment Report; Challenger
  job-cut announcements; state UI initial claims panel; FDIC failed-bank /
  receivership notices; OCC/Fed supervisory enforcement / consent-order; PCS
  catastrophe insured-loss estimates; NOAA billion-dollar weather disasters;
  BTS airline on-time performance; Fed H.4.1 reserve factors; MBA weekly
  mortgage applications; AAR weekly rail carload/intermodal. Dominant fails:
  **G1 free retainable archive** (TSA mutable table, ADP methodology/first-
  vintage gap, PCS entitlement, NOAA reconstructed costs, BTS no first-vintage
  monthly chain, MBA subscription/teaser), **G2 first-public published_at+TZ**
  (Challenger CMS, FDIC closing-date/Last Updated, OCC monthly batch, AAR noon
  without official TZ), or **G5 weekly cadence** (state claims 1/wk + G6 densify
  of #14; H.4.1 1/wk + G6 CB liquidity #5/#24/I7/S11). Near-miss G6 paper only:
  L1 TSA, L5 FDIC, L7 PCS, L11 MBA — still REJECT on earlier gates. Do **not**
  invent L13 densify of these objects; free Wave-H, O13 OHLC, I13 auction/
  warehouse, N13 nowcast, S13 credit densify remain separately forbidden.
  Evidence:
  `.context/cron_20260717_2357/{TASK,PLAN,CANDIDATE_MEMO,REPORT,HERMES_VERIFY}`
  PLAN SHA `830a823cd05b8b6775c839be7e1d05713cbbd13d9b2f225d2f0c672bc591c548`.

- Free public credit / market-structure / regulatory / FX-intervention design
  screen 2026-07-17 (`cron_20260717_2315`) sealed
  `NO_LEGAL_CANDIDATE — ZERO_KEEP_CREDIT_MARKET_STRUCTURE`. Codex temporary
  refs **S1–S12 all REJECT** (design-only; **no probe**): FINRA TRACE
  corporate-bond activity; MSRB EMMA municipal trades/disclosures; OCC daily
  options volume/OI; ICI weekly money-market fund assets; Treasury TGA daily
  balance; OFAC SDN designation/list change; Japan MOF FX intervention
  disclosure; SNB weekly sight deposits / FX assets; FINRA ATS/non-ATS weekly
  volume; SEC Form ATS-N / putative ATS volume; NY Fed Primary Dealer
  positions/financing/fails; FINRA daily off-exchange short-sale volume.
  Dominant fails: **G1 free retainable archive** (EMMA paid bulk, OCC UI ~24
  months, ICI last-20-weeks rolling, ATS rolling 4y historic, ATS-N not a
  continuous volume series / late start) or **G2 first-public published_at+TZ**
  (“end-of-day”, “available by 4:00 p.m.”, “approximately 4:15 p.m.”, “no later
  than 6:00:00 p.m. ET”, date-only SDN/MOF/SNB transitions). Independent G6
  diagnostics: TGA = sealed #4 cash balance; OFAC = R2/#18 legal restriction;
  SNB = I7/#5/#24 CB liquidity. Near-miss S12 short-sale daily files still die
  on G2 upper-bound clock. Do **not** invent S13 densify of these objects;
  free Wave-H, O13 OHLC, I13 auction/warehouse, N13 nowcast densify remain
  separately forbidden. Evidence:
  `.context/cron_20260717_2315/{TASK,PLAN,CANDIDATE_MEMO,REPORT,HERMES_VERIFY}`
  PLAN SHA `63d1f1afd7d534149a5acaef9d853c692d614d8bbcb68bc308ab75f2f61c1bdd`.

- Free public HF macro nowcast / freight design screen 2026-07-17
  (`cron_20260717_2234`) sealed `NO_LEGAL_CANDIDATE — ZERO_KEEP_HF_MACRO_NOWCAST_FREIGHT`.
  Codex temporary refs **N1–N12 all REJECT** (design-only; **no probe**):
  Atlanta Fed GDPNow; NY Fed Staff Nowcast; Cleveland Fed Inflation Nowcast;
  Chicago Fed NFCI/ANFCI; Philadelphia Fed ADS; SF Fed Daily News Sentiment;
  Baltic Dry Index; SCFI/Drewry WCI; ALFRED/FRED first-print surprise panel;
  global manufacturing PMI; EIA jet-fuel/WPSR field; NY Fed GSCPI. Dominant
  fails: **G1 free retainable first-release archive** (licensed BDI, rolling
  workbooks, chart-only history, commercial PMI history, GSCPI pre-2022
  reconstruction), **G2 first-public published_at+TZ** (“around 10:00”,
  “within a few hours”, date-only ALFRED vintage, report-date without file
  clock), **G5** structural weekly/monthly cadence below 2/elapsed-week, or
  **G6 rebrand** after proper-nouns removal vs free `#12/#14/#15/#16/#26`,
  Wave-G `R4` logistics index, Wave-G `R20` model-score, killed
  FRED-displacement/model-score / GoldMacro DFII10 residual. Near-miss N6
  (sentiment G6 PASS on paper) still dies on G1/G2/G5. Do **not** invent
  N13+ densify of these nowcast/freight/logistics/model-score objects; free
  Wave-H, O13 OHLC densify, and I13 auction/warehouse densify remain
  separately forbidden. Evidence:
  `.context/cron_20260717_2234/{TASK,PLAN,CANDIDATE_MEMO,REPORT,HERMES_VERIFY}`
  PLAN SHA `5ea277b48ad5e070d32ac0c161d7e3d074c27c9fd66869e28a71d0dfa4a1577d`.

- Independent non-US primary/LME free-clock design screen 2026-07-17
  (`cron_20260717_2152`) sealed `NO_LEGAL_CANDIDATE — ZERO_KEEP_INDEPENDENT_INFOSET`.
  Codex temporary refs **I1–I12 all REJECT** (design-only; **no probe**):
  UK DMO gilt competitive auction; DE Finanzagentur Bund issuance; JP MOF
  JGB competitive auction clocks; LME warehouse stocks/movements; LBMA Gold
  Price auction free timestamps; AOFM tender results; RBNZ/SNB open-market
  ops; ICE Futures Europe/Endex circulars; Euronext cash open/close auction
  clocks; BoE APF gilt operations; ECB euro FX reference rates; BoC GoC
  auction. Dominant fails: **G2 first-public published_at+TZ** (auction close
  / “immediately after” / “around 16:00” / “no later than” are not clocks) or
  **G1 free retainable 2017–2024 archive** (LME paid history; LBMA licensed;
  ICE/Euronext incomplete free history; AOFM recent RSS only). Independent
  fatal **G6 rebrand** after proper-nouns removal: sovereign auctions = #1/#22;
  CB ops = #5/#24; warehouse = #2/#8; fixing = #10/#13. Country/publisher/
  asset swap is **not** a new causal object. Do **not** invent I13+ densify of
  these objects; free Wave-H and O13 OHLC densify remain separately forbidden.
  Evidence: `.context/cron_20260717_2152/{TASK,PLAN,CANDIDATE_MEMO,REPORT,HERMES_VERIFY}`
  PLAN SHA `51d0eb8f70f9c543d51d8d3ab276cc29be4c62bd7a747207ba4b6ad7ff544ab5`.

- Pure-OHLC orthogonal family design screen 2026-07-17
  (`cron_20260717_2110`) sealed `NO_LEGAL_CANDIDATE — ZERO_KEEP_OHLC_ORTHOGONAL`.
  Codex temporary refs **O1–O12 all REJECT** (design-only; **no probe**):
  prior-session range continuation; cross-TF vol-regime momentum; calendar
  seasonality as primary; OHLC absorption/rejection; basket residual fade;
  vol term-structure break; jump aftershock; signed realized-semivariance;
  early-to-late intraday momentum; close-location pressure; weekend/session
  gap; directional-change intrinsic-time overshoot. Dominant fails:
  **killed-family densify/rebrand** after proper-nouns removal (Sonic/Asia
  coil/ORB, Unicorn/PO3/KLR/FVG rejection, V5 pressure, XS residual/mom,
  MR grid, LNY/gap); secondary no paper path, structural cadence <2/week,
  or threshold-manufactured density. Do **not** invent O13+ densify of these
  objects; free-PIT Wave-H rebrand remains separately forbidden. Pure-OHLC
  novelty path is at frontier unless a genuinely independent information set
  or Owner paid/label unlock. Evidence:
  `.context/cron_20260717_2110/{TASK,PLAN,CANDIDATE_MEMO,REPORT,HERMES_VERIFY}`
  PLAN SHA `037c2538230741a708d413e3a5a55d423e4582d25a56ec60358be02ad2dd20b7`.

- Free/public PIT post-frontier design screen 2026-07-17
  (`cron_20260717_2031`) sealed `NO_LEGAL_CANDIDATE — ZERO_KEEP_POST_FRONTIER`.
  Codex temporary refs **P1–P12 all REJECT** (design-only; **no probe**):
  blockchain/on-chain supply, bridge settlement, collateral liquidation,
  protocol governance (P1–P4); day-ahead power / balancing / gas capacity
  clearing publications (P5–P7); NOTAM, AIS safety broadcast, AIS/ADS-B
  surveillance (P8–P10); certificate-transparency credential inclusion (P11);
  automated EO/hazard detection alerts (P12). Dominant fail: **G6 rebrand**
  after proper-nouns removal vs A–N / #1–#44 / Wave-G R1–R20; secondary
  `NO_PAPER_PATH` where first-public clock, immutable archive, lineage, or
  non-engineered 2–5/week cadence cannot be defended. Do **not** invent
  Wave-H / free-menu rebrands of these transports; chain/Merkle/sensor/API
  novelty ≠ new causal object. Free path remains frontier unless true cure
  of a sealed hard fail or Owner paid/label unlock. Evidence:
  `.context/cron_20260717_2031/{TASK,PLAN,CANDIDATE_MEMO,REPORT,HERMES_VERIFY}`
  PLAN SHA `eab79c42b303d49ae3641fad335e216cda3bd33a34fad135a03cd78942dcec21`.

- Free/public PIT CURE-ATTEMPT 2026-07-17 (`cron_20260717_1855`) sealed
  `NO_LEGAL_CANDIDATE — CURE_ATTEMPT_ZERO_PASS` on near-miss reopen of **Q1/#1
  Treasury auction**, **#19 SEC EDGAR**, **#18 Federal Register** (PLAN SKIP
  #13 CFETS; #35 not authorized). Not Wave-H; no #45+. (Q1) early-2017
  competitive-result XML still empty `<ReleaseTime/>` (Hermes live agree);
  2023 HH:MM clocks lack TZ; auction-close invalid → `CURE_FAIL_G2`. (19)
  `master.idx` date-filed only; no official acceptance→first-public complete
  accession+exhibits+TZ bind → `CURE_FAIL_G2`. (18) PI history HTTP 200 again
  (prior 500 not reproduced) but `filed_at` nulls (e.g. 2023-11734) + no
  fail-closed first-public contract/lineage → `CURE_FAIL_G2`. Do **not**
  re-probe these three without **newer** official free evidence than the 1855
  raw set; do not invent Wave-H rebrands; free path remains frontier unless
  true cure or Owner paid/label unlock. Evidence:
  `.context/cron_20260717_1855/{TASK,PLAN,CANDIDATE_MEMO,REPORT,SOURCE_PROBE_RAW,HERMES_VERIFY}`
  + `raw_samples/` (61 files) + `hermes_raw/`; PLAN SHA
  `54df683e1049e1dbec3a5ffe226957eb5459c4d6464322a05936afc0fef2428a`.

- Free/public PIT Wave-G design screen 2026-07-17 (`cron_20260717_1818`)
  sealed `NO_LEGAL_CANDIDATE — WAVE_G_DESIGN_ZERO_KEEP_POST_44`. Codex design
  R1–R20 all REJECT (G6 rebrand of A–N/#1–#44 or NO_PAPER_PATH); **no #45–#50
  labels**; **no probe** authorized. Free path at frontier after #1–#44 + this
  anti-rebrand screen. Do **not** invent Wave-H rebrands; reopen free only with
  **new** official free evidence curing a sealed class's first hard fail, or
  Owner paid unlock / Unicorn human labels. Evidence:
  `.context/cron_20260717_1818/{TASK,PLAN,HERMES_VERIFY}` PLAN SHA
  `9cb261622a68a386de1d5c9eeca8aa4b04121631cbf638c4c073fd2b043a26e6`.

- Free/public PIT Wave-F residual reserves 2026-07-17 (`cron_20260717_1735`)
  sealed `NO_LEGAL_CANDIDATE` on **#41 national-CSIRT confirmed compromise**
  and **#43 large-scale strike first declaration**. Design set **#39–#44
  FULLY ATTEMPTED** (top-4 at 1644 + both reserves here). Do not reopen
  #39–#44 without new official free evidence curing the first hard fail; do
  **not** invent Wave-G rebrands of #1–#44. (41) CISA/NCSC date-only +
  systematic noon-UTC padding (`T12:00:00Z` / RSS 30/30 hour=12); ACSC live
  timeout; CERT-EU detail Release Date clock without TZ; fixed panel fails
  any leg → `NOT_LEGAL_G2` (Hermes live re-verify AGREE). (43) Teamsters/UAW
  WordPress CMS `date`/`date_gmt`/`modified` + date-only display; Unite live
  403; BLS not PIT clock → `NOT_LEGAL_G2`. Evidence:
  `.context/cron_20260717_1735/{TASK,PLAN_REF,CANDIDATE_MEMO,REPORT,SOURCE_PROBE_RAW,HERMES_VERIFY}`
  + `raw_samples/` (65 files / ~5.3 MB) + `hermes_raw/`.

- Free/public PIT Wave-F top-4 2026-07-17 (`cron_20260717_1644`) sealed
  `NO_LEGAL_CANDIDATE` on **#39 PHMSA pipeline accident**, **#40 FRA main-track
  collision**, **#42 IPPC plant-pest first report**, **#44 WARN mass-layoff**.
  Design set **#39–#44** planned; top-4 probed; reserves later sealed at
  `cron_20260717_1735`. Do not reopen #39/#40/#42/#44 without new official free
  evidence curing the first hard fail; do **not** invent Wave-G rebrands of
  #1–#44. (39) Rolling HL bulk; receipt/accident clocks only; no first-public
  published_at+TZ → `NOT_LEGAL_G2` (live phmsa 403; 648-col extract retained).
  (40) Occurrence date/time + monthly rolling lag; not immutable first-public
  objects → `NOT_LEGAL_G2`. (42) Listing date-only; detail Publication Date
  clock without official TZ → `NOT_LEGAL_G2`. (44) CA/NY notice/posted dates
  only → `NOT_LEGAL_G2`. Evidence:
  `.context/cron_20260717_1644/{TASK,PLAN,CANDIDATE_MEMO,REPORT,SOURCE_PROBE_RAW,HERMES_VERIFY}`
  + `raw_samples/` (61 files / ~28 MB).

- Free/public PIT residual reserves 2026-07-17 (`cron_20260717_1602`) sealed
  `NO_LEGAL_CANDIDATE` on **#37 NRC radiological emergency** and **#38 NTSB
  investigation launch**. Design set **#33–#38 fully attempted** (top-4 at
  1510 + both reserves here). Do not reopen #33–#38 without new official free
  evidence curing the first hard fail; do **not** invent Wave-E rebrands of
  #1–#38. (37) Historical EN HTML exposes licensee Notification Time [ET] /
  Event Time / Last Update Date only — no first-public web published_at+TZ →
  `NOT_LEGAL_G2` (live nrc.gov 403 from host; samples retained). (38) Public
  NTSB PR date-only; SharePoint ArticleStartDate midnight default
  (`…T05:00:00Z`) vs divergent CMS Created/Modified → `NOT_LEGAL_G2`. Evidence:
  `.context/cron_20260717_1602/{TASK,PLAN_REF,CANDIDATE_MEMO,REPORT,SOURCE_PROBE_RAW,HERMES_VERIFY}`
  + `raw_samples/` (89 files).

- Free/public PIT orthogonal top-4 2026-07-17 (`cron_20260717_1510`) sealed
  `NO_LEGAL_CANDIDATE` on **#35 NYSE market-system**, **#36 CPSC recall**,
  **#34 FDA drug shortage**, **#33 WHO DON**. Design set **#33–#38** planned;
  top-4 probed; reserves later sealed at `cron_20260717_1602`. Do not reopen
  #33–#36 without new official free evidence curing the first hard fail; do
  **not** invent Wave-E rebrands of #1–#36. (35) Free NYSE system/2 API has
  real epoch-ms `publishedDate` but upper-bound parent cadence 0.591/0.335 per
  elapsed week ≪ 2.0 → `NOT_LEGAL_G5_SOURCE_ONLY_CADENCE`. (36) SaferProducts
  REST `RecallDate`/`LastPublishDate` all `T00:00:00` no TZ → G2 fail. (34) FDA
  detail `Date first posted` date-only → G2 fail. (33) WHO DON API 2017 objects
  all `PublicationDateAndTime=…T00:00:00Z` → G2 fail both-split. Evidence:
  `.context/cron_20260717_1510/{PLAN,CANDIDATE_MEMO,REPORT,SOURCE_PROBE_RAW,HERMES_VERIFY}`.

- Free/public PIT discovery Wave-D residual 2026-07-17 (`cron_20260717_1431`)
  sealed `NO_LEGAL_CANDIDATE` on reserves **#31 NGA NAVAREA** and **#32 CISA ICS**.
  Full free design set **#1–#32 EXHAUSTED**. Do not reopen without new official free
  evidence curing the recorded first hard fail; do **not** invent Wave-E rebrands.
  (31) NGA MSI NavWarnings/NTM/API HTTP 503 maintenance; FAQ JS SPA only; DailyMem
  Zulu DTG present but MSI email/web is SOLAS **supplement** and current in-force
  only → `NOT_LEGAL_G2_POINT_IN_TIME_AVAILABILITY`. (32) CISA historical ICS pages
  expose Last Revised only as noon-UTC date (`…T12:00:00Z`); Update A overwrites
  visible date; listing/Release Date also date-only → same G2 fail. Evidence:
  `.context/cron_20260717_1431/{CANDIDATE_MEMO,REPORT,SOURCE_PROBE_RAW,HERMES_VERIFY}`.

- SGE SHAU fixing detail is terminal at source feasibility despite valid
  density (4.642/week train; 4.647/week validation). Official article/listing
  pages expose only a date, sampled responses have no `Last-Modified`/`ETag`,
  and no official first-publication or revision lineage was found. Do not
  invent a T+1 availability timestamp, infer historical availability from the
  current endpoint, or join XAU outcomes. Reopen only with immutable official
  `published_at` plus version lineage. Evidence:
  `03. EA Developer/EA_SGEFixingPulse/research/SGE_SHAU_SOURCE_FEASIBILITY_READOUT.md`.

- `HYP-FVG-SCALP-CONFL-M5-EUR-001` is terminal at de-dup. Its M5
  three-candle FVG plus 40-60% fill/rejection is the same primary object as
  killed `HYP-H1-DISPLACE-FVG-CONT-001`; HTF BOS, OB, premium/discount,
  liquidity sweep, session and management scoring only densify the dead
  price-only family. Current source compiles 0/0 and is closed-bar clean, but
  engineering validity does not authorize Model 0. Do not change FVG fill,
  confluence, session, timeframe, symbol, RR, BE/partial or year as rescue.
  Evidence:
  `03. EA Developer/EA_FVGConfluence/research/HYP-FVG-SCALP-CONFL-M5-EUR-001_DEDUP_READOUT.md`.

- `HYP-CME-OI-CONT-H1-FX-001` is terminal. Daily CME FX futures open-interest
  expansion had valid density but negative post-cost expectancy in both
  unsealed splits: PF x1 0.878 train and 0.924 validation; x1.5/x2 also failed.
  Do not reverse direction, change OI ranking/threshold, symbol/day/hour,
  17:00-20:00 window, stop/RR, or open 2024-2025 as rescue. Evidence:
  `03. EA Developer/EA_CMEParticipationPulse/research/HYP-CME-OI-CONT-H1-FX-001_READOUT.md`.

- Do not use CME Daily Volume call/put labels as signed options demand: later
  monthly contracts aggregate call and put rows, and the public bulletin has
  no buyer/seller aggressor. Cboe EVZ is also not a current operational input:
  the official history ends 2025-03-11. A new hypothesis must prove a currently
  live point-in-time source with continuous 2017-2025 coverage before outcomes.

- Public SDR FX-options free-data frontier is terminal at source feasibility.
  DTCC has dense current files but public historical objects before mid-2024
  are deep-archived without restore. CME SDR has official 2017-2023 history,
  but a hash-bound three-day/month sample falls to zero major-FX new-option
  days in 2023 and only 1.944 active days/week on 2022-2023 validation. Do not
  rescue by ending the sample in 2022, multiplying same-day pairs, accepting a
  sub-2 cadence, or treating call/put currency orientation as buyer/seller
  demand. Evidence: `EA_CFTCOptionsPulse/research/*SDR*FEASIBILITY_READOUT.md`.

- Free/public PIT discovery 2026-07-17 (`cron_20260717_0746`) sealed
  `NO_LEGAL_CANDIDATE` on Q1–Q3. Do not promote without new official evidence:
  (1) U.S. Treasury auction absorption has free Fiscal Data allocation fields
  for 3086 auctions 2017–2024 and strong mechanism de-dup, but PIT fails —
  `record_date` is date-only with multi-day lag, XML `ReleaseTime` empty for
  early-2017 samples (40/40), and live historical objects show bulk
  Last-Modified rewrite (2026-05-22) without vintage lineage. Do not invent
  close+2min or treat PDF CreationDate as published_at contract. (2) COMEX
  gold stocks/delivery free surface is current files; free immutable
  2017–2024 archive + published_at not proven (history routes to paid
  DataMine). (3) Cboe free IV CSVs are date-only/single live files without
  vintage; EVZ ends 2025-03-11; BPVIX/JYVIX/EUVIX end before 2024-12-31.
  Evidence: `.context/cron_20260717_0746/{PLAN,CANDIDATE_MEMO,REPORT,SOURCE_PROBE_RAW}.md|json`.

- Free/public PIT discovery 2026-07-17 (`cron_20260717_0839`) sealed
  `NO_LEGAL_CANDIDATE` on matrix #5–#8 (after Q1–Q3/#4). Do not reopen without
  new official evidence: (5) ECB/BoE/BoJ liquidity-op allotment — free fields
  exist but no TZ published_at; BoJ free daily archive only from 2025-10
  (2017–2024 daily 404); ECB 2017 HTML shows `converted at 2020-07-28`; BoE
  by-operation XLSX are rolling with 2026 Last-Modified. (6) Overnight funding
  volume/dispersion panel fails 2017 coverage contract — SOFR production starts
  2018-04-02 (volume+percentiles free thereafter), €STR 2019-10-01; do not splice
  pre-production proxies to manufacture 2017. (7) TFX Click 365 free retail
  long/short is weekly-only (~1/elapsed-week cadence fail); free daily files are
  OHLC/total OI not retail long/short; vendor daily positioning rejected.
  (8) SHFE gold warehouse has no free PIT stronger than SGE (WAF/SPA shells;
  no immutable free archive + published_at). Evidence:
  `.context/cron_20260717_0839/{PLAN,CANDIDATE_MEMO,REPORT,SOURCE_PROBE_RAW}.md|json`.

- Free/public PIT discovery 2026-07-17 (`cron_20260717_0920`) sealed
  `NO_LEGAL_CANDIDATE` on matrix #9–#12 and declared the free/public **12-class
  PIT matrix EXHAUSTED**. Do not reopen without new official free evidence:
  (9) Japan MOF weekly ITS — free JP `week.csv` covers 2017–2024 with ~53
  periods/year and official 8:50 JST schedule, but weekly-only cadence ≈1.0
  per elapsed week fails 2–5 target; rolling CSV lacks immutable first-release
  vintage; multi-trade forward-fill forbidden. (10) Gold lease/GOFO free
  composite fails closed if any leg fails — SOFR free history starts
  2018-04-02 (y2017=0); LBMA historical is IBA/MyLBMA licence + date-only JSON
  `{d,v}`; CME free GC settlement bulk not available (403). (11) CLS free
  surface is monthly FX Trade Volume (sign-up); dense history is commercial
  CLSMarketData. (12) Panama Canal free advisories exist but max density
  ~0.8–1.1/elapsed week (<2); no TZ published_at; bulk Last-Modified rewrite
  risk. Evidence:
  `.context/cron_20260717_0920/{PLAN,CANDIDATE_MEMO,REPORT,SOURCE_PROBE_RAW,HERMES_VERIFY}.md|json`.

- Free/public Wave-B discovery 2026-07-17 (`cron_20260717_0959`) sealed
  `NO_LEGAL_CANDIDATE — WAVE_B_TOP4_ATTEMPTED: #13,#14,#15,#16`. Do not reopen
  without new official free evidence curing the first hard fail:
  (13) CFETS CNY central parity — free hist API ~1957 dates 2017–2024 (~4.7/wk)
  but hist records are date+values only; no official per-release published_at/TZ
  (current 9:15 is not a historical contract). (14) U.S. principal-statistics
  first-vintage panel (BLS/BEA/Census) — BLS schedules/archives free, but Census
  economic-indicators calendar returns Cloudflare 403 so the fixed multi-agency
  panel cannot bind full PIT. (15) Eurostat euro-indicators — free samples exist
  but 2017 release dates are date-only; no full-history CET/CEST published_at
  contract (PDF Last-Modified invalid). (16) EIA WPSR+WNGSR weekly pair — WPSR
  week archive present; WNGSR first-release weekly archive missing (rolling
  ngshistory.xls is not first-vintage; storage archive paths 404). Evidence:
  `.context/cron_20260717_0959/{PLAN,CANDIDATE_MEMO,REPORT,SOURCE_PROBE_RAW,HERMES_VERIFY}.md|json`.

- Free/public Wave-B RESERVE discovery 2026-07-17 (`cron_20260717_1052`) sealed
  `NO_LEGAL_CANDIDATE — WAVE_B_RESERVE_ATTEMPTED: #17,#18,#19,#20` and declares
  free/public PIT matrix **#1–#20 EXHAUSTED**. Do not reopen without new official
  free evidence curing the first hard fail:
  (17) CME Clearing CHADV performance-bond notices — free 2017/2020/2024 HTML
  with Notice/Effective **dates only** (e.g. Chadv17-159 27/28 Apr 2017); no
  publication clock/TZ → `NOT_LEGAL_G2_POINT_IN_TIME_AVAILABILITY`.
  (18) Federal Register trade/export (USTR/BIS/Treasury) — free FR API
  `publication_date` is date-only; historical public-inspection timing queries
  HTTP 500 → `NOT_LEGAL_G2_POINT_IN_TIME_AVAILABILITY`.
  (19) SEC EDGAR gold/silver miner 8-K/6-K (SIC 1040) — free indexes and
  acceptanceDateTime samples exist, but bulk master.idx is date-filed only and
  exhibit first-public bind + TZ contract not proved →
  `NOT_LEGAL_G2_POINT_IN_TIME_AVAILABILITY`.
  (20) USGS ComCat mine-belt seismic — free FDSN/ComCat works but first-vintage
  /deletion archive not proved (preferred-state risk); origin time ≠ first-public
  → `NOT_LEGAL_G3_REVISION_LINEAGE`.
  Do not invent free classes that rebrand #1–#20. Evidence:
  `.context/cron_20260717_1052/{PLAN,CANDIDATE_MEMO,REPORT,SOURCE_PROBE_RAW,HERMES_VERIFY}.md|json`.

- Free/public Wave-C discovery 2026-07-17 (`cron_20260717_1137`) sealed
  `NO_LEGAL_CANDIDATE — WAVE_C_TOP4_ATTEMPTED: #21,#22,#23,#24`. Do not reopen
  without new official free evidence curing the first hard fail:
  (21) Elexon REMIT unavailability — free Insights API has `publishTime` ISO Z
  from ~2017-10 samples, but free docs are SPA/403 and do not bind first-public
  + publisher TZ for full history; early-2017 by-publish weeks empty →
  `NOT_LEGAL_G2_POINT_IN_TIME_AVAILABILITY` (by-id latest-revision-only = G3 risk).
  (22) EU ETS primary auction demand/cover — EC/EEX official language is result
  publication **within 15 minutes** of close; PLAN rejects close+window; free
  yearly primary-result XLSX archive paths 404 →
  `NOT_LEGAL_G2_POINT_IN_TIME_AVAILABILITY`.
  (23) USDA FAS daily export-sales announcements — schedule language 9 a.m. ET
  exists, but free historical immutable daily announcement objects with
  release-ID clocks 2017–2024 not recovered (ESR/Cornell paths 404) →
  `NOT_LEGAL_G2_POINT_IN_TIME_AVAILABILITY`.
  (24) NY Fed ON RRP operation results — free hist Markets API works for
  2017/2020/2024, but fields are operation clocks + naive `lastUpdated`, not a
  documented first-public result publication+TZ contract →
  `NOT_LEGAL_G2_POINT_IN_TIME_AVAILABILITY` (do not promote as DTS/SOFR rescue).
  PLAN reserves #25–#26 were later probed and sealed at `cron_20260717_1235`.
  Do not rebrand #21–#24. Evidence:
  `.context/cron_20260717_1137/{PLAN,CANDIDATE_MEMO,REPORT,SOURCE_PROBE_RAW,HERMES_VERIFY}.md|json`.

- Free/public Wave-C residual discovery 2026-07-17 (`cron_20260717_1235`) sealed
  `NO_LEGAL_CANDIDATE — WAVE_C_RESERVE_ATTEMPTED: #25,#26` and declares free/public
  PIT matrix **#1–#26 EXHAUSTED**. Do not reopen without new official free evidence
  curing the first hard fail:
  (25) ENTSOG/ENTSO-E physical gas/power capacity shock — free ENTSOG interruptions
  API is no-key and returns historical rows with `periodFrom`/`periodTo`/
  `lastUpdateDateTime` only; no official first-public `published_at`+TZ; PLAN
  rejects lastUpdate/period clocks as PIT; ENTSO-E web API without token is 401;
  AGSI+ API requires key → `NOT_LEGAL_G2_POINT_IN_TIME_AVAILABILITY`.
  (26) NESO non-REMIT day-ahead demand-forecast revision — free CKAN API works,
  but official live resource text is publication **windows** 09:00–09:15 and
  12:00–12:15 (not exact clocks); historic series starts **2018** (2017 empty);
  portal HTML 403 → `NOT_LEGAL_G2_POINT_IN_TIME_AVAILABILITY`.
  Evidence:
  `.context/cron_20260717_1235/{PLAN,CANDIDATE_MEMO,REPORT,SOURCE_PROBE_RAW,HERMES_VERIFY}.md|json`.

- Free/public Wave-D discovery 2026-07-17 (`cron_20260717_1320`) sealed
  `NO_LEGAL_CANDIDATE — WAVE_D_TOP4_ATTEMPTED: #28,#27,#29,#30` and declares free/public
  PIT matrix **#1–#30 EXHAUSTED**. Do not reopen without new official free evidence
  curing the first hard fail:
  (28) FEMA/NWS CAP extreme-weather lifecycle — OpenFEMA free archive has TZ-bearing
  CAP `sent` for 2017/2020/2023/2024 and official **24h GMT publication delay**
  (MapServer); G2 archive-path preflight pass, but even Tornado Warning initial
  `msgType=Alert` alone is 2071/2695/3637 events in 2020/2023/2024 (~40–70 per
  elapsed week) ≫ 5.0 upper bound → `NOT_LEGAL_G5_SOURCE_ONLY_CADENCE`. Do not
  rescue by narrowing severity/event taxonomy after counts, polygon/zone
  multiplication, or inventing live first-public clocks beyond the official delay.
  (27) FAA ATCSCC system-level flow-control — advisory form/list/historical deep
  links return **403 Access Denied**; no immutable SEND TIME+TZ objects recovered
  for 2017–2024 → `NOT_LEGAL_G2_POINT_IN_TIME_AVAILABILITY`.
  (29) WOAH WAHIS animal-disease notification — official code requires Members to
  notify via WAHIS **or fax/email within 24 hours** (submission obligation); free
  WAHIS SPA + email distribution list + 1992–2006 weekly archives do not prove
  exact public `published_at`+TZ for 2017–2024 immediate notifications →
  `NOT_LEGAL_G2_POINT_IN_TIME_AVAILABILITY`.
  (30) NOAA SWPC space-weather warning — current `alerts.json` has Issue Time UTC
  but is rolling only; free historical surfaces are graphical timeline and NCEI
  next-day `dayevt` observational reports, not retainable G/S/R warning first-public
  objects for 2017–2024 → `NOT_LEGAL_G2_POINT_IN_TIME_AVAILABILITY`.
  PLAN reserves #31 NGA NAVAREA / #32 CISA ICS were **not** probed this tick.
  Do not invent Wave-E rebrands of #27–#30. Evidence:
  `.context/cron_20260717_1320/{PLAN,CANDIDATE_MEMO,REPORT,SOURCE_PROBE_RAW,HERMES_VERIFY}.md|json`.

- `HYP-MR-REGIME-EURUSD-H1-001` is terminal at offline probe (2026-07-17). The
  Owner MR v3 spec's Variant A — detrended-z fade (|z|≥2 vs SMA100) on EURUSD
  H1 gated by ADX(H1)<23 + ADX(H4)<28 + ATR-percentile[25,75] + half-life[4,48]
  — was falsified against its own always-on control under a pre-outcome frozen
  plan: the un-gated object is dead before cost (gross PF 0.981 train / 0.923
  validation) and the regime ensemble made it WORSE (PF@x1 0.685/0.247, 82 vs
  657 trades, required +0.10 PF margin inverted in both splits). Do not rerun
  or rescue by tuning Z/W/SL/TP/session, swapping the trendiness index
  (CI/Hurst/other), dropping single gates, moving to M15 or XAUUSD, post-hoc
  hour/day/year vetoes, or optimistic re-costing. Regime-gated OHLC
  mean-reversion on majors/gold is a closed family; a new MR lane needs a
  materially different information set + fresh prereg. Evidence:
  `03. EA Developer/EA_HybridRegimeMR/research/HYP-MR-REGIME-EURUSD-H1-001_READOUT.md`.
  Reusable data win (do not re-derive): EURUSD H1/H4/M1 2015–2026 parquet +
  weekly-verified FivePercent server→UTC model (EU DST ≤2023, US DST ≥2024) at
  `03. EA Developer/EA_HybridRegimeMR/research/evidence/`; the broker's
  historical M1/H1 `spread` column is zero-filled 2023+ — never use it as cost
  evidence.

- **AMENDMENT 2026-07-17 (Owner scope directive, pre-run).** The regime-gated
  OHLC-MR family closure is converted from a single-config kill
  (`HYP-MR-REGIME-EURUSD-H1-001`, which stays terminal/killed) into an
  **exhaustive pre-registered grid falsification** under the NEW id
  `HYP-MR-GRID-EURUSD-H1-002`. The Owner explicitly directed research to
  enumerate the full legal variant grid (W / Z / K_sl / TP_cap / k_ts /
  trailing × 6 gate arms per cell; conditional gate-subset/threshold/session
  ablation) offline on the unsealed 2015–2022 splits, log EVERY simulation,
  and pass one deflated verdict (DSR, Bailey & López de Prado 2014) over the
  full trial count. This is the **sanctioned closure instrument, not a rescue
  of -001**: the same tune list forbidden as rescue is permitted only because
  every cell is declared pre-outcome, every trial is counted, and the verdict
  defaults to `KILL_FAMILY_EXHAUSTIVE`. Hard exclusions unchanged: no
  M15/lower TF, no XAUUSD/other symbol, no CI/Hurst/new trendiness gate, no
  news filter without calendar, no post-hoc cells/axes, entry object stays
  std-normalized detrended-z, holdout 2023+ sealed, cost stays frozen
  UNVERIFIED_PROXY. A DSR survivor is a flag requiring fresh Owner-approved
  prereg + verified cost + Model 0 — the grid never authorizes `.mq5`/live.
  If no cell survives, the family is `CLOSED_EXHAUSTIVE`. Evidence:
  `03. EA Developer/EA_HybridRegimeMR/research/HYP-MR-GRID-EURUSD-H1-002_GRID_PLAN.md`.
  **RESULT (same day): the grid ran and the family IS `CLOSED_EXHAUSTIVE`.**
  8100 simulations, ZERO arms reached the necessary condition gross PF ≥ 1.25
  (max 1.2476, median 0.8902); max net PF@x1 anywhere 1.0991; best deflated
  arm DSR 0.0129 vs floor 0.95 with negative expectancy; Stage-2 auto-skipped.
  The failure is the object, not the tuning. Do not run any further OHLC
  regime-gated MR variant on majors/gold — reopen requires a materially
  different information set + fresh Owner-scoped prereg. The sealed 2023+
  holdout was never opened. Scope (addendum 2026-07-18): Stage-1 axes at
  session [7,16) were simulated; Stage-2 session-shift/threshold arms were
  routed away by the frozen necessary-condition rule, not simulated, and the
  gate-ablation sub-claim is contingent on unverified MT5 indicator parity.
  Evidence:
  `03. EA Developer/EA_HybridRegimeMR/research/HYP-MR-GRID-EURUSD-H1-002_READOUT.md`
  + `_READOUT_ADDENDUM.md`.

- `HYP-CFTC-FX-H1-001` is terminal: do not repair/rerun the weekly TFF
  `Combined - FutOnly` leveraged-money residual by changing historical market
  name matching, missing-bar policy, direction, magnitude threshold, Monday
  hours, ATR stop, cost proxy or holding period. It was negative gross in both
  train and internal validation and passed only 2/22 frozen gates. A future
  FX-options lane requires a materially different point-in-time information
  set such as transaction-level public SDR flow or paid strike/surface data.

Updated: 2026-07-17
Language: English (evidence plane). Purpose: stop re-running dead ends.

Authority: evidence pointers only. Do **not** invent kill reasons. If a row has
no pointer, treat as unknown and re-check artifacts before any revive.

Companion inventory: `00. Old File/EA_Archive/MANIFEST_20260715_workspace_cleanup.json`  
Portfolio audit: `00. Old File/EA_Archive/EA_SonicR/research/20260710_EA_FAILURE_PORTFOLIO_AUDIT.md`  
Strategy diary (legacy S-numbers): `02. AlphaFactory/STRATEGY_LOG.md`

## How to use

1. Before a new hypothesis, search this file + registry + STRATEGY_LOG.
2. “Do not revive unless X” is a **hard gate**, not a suggestion.
3. Post-hoc threshold/hour/day veto from a just-read readout → new `idea` only,
   never a rescue of the killed hyp (`AGENTS.md`).

---

## A. EA families (shelf / killed) — code now under `00. Old File/EA_Archive/`

| Family / EA | Verdict (evidence) | Do not revive unless |
|---|---|---|
| **EA_SonicR** Classic XAU route | Best short seed PF~1.40 / ~1.23 tpw; longer route PF~1.15; equity REJECT; regime pocket 2024-25 — **not survivor**. Full package + research ledger archived 2026-07-15 under `EA_Archive/EA_SonicR/`. | New independent mechanism + cost provenance; not another Asian-range / CONTEXT / Dragon-Trend / ATR-delete-cadence patch on same fields. Audit `20260710_EA_FAILURE_PORTFOLIO_AUDIT.md`. |
| **EA_SilverBullet** historical book | Near cadence seed PF~1.33 / ~1.99 tpw; The5ers transfer **KILL** (PF~1.02, x1.5~1.00); overnight vs scalp contract. Full package archived 2026-07-15 under `EA_Archive/EA_SilverBullet/` — no active code lane. | Fresh Model 0 only after Owner restores package to `03. EA Developer/` + updates `hot.md`; not tune from `131343` / The5ers kill. |
| **EA_LondonNY** | Strong PF/quality but ~0.3 tpw; cross-pair transfer killed; book ~0.42 tpw — sparse sleeve. | Cadence-capable universe redesign with prereg; not pair-add rescue. |
| **EA_ITSM** | Holdout PF~1.05 + 2024-25 decay → **KILL**. Portfolio expansions with ITSM offline **FAIL**. | Independent thesis; not Spark/SB+ITSM densify. |
| **EA_ChopRegime** | Untouched 2018-20 OOS PF~1.03 → **KILL_FAMILY**. | New family id + different mechanism. |
| **EA_Gotobi** | TZ fix did not rescue; treatment PF~0.91. | New evidence package. |
| **EA_Spark** / **EA_M15SparkAsian** | Configs ~PF 1.00 / 0.93; SB+Spark dual-runner Model 0 **KILL** (tester PF 1.219 < 1.30). | Independent Spark child with capital twin + a priori weights — not deposit-contaminated rerun. Readout `20260714_HYP_PORTFOLIO_SB_SPARK_RUNNER_001_READOUT.md`. |
| **EA_H4Ribbon** | Pooled PF ~0.36. | — |
| **TrendBook** / trend distance patches | Portfolio PF ~0.50; Dragon/Trend distance killed cadence-vs-impulse tradeoff. | — |
| **Gap-fill** | Stage-1 illusion; compiled probe PF~0.48. | — |
| **EA_Portfolio** (legacy multi-sleeve host) | Tear-down: contaminated toggles reintroduce killed sleeves. | Clean dual-instance compose only after survivors; do not compile legacy host. `20260714_EA_PORTFOLIO_TEARDOWN_FOR_SB_SPARK_BOOK.md`. |
| **EA_Cobra** | Historical E8 survivor class but sparse (~0.5 tpw in audit taxonomy); outside current SB Phase-0 universe. | Owner-scoped new prereg — not silent revive. |
| **EA_InsideBar** | Killed in portfolio teardown table. | — |
| Other flat `EA_*` under archive (ACF, Gold*, M15*, H1*, etc.) | Shelf after 20260710 frontier / later offline boards; many never cleared Model 0 with hypothesis_id. | Registry row + offline probe beat locked controls; no compile-from-archive as evidence. |

Duplicate / index stubs archived (do not use as fallback):
`EA_SilverBullet_Index` (full package),
`00. Old File/EA_Archive/EA_SilverBullet_dead_siblings/`
(`EA_SilverBullet_v2_Index.mq5`, `EA_SilverBullet_v1_backup.mq5`), and the
full former-active package
`00. Old File/EA_Archive/EA_SilverBullet/`. No active pin under
`03. EA Developer/` (shelf empty 2026-07-15).

---

## B. Research approaches / hypothesis classes already killed

### Sonic field / process illusions (closed frontier)

| Approach | Kill summary | Evidence | Do not revive unless |
|---|---|---|---|
| Generic sideway/range, compression breakout, retest, context-rescue | Failed on Sonic fields | Portfolio audit | Materially different feature set |
| EUR Asian manipulation | Cadence OK (~2.21 tpw) but cost PF~1.08 + year concentration fail | Portfolio audit | New cost-honest holdout |
| GBP value-drift EMA89 | Holdout cost PF~0.82 | Portfolio audit | — |
| XAU ATR filter “improve PF” | Deletes ~90% cadence | Portfolio audit | — |
| Same-bar consensus / lead-lag / laggard catch-up (S555/S618/S670 class) | Locked falsification controls for FX factor idea | Portfolio audit + XS prereg notes | Beat all three in train + one-time holdout |
| Matched-control-less Model 1 promotion | Model 1 kill/park only | `AGENTS.md` | — |
| Zero/missing cost treated as zero | Invalid | Doctrine / cost audit | Verified broker cost artifact |
| Active-week cadence denominator | Invalid | Portfolio audit | Elapsed calendar weeks only |
| Post-hoc hour/day/year veto | Forbidden rescue | `AGENTS.md` | New preregistered idea |

### Deep Research / data frontier (2026-07-13+)

| Item | Result | Pointer | Do not revive unless |
|---|---|---|---|
| V2–V7 Deep Research strategy candidates | No legal MT5 candidate / family locks | `readouts/20260713_DEEP_RESEARCH_V*_COORDINATOR_AUDIT.md`, failure packets V3/V6/V7 | Owner-new scope + de-dup clearance |
| V5 Impact-per-Pressure proxy | `KILL_AT_OFFLINE_PROBE` | `20260713_IMPACT_PRESSURE_PROXY_PROBE_READOUT.md` | Not rename/rescue; need independent hyp |
| V8 weekly carry / rates offline | `KILL_AT_OFFLINE_PROBE` (PF high, cadence dead) | `20260713_V8_CARRY_DIFF_OFFLINE_PROBE_READOUT.md` | Different timescale + cadence design |
| QFSI / GVBCI as strategy authority | Foundation only; QFSI STOP / quote-days gate | V4 foundation readout; hot QFSI 006 harvest | Research-grade multi-month quote+commission+slip |
| Unicorn exact-adjacency XAU M5 (`HYP-UPS-XAU-M5-001`) | `PARKED_BEFORE_BUILD`: 65 candidates, 55 long/10 short, 23 active months, median 3/month; failed 4/5 frozen density gates | `03. EA Developer/EA_UnicornPrecisionScalper/research/HYP-UPS-XAU-M5-001_READOUT.md` | Do not lower score/displacement/overlap or revive 001. The materially different stateful-sweep 002 is the only open Unicorn mapping and remains cost-blocked before Model 0. |
| Unicorn four-closed-bar control (`HYP-UPSC-XAU-M5-002`) | `KILL_AT_MODEL0_RESEARCH_FALSIFICATION`: N=138, 1.334/week, report PF 0.986/net -$233.83; research full-cost PF 0.688, x1.5 0.574, x2 0.481; robustness 0%, MC P95 DD 5.654% | `03. EA Developer/EA_UnicornPrecisionScalperControl/research/HYP-UPSC-XAU-M5-002_READOUT.md` | Do not disable weak hours/weekdays/years, lower filters, change RR/session, or rerun this ID. The separately preregistered event-anchored Unicorn lane must stand on its own identity and cannot inherit post-outcome tuning. |
| Unicorn event-anchored sweep (`HYP-UPS-XAU-M5-006`) | `KILL_AT_MODEL0_RESEARCH_FALSIFICATION`: N=130, 1.257/week, report PF 0.724/net -$4,396.90; research full-cost PF 0.498, x1.5 0.413, x2 0.343; robustness 0%, MC P95 DD 7.118%, equity REJECT. It was diagnostically worse than the already-killed four-bar control. | `03. EA Developer/EA_UnicornPrecisionScalper/research/HYP-UPS-XAU-M5-006_READOUT.md` | Unicorn fixed-expiry/event-expiry family is closed. Do not try another sweep-age threshold, price-invalidation variant, weak day/hour veto, RR/session/score tune, or rename. Require a materially different causal mechanism and fresh preregistration. |
| Unicorn report-to-code fidelity audit | Prior Model-0 kills apply to the coded proxy, not the unimplemented discretionary memo. Missing MSS/BOS close, true breaker geometry, FVG freshness/fill and micro-confirmation cannot be silently added as a rescue. The build probe also used breaker scan 8 while Model-0 source used 6 (17 candidate identities differ); corrected full-bar invalidation changed zero candidates. | `03. EA Developer/EA_UnicornPrecisionScalper/research/20260716_UNICORN_REPORT_TO_CODE_FIDELITY_AUDIT.md` | Do not claim the memo is falsified, but also do not run an “MSS/retest fidelity” child without sealed labels, de-dup against PO3/KLR, one frozen feature family and a fresh hypothesis/window. |
| Unicorn alert-label taxonomy gate | V1.2 run `20260716_153059` proved the taxonomy problem but is diagnostic-only for future labeling: objective review found only 22/200 rows passing sweep+displacement+MSS+FVG before breaker judgment; sealed Grok calibration gave final-core kappa 0.286, sweep -0.154 and breaker 0.000, while binary human kappa was not estimable. V1.3 run `20260716_155111` is the authoritative source-bound, breaker-complete blank corpus and remains unlabeled. The detector emits on FVG formation, before post-formation micro-confirmation can exist. | `03. EA Developer/EA_UnicornPrecisionScalper/research/20260716_ALERT_FIRST_LABEL_GATE_READOUT.md`; `20260716_ALERT_FIRST_CASEBOOK_V123_COLLECTION_READOUT.md` | Do not treat AI labels as independent human review; do not add MSS/retest/breaker or open HYP-009/Model 0. Label only immutable V1.3 rows through overlays. Do not query MT5 context by logged UTC as broker bar time: use decision server time, normalize the frozen offset and treat decision time as the M5 close cutoff. |
| Unicorn FVG-CE resting limit (`HYP-UPS-XAU-M5-007`) | `KILL_AT_FILL_FEASIBILITY_PROBE`: 115/251 fills in 3 bars, 45.82% fill rate, 1.110/week, 87 long/28 short. Failed fill-rate, cadence and short-count gates before PnL/source/backtest. | `03. EA Developer/EA_UnicornPrecisionScalper/research/HYP-UPS-XAU-M5-007_READOUT.md` | Do not extend expiry, move away from CE, add market fallback/chase, remove shorts or filter hours/days. Current memo needs an alert-first labeled-quality program or a materially new causal information set, not another execution variant. |
| Unicorn owner-directed RR1.5 replay (`HYP-UPS-XAU-M5-008`) | `KILL_DIAGNOSTIC`: exact HYP-006 replay N=132, WR 35.606%, report PF 0.697/net -$4,904.75, full-cost PF 0.475/x1.5 0.391/x2 0.322, robustness 0%, MC P95 DD 7.315%. WR rose only 0.991 pp versus 2.5R while PF/net/DD worsened. | `03. EA Developer/EA_UnicornPrecisionScalperRR15/research/HYP-UPS-XAU-M5-008_READOUT.md` | Do not test another RR, disable Thursday/hour/session/year/direction, or tune break-even/hold/score/sweep thresholds. The target is not the missing edge; require a materially independent causal mechanism. |
| PO3-AMD XAU M5 report v1 | `KILL_AT_OFFLINE_PROBE`: 212,339 M5 bars / 774 ET dates, only 6 dates met the frozen 80..300-point Asian range; sweep control N=1, full PO3 N=0 | `03. EA Developer/EA_PO3_AMD_Scalper/research/HYP-PO3-AMD-SCALP-M5-XAU-001_READOUT.md` | Do not widen/reinterpret Gold points, range max, session or retest under the killed ID. ATR-relative/normalized range is a new Owner-scoped hypothesis. |
| PO3-AMD ATR-normalized London (`HYP-PO3-AMD-SCALP-M5-XAU-002`) | `KILL_AT_OFFLINE_PROBE`: range coverage recovered to 729/774 dates, but 121 sweeps -> 1 displacement+MSS -> 1 FVG -> 0 retests; control N=36, PF 0.511, -10.71R | `03. EA Developer/EA_PO3_AMD_Scalper/research/HYP-PO3-AMD-SCALP-M5-XAU-002_READOUT.md` | Do not loosen H4 bias, displacement, MSS, FVG/retest or normalized range under 002. Only the report's independently pre-declared NY branch may receive a fresh ID. |
| PO3-AMD ATR-normalized NY (`HYP-PO3-AMD-SCALP-M5-XAU-003`) | `KILL_AT_OFFLINE_PROBE`: 122 sweeps -> 0 displacement+MSS; control N=37, PF 0.674, -5.42R and all three years negative; challenger N=0 | `03. EA Developer/EA_PO3_AMD_Scalper/research/HYP-PO3-AMD-SCALP-M5-XAU-003_READOUT.md` | PO3 report lane closed. Do not mine more sessions or weaken H4/displacement/MSS/FVG/retest. Require materially different external thesis/provenance. |
| KLR Scalper report mapping + external USD branch | Offline HYP-001 was sparse; Owner-required native replication then independently confirmed the kill. FivePercent Model 0 core N=4/0.02555 per week/PF 1.891; USD gate N=1/0.00639 per week. Native funnel 346 raids -> 61 displacement/MSS -> 26 FVG -> 5 retests. Both fail cadence by orders of magnitude; tiny-sample positive PF is not an edge. | `03. EA Developer/EA_KLR_Scalper/research/HYP-KLR-MT5-REPLICATION-M5-XAU-001_READOUT.md` plus the parent offline readout | Do not rename, remove the USD gate, loosen structure/displacement/FVG/retest, mine session/hour/day/year/RR, rerun the same IDs, or open 2025+. Require a materially different causal mechanism/provenance and fresh Owner-scoped hypothesis. |
| XAU next-session real-yield shock (`HYP-GMP-XAU-M15-REALYIELD-001`) | `KILL_AT_OFFLINE_PROBE`: N=270, 1.726/week, cost-proxy PF 0.684, -63.10R, DD 16.87%, 0/3 positive years. Gross PF was only 1.061 before commission/slippage. | `03. EA Developer/EA_GoldMacroPulse/research/HYP-GMP-XAU-M15-REALYIELD-001_READOUT.md` | Do not change the 5 bp threshold, 14:30 UTC entry, inverse direction, ATR stop, RR, hold, year/subgroup or cost to rescue this ID. Require a materially different information set and fresh prereg. |
| Lagged SPDR primary creations/redemptions (`HYP-GLDFLOW-XAU-M15-002`) | `KILL_AT_OFFLINE_PROBE_NO_EDGE`: N=512, 3.273/week, gross PF 0.862/-44.40R; x1 PF 0.556/-180.42R/DD 48.56%; x1.5 0.448; x2 0.358; 0/3 positive years and worse than matched momentum control. HYP-001 was a pre-outcome schema kill only. | `03. EA Developer/EA_GLDFlowPulse/research/HYP-GLDFLOW-XAU-M15-002_READOUT.md` | Do not reverse flow direction, threshold/smooth/z-score creations, mine days/hours/years, change RR/hold/session, substitute holdings changes, or open 2025+. Require a materially different information set and fresh prereg. |

### Offline monetization / greenfield boards (2026-07-15/16) — killed before or at Model 0

| Hypothesis / board | Why dead | Do not |
|---|---|---|
| RR2 BE@1R, MFE stall-cut | Path exits destroy edge | Densify arm/stall/giveback; revive BE@1R |
| Scale-out 1R50 / timebox 2h / vol-regime R-mult | Kill under joint PF+stress | Densify scale/timebox/R-mult |
| ATR-trail M1 path proxy | KILL (false early SL); envelope survivors ≠ deployable | Treat offline PF as Model 0; densify arm/k |
| LNY EUR fade / GBP coil / EUR lead catch-up | Cadence+PF+stress kills | Densify imbalance/coil/catch-up |
| Asia pctl-coil London break | Cadence kill (nearest miss) | Densify p40/lookback/hours |
| Greenfield XS USD residual/mom + AUDNZD zMR | Joint screen kill | Densify XS z / mom / AUDNZD z |
| FRED displace / ToT spam | Owner-rejected stall path | Revive FRED spam boards |
| Cost freeze invented from shallow capture | Diagnostic only (quote days << 90) | Invent cost freeze / densify Wave8 |
| DRAT ONNX regime-gated sweep → MSS → FVG/OB retest (`HYP-DRAT-ONNX-ICT-M15-EUR-001`) | Frozen EURUSD M15 OOS probe: rules-only PF 0.764 / -67.75R; ONNX gate PF 0.749 / -52.82R; all year buckets negative | Tune regime probability, session, RR, hold time, sweep/MSS/FVG thresholds or attach the model gate to killed Hybrid-Sonic source. Read package readout before any independent DRAT revival. |
| Gold→USDJPY inverse lead as a local DRAT alternative | Historical PF 1.26 came from Mon/Thu selection; the later Mon/Thu-unfiltered, weekend-flat closed-bar Model 0 produced PF 0.97, N=931, net -$710.49 at ~3.57 elapsed-week cadence | Reapply weekday/hour mining or add ONNX/ICT gates after reading the clean-transfer loss. See `EA_DRAT_ONNX_ICT_Hybrid/research/20260716_DRAT_INDEPENDENT_FRONTIER_AUDIT.md`. |

Best **shelf** reference run (not promotion): SilverBullet RR2 `20260714_194548` (a priori +$12 x1.5 still fail per closeouts). GOAL unmet.

---

## C. Process failures already paid for (do not reintroduce)

- Attractive PF hiding calendar cadence miss.
- Short favorable windows outranking longer falsification.
- Tester zero slippage / fixed $0.50 as live proof.
- Tool exit-code PASS as numeric validation.
- Duplicate reruns as independent confirmation.
- Globally keyed timestamp `run_id` cross-wiring EAs (ITSM/LondonNY collision).
- Compiling from `00. Old File` or other archive paths as evidence.
- Calling a discretionary memo tested when the EA only implemented a proxy;
  require a hard-gate requirement-to-code matrix and scope claims to exact source.
- Letting offline builder and Model-0 source drift in lookback/anchor/invalidation;
  compare event identities before economic execution.
- Treating formation-time FVG alerts as if a later retest/micro-confirmation had
  already occurred.
- Using AI agreement to clear a preregistered human-label gate, or joining
  outcomes before taxonomy agreement and density are frozen and passed.
- Mixing MT5 UTC log time with broker server-time bars, or leaving decision
  timestamp semantics (`open` versus `close cutoff`) implicit.
- Calling a zero-trade casebook collection a performance backtest or citing its
  PF/cadence; collection authority requires mutation/outcome off and source-bound
  schema/manifest.

### Agent delivery failure — Owner correction 2026-07-16

This is an execution-quality failure, not a request for more safety ceremony.

- The agent started with an incomplete Unicorn proxy and only audited full
  report-to-code fidelity after economic Model 0. Missing MSS/BOS, true breaker,
  FVG state, M15 structure and micro-confirmation should have been resolved or
  explicitly scoped before calling the EA implementation complete.
- The build probe used breaker lookback 8 while the Model-0 source used 6,
  producing a 17-event identity difference. This is weak implementation control,
  not useful experimentation.
- A rejected nonportable Python path wrote 360,407,524 bytes to C despite the
  Owner's storage objective. Later cleanup does not erase the avoidable miss.
- Compile/test/safety hardening, casebook tooling and documentation volume were
  repeatedly presented as progress while the requested faithful EA logic,
  economic evidence and GOAL remained unmet.
- Work fragmented into plans, audits and follow-up research and repeatedly
  waited for Owner prompts such as `tiến hành`/`oke` instead of continuing the
  next legal material step autonomously.
- After the Owner asked for lessons about poor delivery, the first response
  again promoted strategy/safety rules rather than owning execution quality.
- The thread goal was marked `complete` after 925,764 tokens / 3,343 seconds
  even though `GOAL.md`, `hot.md` and the Owner still said the requested EA
  outcome was unmet. This was a false closeout, not a tooling detail.
- Frequent status/checkpoint behavior made the Owner supervise routine next
  steps. Reporting activity is not autonomy; the agent must continue the next
  safe in-scope experiment without waiting for another acknowledgement.

Required correction: keep one outcome-led loop; do code/compile/test/backtest or
probe/diagnosis before closeout prose; continue without micro-prompts while
authority remains; treat status messages as information rather than approval
gates; and never label intermediate engineering artifacts as EA completion.
Add process only when it prevents a repeated material loss or directly unlocks
the next verification step; otherwise consolidate or remove it.

### Unicorn V1.2 -> V1.3 casebook and execution lessons

Evidence: `03. EA Developer/EA_UnicornPrecisionScalper/research/20260716_ALERT_FIRST_CASEBOOK_V123_COLLECTION_READOUT.md`.

- Manifest-only source identity is insufficient for a review corpus. A
  label-eligible casebook must bind the same exact source SHA256 in task,
  receipt, run manifest, metadata, every row and downstream extractor.
- Freeze the full review taxonomy before collection. Omitting a semantic field
  such as true-breaker validity makes the old corpus diagnostic-only; preserve
  it, do not rewrite its schema or silently use an overlay as equivalent data.
- MQL5 `input string` values must be written as plain `key=value`. The numeric
  optimization tuple becomes literal string data. If required sidecars are
  absent, inspect tester inputs and `OnInit`; do not weaken EA validation to
  force a run through.
- API enumeration failure is not an empty account/history state. Position,
  order and deal traversal must fail closed when a ticket/select call fails.
- Pre-send money sizing is only a budget estimate. Recalculate stop-loss money
  risk from actual fill price, SL and volume, include declared execution cost,
  and close immediately when the frozen budget is exceeded.
- Broker deviation is a slippage allowance, not the maximum spread. Keep
  spread gating and order deviation as separate contracts.
- A zero-trade data-acquisition run has no win rate, PF or expectancy. Log its
  schema/storage/provenance verdict separately from strategy performance.
- Upgrade and preflight every downstream consumer against the new schema before
  calling the corpus usable. Parse success alone is not enough; reject old
  contract ids, missing label columns and source-hash mismatch.
- Under tester-only mutation authority, non-tester persistence code is dormant.
  Do not claim restart-persistent peak equity unless an authorized execution
  mode and a runtime test actually exercise that branch.

---

## D. What is still allowed (narrow)

- Six compilable packages remain under `03. EA Developer/`, but package
  presence is not execution authority. `EA_FVGConfluence`, Hybrid, KLR and all
  Unicorn packages are terminal/audit-only.
- Canonical active ledger: `04. Memory/research/CANDIDATE_REGISTRY.jsonl`.
  Archived Sonic ledger remains de-dup history only; compile-from-archive invalid.
- New independent mechanisms follow de-dup → cheap offline probe → frozen prereg
  → capability/cost contract → sequential matched Model 0.
- Data acquisition toward research-grade bid/ask + commission + slip (QFSI frontier), without pretending gate is green.
- A fresh DRAT hypothesis requires a genuinely new point-in-time information
  set such as FX options-implied state/real OI or primary-market signed order
  flow. Public current-day summaries or another OHLC/ATR/ICT recombination are
  not sufficient.
