# Sonic Rules Matrix

## Core doctrine
| Theme | Sonic / forum doctrine | EA mapping |
| --- | --- | --- |
| Core setup | `Classic` is the core Sonic trade. | `SNR_MODE_CLASSIC` is the only base entry. |
| Session | London is the preferred entry session; New York can work but is secondary. | Router only trades inside configured London / New York windows, with current `EURUSD` work starting from London-first. Plus-suffix symbols are historical E8 context only. |
| Dragon | Wait for a steep Dragon angle. Avoid flat, low-volume chop. | `dragon_slope_atr` must clear `InpMinDragonSlopeATR`. |
| Trend side | Price should be on the right side of Dragon and better still the Trend line. | Context requires price above/below Dragon mid and Trend before `Classic` can fire. |
| Wave | A proper price-action wave must cross the Dragon, then break out. | `Classic` requires pullback into Dragon plus breakout of recent swing high/low. |
| Re-entry | Re-entry is allowed, but only after the original setup and only once the retrace is complete and broken again. | `REENTRY` is available only when a live `Classic` narrative already exists and there is a fresh breakout after retrace. |
| Scout | Scout is higher-risk and should be very light. | `SCOUT2` is capped to one extra same-bias layer and uses the smaller second-layer risk budget. |
| PVSRA | PVSRA helps qualify `Classic` and `Scout`; it is not a direct trigger by itself. | PVSRA grade changes ranking and vetoes weak add-ons, but never fires a trade without structure. |
| Whole / half numbers | Whole and half numbers matter as Sonic S&R. | Context marks `level_zone` and scores setups near whole / half levels. |
| News | Avoid trading blindly into event risk. | Snapshot calendar blocks entries and can force-flat before scheduled news. |
| Discipline | Do not build endless campaigns. | Max `2` layers total, no overnight, no weekend. |

## Implementation notes
- `CLASSIC` is intentionally conservative. It wants Dragon slope, trend-side alignment, a Dragon touch, and a real breakout.
- `REENTRY` is stricter than the first entry. It must inherit a valid `Classic` narrative and break after the retrace, not during it.
- `SCOUT2` is not the old discretionary Sonic multi-add. Here it is a capped second layer with tighter RR and stronger PVSRA requirement.
- `tick volume` is only used as a local activity proxy. It cannot trigger a trade without price structure.

## Research sources
- Post #1, Sonic R. System thread: [forexfactory.com/thread/114792-sonic-r-system](https://www.forexfactory.com/thread/114792-sonic-r-system)
- `Classic` remains the original unchanged setup and is London-centric: [post 28455](https://www.forexfactory.com/thread/post/5168443)
- Proper entry requires steep Dragon and a wave breakout, not top/bottom picking: [post 7865625 / page 3938 excerpt](https://www.forexfactory.com/thread/post/8044523)
- Re-entry needs extra care and HTF / PPZ awareness: [post 2793](https://www.forexfactory.com/thread/post/2729269)
- PVSRA is a qualifier, not an entry engine: [thread post #1 PVSRA note](https://www.forexfactory.com/thread/114792-sonic-r-system)
