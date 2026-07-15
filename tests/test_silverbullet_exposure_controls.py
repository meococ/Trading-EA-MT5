from pathlib import Path


SOURCE = (
    Path(__file__).resolve().parents[1]
    / "03. EA Developer"
    / "EA_SilverBullet"
    / "EA_SilverBullet_v2.mq5"
)


def _source() -> str:
    return SOURCE.read_text(encoding="utf-8-sig")


def test_exposure_controls_are_opt_in_with_frozen_defaults() -> None:
    source = _source()

    assert "input bool   InpUseWeekendFlat = false;" in source
    assert "input int    InpFridayFlatHour = 21;" in source
    assert "input int    InpFridayFlatMinute = 45;" in source
    assert "input bool   InpUseMaxHold = false;" in source
    assert "input int    InpMaxHoldHours = 30;" in source


def test_exposure_exit_gate_precedes_holiday_and_day_filters() -> None:
    source = _source()
    on_tick = source[source.index("void OnTick()") : source.index("ENUM_KZ_TYPE GetCurrentKZ")]

    new_bar = on_tick.index("if(barTime == lastBar) return;")
    exposure_gate = on_tick.index("ManageExposureControls")
    holiday_gate = on_tick.index("IsMarketHoliday()")
    bars_gate = on_tick.index("if(Bars(_Symbol, PERIOD_M15) < 50) return;")
    day_gate = on_tick.index("if(dow == 0 || dow == 6) return;")

    assert new_bar < exposure_gate < holiday_gate < bars_gate < day_gate


def test_max_hold_uses_position_open_time_and_weekend_gate_blocks_reentry() -> None:
    source = _source()

    assert "g_pos.Time()" in source
    assert "long maxHoldSeconds = (long)InpMaxHoldHours * 3600;" in source
    assert "heldSeconds >= maxHoldSeconds" in source
    assert "PositionSelectByTicket(ticket)" in source
    assert "Friday cutoff active; entries blocked" in source
