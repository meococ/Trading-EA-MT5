# DR2_VARIANTS — cadence + recall on the 60 BURNED cases

DESIGN weeks (span): 312.7. Census baseline: exec=1, 0.0032/week. E3: this set is BURNED; counts here are diagnostic, never fidelity. E4: no outcomes.

| variant | exec | /week | AB iv | AB iii | AB ii | AB i | C iv | C iii | C ii | C i |
|---|---|---|---|---|---|---|---|---|---|---|
| DR1 | 1 | 0.0032 | 0 | 4 | 11 | 1 | 0 | 19 | 15 | 10 |
| V1_signal_lo_0.50 | 1 | 0.0032 | 0 | 11 | 4 | 1 | 0 | 30 | 4 | 10 |
| V2_V1_room_sig | 1 | 0.0032 | 0 | 11 | 4 | 1 | 0 | 30 | 4 | 10 |
| V3_V2_buildup_2of4 | 2 | 0.0064 | 0 | 11 | 4 | 1 | 0 | 30 | 4 | 10 |
| DR2a_sig_sess | 3 | 0.0096 | 0 | 11 | 4 | 1 | 0 | 30 | 4 | 10 |
| DR2b_a_room_sig | 3 | 0.0096 | 0 | 11 | 4 | 1 | 0 | 30 | 4 | 10 |
| DR2c_b_prev_bar | 4 | 0.0128 | 0 | 15 | 0 | 1 | 0 | 34 | 0 | 10 |
| DR2d_c_buildup_2of4 | 4 | 0.0128 | 0 | 15 | 0 | 1 | 0 | 34 | 0 | 10 |
| DR2e_trend_only_bound | 5528 | 17.678 | 10 | 5 | 0 | 1 | 8 | 26 | 0 | 10 |

Funnel counters per variant:

| variant | signal_eval | skip_trend | skip_room | skip_no_buildup | skip_chop | skip_direction | skip_anti_chase | skip_adverse_magnet | skip_session | skip_missed_break | chop_exempt_buildup |
|---|---|---|---|---|---|---|---|---|---|---|---|
| DR1 | 19957 | 2752 | 779 | 635 | 284 | 202 | 26 | 2 | 15276 | 23067 | 278 |
| V1_signal_lo_0.50 | 75154 | 9763 | 2227 | 2142 | 941 | 2466 | 58 | 3 | 57553 | 23067 | 731 |
| V2_V1_room_sig | 75154 | 9763 | 2241 | 2142 | 941 | 2466 | 42 | 5 | 57553 | 23067 | 731 |
| V3_V2_buildup_2of4 | 75152 | 9763 | 5182 | 69 | 27 | 2466 | 78 | 12 | 57553 | 23066 | 1645 |
| DR2a_sig_sess | 75148 | 17918 | 4024 | 3663 | 1650 | 4415 | 102 | 8 | 43365 | 23065 | 1299 |
| DR2b_a_room_sig | 75148 | 17918 | 4047 | 3663 | 1650 | 4415 | 78 | 9 | 43365 | 23065 | 1299 |
| DR2c_b_prev_bar | 98213 | 22389 | 4647 | 4785 | 2068 | 9007 | 85 | 9 | 55219 | 23064 | 1474 |
| DR2d_c_buildup_2of4 | 98210 | 22389 | 11141 | 164 | 63 | 9007 | 189 | 34 | 55219 | 23064 | 3479 |
| DR2e_trend_only_bound | 89541 | 21616 | 0 | 0 | 0 | 6610 | 0 | 1228 | 54559 | 19374 | 2038 |