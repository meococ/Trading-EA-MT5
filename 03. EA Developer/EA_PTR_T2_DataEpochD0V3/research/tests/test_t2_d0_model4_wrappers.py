from __future__ import annotations

import importlib.util
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]


def _load(name: str):
    path = RESEARCH / name
    spec = importlib.util.spec_from_file_location(name.removesuffix(".py"), path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_model4_packet_builder_freezes_new_identity() -> None:
    source = (RESEARCH / "build_t2_d0_model4_task_packets.py").read_text(encoding="utf-8")
    assert 'builder.HYPOTHESIS_ID = "HYP-PTR-T2-DATA-EPOCH-D0-M5-004"' in source
    assert 'builder.AUTHORITY = "DATA_ACQUISITION_ONLY_NO_PERFORMANCE"' in source
    assert "builder.MODEL = 4" in source
    assert "88F6281385DED567E05B23BB6347F2A91B768C8B5653DAC394751D06003901C8" in source


def test_model4_rebind_wrapper_freezes_new_identity() -> None:
    module = _load("rebind_t2_d0_model4_packet_identity.py")
    assert module.CORE.HYPOTHESIS_ID == "HYP-PTR-T2-DATA-EPOCH-D0-M5-004"
    assert module.CORE.AUTHORITY == "DATA_ACQUISITION_ONLY_NO_PERFORMANCE"
    assert module.CORE.MODEL == 4


def test_model4_rebind_wrapper_uses_strict_real_tick_mode_line() -> None:
    module = _load("rebind_t2_d0_model4_packet_identity.py")
    exact = (
        "CS\t0\t07:55:31.561\tTester\tXAUUSD,M5 "
        "(FivePercentOnline-Real): generating based on real ticks\n"
    )
    assert module.CORE.model4_mode_errors(
        exact,
        symbol="XAUUSD",
        period="M5",
        server="FivePercentOnline-Real",
    ) == []
    assert module.CORE.model4_mode_errors(
        "Tester: real ticks cache warmed\n",
        symbol="XAUUSD",
        period="M5",
        server="FivePercentOnline-Real",
    )
    assert module.CORE.model4_mode_errors(
        exact
        + "CS\t0\t07:55:31.562\tTester\tXAUUSD,M5 "
        "(FivePercentOnline-Real): every tick generated from M1 bars\n",
        symbol="XAUUSD",
        period="M5",
        server="FivePercentOnline-Real",
    )
    for wrong_line in (
        "CS\t0\t07:55:31.561\tTester\tEURUSD,M5 "
        "(FivePercentOnline-Real): generating based on real ticks\n",
        "CS\t0\t07:55:31.561\tTester\tXAUUSD,M15 "
        "(FivePercentOnline-Real): generating based on real ticks\n",
        "CS\t0\t07:55:31.561\tTester\tXAUUSD,M5 "
        "(WrongServer): generating based on real ticks\n",
        "Tester: XAUUSD,M5 (FivePercentOnline-Real): generating based on real ticks\n",
    ):
        assert module.CORE.model4_mode_errors(
            wrong_line,
            symbol="XAUUSD",
            period="M5",
            server="FivePercentOnline-Real",
        )
