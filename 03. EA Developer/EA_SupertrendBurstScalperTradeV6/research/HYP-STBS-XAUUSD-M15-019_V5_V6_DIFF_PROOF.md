# HYP019 V5 to V6 bounded diff proof

The V6 source was mechanically copied from frozen V5 source SHA256
`3822EED82C8D484CE8010A496767271DED20528158D68509B46EF934B043D918`.

The only source changes are:

- property version/description;
- package EA name;
- hypothesis ID, variant tag and magic;
- telemetry default `false -> true`;
- OnInit guard `audit=true/telemetry=false -> audit=false/telemetry=true`.

Normalizing those exact tokens from V6 back to V5 must reproduce the V5 source
byte-for-byte. Signal, indicator, design-window, entry/exit, risk, margin,
persistence, lifecycle reconciliation and OrderSend functions are unchanged.
