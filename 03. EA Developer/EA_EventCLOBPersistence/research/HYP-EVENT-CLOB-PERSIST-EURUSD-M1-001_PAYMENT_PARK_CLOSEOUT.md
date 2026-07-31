# Payment Park Closeout — HYP-EVENT-CLOB-PERSIST-EURUSD-M1-001

Status: `PARK_SOURCE_PAYMENT_AUTHORITY_UNMET`

The strategy remains economically untested. This is an authority park, not a
no-edge verdict and not a completed EA.

## Preserved source evidence

- Immutable quote plan ID:
  `F8CC58697DAF05713DCD4A4D0DDF1AA3DE9684A3DF646AE9C8F424F645851BDB`.
- Estimated source cost: USD 7.005795553319.
- Estimated billable size: 15,044,831,392 bytes (14.0116 GiB).
- Coverage: 630/630 frozen canonical event windows.
- Free calls: 631 `metadata.get_cost` attempts, including one bounded transient
  retry; 630 `metadata.get_billable_size` attempts.
- Forbidden calls: zero time-series, zero batch and zero paid requests.
- Raw source state: zero DBN files and no download manifest.
- Evidence manifest:
  `02. AlphaFactory/data/databento/cme_6e_event_clob/evidence/FREE_QUOTE_F8CC5869/manifest.json`,
  SHA-256 `2AE3A6CE134653F452FBA62677A1141E0F561ED686028BF9C5940BB149EEAA71`.

The earlier Stage-0 source readout is frozen byte-for-byte at SHA-256
`A6EB3855E3DF1965E80CBCF945EB64B7C94213C576BF71F16C464F6CBF19E162`
because the canonical parked registry row binds that exact artifact.

## Current guard

- Canonical registry: 268 rows / 89 hypotheses PASS.
- EVENT history: exact `idea -> probe -> parked` three-row sequence; latest row
  SHA-256 `15DAF05F86AAC2777925589ABE35725A274746A80C94F067A40FC333EB8643E3`.
- V9 acquisition tool SHA-256:
  `CDB887AD88410CDFC537B56876B77ADBCDB5D7F11A637A5B889A18E64E23FDE4`.
- V9 focused tests SHA-256:
  `1DAB39BA5279F196F3897F5423957BD9C533FD655E57E9D6DEED348D5E4F73E6`.
- Parent and independent reviewer runs: 48/48 PASS.
- Active plan is offline only, ID
  `FFE1B9BD054A54D4215FBCD148B627E2BF9192C5005191999C08CC1D21B37F82`,
  SHA-256 `C485CA9D35359E0F8447C7B78ECD69CB2D6A398880A9F18337D64FD9F0DEFF10`.
- V9 rejects `download_windows` at the parked-authority gate before creating a
  lock, calling live metadata or reaching `timeseries.get_range`.

The duplicate quote receipt and storage assessment were removed from the active
data-root after hash verification; both remain byte-recoverable in the immutable
evidence directory above. The active root now contains only the offline plan.

## Reopen condition

The Owner must explicitly approve a positive USD ceiling. Recommended ceiling:
**USD 7.75**, a 10.6% buffer above the final quote. A future amendment must bind
that authority and the latest parked registry row before the tool can re-quote
and issue one serial paid source download. If the live re-quote exceeds the
ceiling, it stops before the first paid call.

Even after source acquisition, `.mq5` remains forbidden until Stage 0B source
coverage/cadence and both predeclared economic splits survive. No chart/backtest
claim exists yet. The owner goal remains active and UNMET.
