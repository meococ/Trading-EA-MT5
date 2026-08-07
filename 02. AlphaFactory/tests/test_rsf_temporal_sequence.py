from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EA = (
    ROOT
    / "03. EA Developer"
    / "EA_RegimeStructureFusion"
    / "EA_RegimeStructureFusion.mq5"
)


def source() -> str:
    return EA.read_text(encoding="utf-8-sig")


def test_sequence_is_opt_in_and_uses_closed_bar_age() -> None:
    text = source()
    assert "input bool   InpUseTemporalSequence=false" in text
    assert "g_armed_bar_time=g_last_bar_time" in text
    assert "age>=InpSequenceMinConfirmBars" in text
    assert "age>InpSequenceExpiryBars" in text
    assert "BuildTemporalDecision(snapshot,profile,decision)" in text
    assert "CopyBuffer(handle,buffer,1,1,data)" in text
    assert "iClose(_Symbol,PERIOD_M5,1)" in text


def test_arm_path_cannot_submit_on_same_bar() -> None:
    text = source()
    body = re.search(
        r"bool BuildTemporalDecision\(.*?\n  \}(?=\n\nbool SubmitEntry)",
        text,
        flags=re.S,
    )
    assert body is not None
    sequence = body.group(0)
    assert "ArmTemporalSetup(setup,s); return(false);" in sequence
    assert "Opposite event becomes a fresh arm, never a same-bar entry" in sequence
    assert "ClearTemporalArm(); return(true);" in sequence


def test_preregistered_location_and_runway_constants_are_explicit() -> None:
    text = source()
    for frozen in (
        "InpSequenceMinConfirmBars=1",
        "InpSequenceExpiryBars=3",
        "InpTrendMaxBasisDistanceHalfWidths=0.75",
        "InpBreakoutMaxExtensionAtr=0.35",
        "InpMinBandRunwayR=0.75",
    ):
        assert frozen in text
    assert "s.close_price-s.mbb_upper<=InpBreakoutMaxExtensionAtr*s.tb_atr" in text
    assert "room/risk+1e-12>=InpMinBandRunwayR" in text
