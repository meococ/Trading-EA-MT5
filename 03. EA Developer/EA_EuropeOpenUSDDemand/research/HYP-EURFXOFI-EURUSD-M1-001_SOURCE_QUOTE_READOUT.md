# HYP-EURFXOFI-EURUSD-M1-001 - source quote readout

## Verdict

`PARK_SOURCE_PAYMENT_AUTHORITY_UNMET`

The free metadata quote is complete and independently reconciled. No market
data was downloaded, no paid request was made and no economic outcome was
joined. A new explicit Owner ceiling tied to this source plan is required
before acquisition; the earlier USD 3.50 authority was specific to another
plan and is not reused.

## New information set

The candidate would add CME Globex 6E ten-level order-book state during the last
30 seconds before the `14:15 Europe/Berlin` ECB-fix boundary. It keeps the 612
dates selected ex ante by the killed price-pressure object, but changes the
decision input from price/VIX proxies to contemporaneous exchange-book flow.
It remains a futures proxy, not EBS spot dealer flow.

Future source acquisition, if authorized, would still be outcome-blind. It
must first establish nonempty coverage, timestamp/contract continuity and a
causal signed OFI feature. Only a later independently preregistered economic
probe could join that feature to post-fix returns.

## Free vendor quote

| Field | Result |
|---|---:|
| Dataset / schema | `GLBX.MDP3` / `mbp-10` |
| Symbol | `6E.v.0` continuous |
| Requests | 612 / 612 |
| Window per request | 30 seconds |
| Estimated vendor cost | USD 2.010802611691 |
| Estimated billable bytes | 4,318,165,728 |
| Estimated GiB | 4.022 |
| `metadata.get_cost` | 612 |
| `metadata.get_billable_size` | 612 |
| Timeseries / batch / paid calls | 0 / 0 / 0 |

All request IDs are unique, every UTC interval is exactly 30 seconds, DST
conversion is tested and totals reconcile to the 612 child quotes. No API key
was persisted and `outcome_fields_used=[]`.

## Storage and safety gate

Because the quote exceeds the 1 GiB batch threshold, the required storage
checks were run before any purchase:

- AlphaFactory inventory: 10,261 files, 5,806,464,512 bytes; orphan estimate
  257,022,846 bytes; possible mirror estimate 6,669,194 bytes.
- Workspace hygiene dry-run: zero root-sample and zero stale-worktree
  candidates; no execution/deletion was performed.
- `D:` free space at quote time: 405.12 GiB, so capacity is sufficient.

## Authority boundary and next gate

The smallest useful paid step is the exact 612-window acquisition quoted here,
not a continuous feed. Required new authority:

- maximum USD ceiling at least `2.010802611691`, with prudent headroom for the
  mandatory live re-quote before the first paid call;
- explicit binding to `HYP-EURFXOFI-EURUSD-M1-001`, the quote receipt SHA and
  the exact 612 windows;
- no automatic retry of any charged missing/empty response;
- D-side storage only, download manifest and full DBN validation.

Acquisition success would be source-valid only. It would not authorize an EA,
backtest, optimization, promotion, paper or live trading.

## Bound evidence

- Plan SHA256: `91E6A9FABCCB3449BD02B2354DE7872CBBEBB3644BFDD8AD7C962A0F24434A82`
- Quote tool SHA256: `707311A9A6B47C78DD91549D2269446CB45CF4B12AF646A33C111583DF8FE762`
- Tool test SHA256: `5C9BAC3168D68AD9AC00ED1E04FDB7986B107C531343D515C01FE3264215E9AD`
- Quote receipt SHA256: `07B20D56B521ADEAAD0FB25848D8C429FF47DF4514162C160F9ABF874CE8B4D1`
- Storage inventory SHA256: `C8EDBCA736279DF0119BBCCA2C6A0C6542CB0C3FE0454D208CD0B23AC16C47F3`
