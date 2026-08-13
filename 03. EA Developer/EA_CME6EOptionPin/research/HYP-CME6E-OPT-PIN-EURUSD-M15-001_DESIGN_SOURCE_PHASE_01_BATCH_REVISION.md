# HYP-CME6E-OPT-PIN-EURUSD-M15-001 - phase-01 batch revision

The frozen phase-01 streaming request was attempted once on 2026-08-12 and
returned `BentoServerError` after 66 seconds.  No local payload or partial file
was created.  Automatic retry was not performed.  The hypothesis, parents,
period, schema, budget ceiling, and all event-discovery rules remain unchanged.

Databento documents `BentoServerError` as a server-side 5xx condition and
recommends `batch.submit_job` for large requests because streaming does not
return until all data is downloaded.  Revision R1 changes delivery only:

- same exact `GLBX.MDP3` definition request;
- DBN/Zstandard, parent to instrument-ID mapping;
- one `batch.submit_job` call, `split_duration=year`, download delivery;
- no `timeseries.get_range` retry;
- submit once, persist job ID immediately, then poll read-only;
- downloading an already billed completed batch job does not constitute a new
  data purchase and may resume only from the persisted job ID;
- the same live quote must remain finite and strictly below USD 10;
- no statistics, target, outcome, MQL5, or MT5 authority is added.

The failed streaming charge is not inferable from local artifacts.  The local
receipt records zero received bytes.  Before phase-2 statistics, cumulative
budget accounting must conservatively use a verified Databento batch billed
size/cost and must stop for Owner authority if uncertainty could put cumulative
campaign spend at or above USD 10.

