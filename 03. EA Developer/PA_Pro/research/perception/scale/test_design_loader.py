"""test_design_loader.py — the data wall must hold (R37 §37.3).

Run:  python scale/test_design_loader.py
Checks:
  1. refuses a window touching 2015-12-31 (CONFIRM-PRE side);
  2. refuses a window touching 2022-01-03 (CONFIRM-VAL side);
  3. refuses a non-SCALE symbol;
  4. refuses when an outcome module is loaded in the process;
  5. accepts 2016-01-04 (first Monday of the window) and returns M5 bars
     whose CET dates are all 2016-01-04.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import design_loader as DL                       # noqa: E402


def expect_raise(fn, what):
    try:
        fn()
    except DL.DesignWallError as ex:
        print("  ok  refused %-28s (%s)" % (what, str(ex)[:80]))
        return
    raise AssertionError("NOT refused: " + what)


def main():
    print("design_loader wall tests")

    # 1-2. window edges: the day before and the day after the window
    expect_raise(lambda: DL.load_m5("EURUSD", "2015-12-31 00:00",
                                    "2015-12-31 23:59"),
                 "2015-12-31 (CONFIRM-PRE)")
    expect_raise(lambda: DL.load_m5("EURUSD", "2022-01-03 00:00",
                                    "2022-01-03 23:59"),
                 "2022-01-03 (CONFIRM-VAL)")
    expect_raise(lambda: DL.load_m5("EURUSD", "2021-12-30 00:00",
                                    "2022-01-04 23:59"),
                 "window straddling 2022 boundary")
    # 3. symbol wall
    expect_raise(lambda: DL.load_m5("USDCNH", "2016-01-04 00:00",
                                    "2016-01-04 23:59"),
                 "USDCNH (not a SCALE symbol)")
    # 4. outcome module loaded
    sys.modules["pa_eval"] = object()
    expect_raise(lambda: DL.load_m5("EURUSD", "2016-01-04 00:00",
                                    "2016-01-04 23:59"),
                 "pa_eval loaded in process")
    del sys.modules["pa_eval"]

    # 5. a real in-window day loads
    b = DL.load_m5("EURUSD", "2016-01-04 00:00", "2016-01-04 23:55")
    assert len(b["t"]) > 200, "expected a full day of M5 bars"
    import numpy as np
    cet_days = np.unique(b["cet"] // 86400)
    assert len(cet_days) == 1 and \
        cet_days[0] == 16804, cet_days      # 2016-01-04 CET epoch day
    # end-exclusive window: the last complete M5 group is 23:50
    # (the 23:55 group needs server bars past the cut and is dropped).
    assert b["cet_min"][0] == 0 and b["cet_min"][-1] == 1430
    print("  ok  2016-01-04 loads: %d M5 bars, CET %02d:%02d-%02d:%02d, "
          "dropped=%d" % (len(b["t"]),
                          b["cet_min"][0] // 60, b["cet_min"][0] % 60,
                          b["cet_min"][-1] // 60, b["cet_min"][-1] % 60,
                          b["dropped"]))
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
