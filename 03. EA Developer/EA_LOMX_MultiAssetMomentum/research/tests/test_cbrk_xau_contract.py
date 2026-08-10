import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
EA_ROOT = ROOT / "03. EA Developer" / "EA_LOMX_MultiAssetMomentum"
SOURCE = EA_ROOT / "research" / "source_snapshots" / "EA_LOMX_MultiAssetMomentum_D363121DC7FFCB12.mq5"
PREREG = EA_ROOT / "research" / "HYP-CBRK-XAUUSD-M5-001_FROZEN_PREREG.md"
STAGE0 = (
    EA_ROOT
    / "research"
    / "evidence"
    / "HYP-LOMX-DESIGN-M5-002"
    / "P0_DESIGN_001"
    / "stage0_result.json"
)
DATA_RUN = (
    ROOT
    / "02. AlphaFactory"
    / "runs"
    / "EA_PTR_T2_DataEpochD0V3"
    / "20260731_075527"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_frozen_source_and_parent_evidence_hashes() -> None:
    assert sha256(SOURCE) == "D363121DC7FFCB128A67C796B76F8B86C8AB2262FF045EAC62B49FE19FB3298B"
    assert sha256(STAGE0) == "8193E68D4EC240B696CDB91884C95976F3B47ECFFF740D5416BE2BEB4D2EF1DB"


def test_mql_breakout_contract_is_exact_and_sweep_is_inert_in_mode_one() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    required = [
        "const double BREAKOUT_CONTRACTION_RATIO=0.70;",
        "const double BREAKOUT_BUFFER_ATR_MULT=0.20;",
        "const double BREAKOUT_STOP_ATR_MULT=0.10;",
        "const double BREAKOUT_TARGET_R=2.0;",
        "for(int i=2;i<=51;i++)",
        "double bar2_range=rates[1].high-rates[1].low;",
        "for(int i=1;i<=15;i++)",
        "for(int i=1;i<=InpVolumeLookback;i++)",
        "if((double)rates[0].tick_volume<=prior_volume_mean)",
        "if(rates[0].close>box_high+BREAKOUT_BUFFER_ATR_MULT*atr)",
        "signal.stop=box_low-BREAKOUT_STOP_ATR_MULT*atr;",
        "if(rates[0].close<box_low-BREAKOUT_BUFFER_ATR_MULT*atr)",
        "signal.stop=box_high+BREAKOUT_STOP_ATR_MULT*atr;",
        "if(InpEngineMode==ENGINE_SWEEP || InpEngineMode==ENGINE_BOTH)",
        "if(InpEngineMode==ENGINE_BREAKOUT || InpEngineMode==ENGINE_BOTH)",
    ]
    for anchor in required:
        assert anchor in source


def test_stage0_xau_atomic_cell_is_balanced_and_split_cadence_is_in_band() -> None:
    stage0 = json.loads(STAGE0.read_text(encoding="utf-8"))
    cell = stage0["atomic_cells"]["XAUUSD__BAR_RANGE_COMPRESSION_BREAKOUT"]
    assert cell["pass"] is True
    assert cell["candidate_count"] == 2072
    assert cell["direction_counts"] == {"long": 1117, "short": 955}
    assert cell["year_counts"] == {
        "2016": 263,
        "2017": 233,
        "2018": 235,
        "2019": 270,
        "2020": 258,
        "2021": 234,
        "2022": 198,
        "2023": 187,
        "2024": 194,
    }
    assert 2.0 <= sum(cell["year_counts"][str(y)] for y in range(2018, 2023)) / (1824 / 7) <= 5.0
    assert 2.0 <= cell["year_counts"]["2023"] / (365 / 7) <= 5.0
    assert 2.0 <= cell["year_counts"]["2024"] / (366 / 7) <= 5.0


def test_later_zero_trade_xau_m5_population_evidence_is_full_2018_plus() -> None:
    manifest_path = DATA_RUN / "run_manifest.json"
    report_path = DATA_RUN / "report.html"
    assert sha256(manifest_path) == "EA138F8971BA5552674316BB4D296D486E0813095F7E140C78531DECB9293476"
    assert sha256(report_path) == "263F7D9E665556E1D2D8EE1FB492F74805C7646C742D552455221422B078FC37"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    dq = manifest["data_quality_gate"]
    assert manifest["symbol"] == "XAUUSD"
    assert manifest["model"] == 0
    assert dq["history_quality"] == 98
    assert dq["coverage_class"] == "FULL_2018_PLUS"
    assert dq["actual_from"] == "2004.06.11"
    assert dq["actual_to"] == "2026.07.30"
    assert dq["journal_truncated"] is False
    assert dq["series_proof"]["copytime_result"] == 1
    assert dq["series_proof"]["copytime_first_epoch"] == dq["series_proof"]["m5_first_epoch"]
    report = report_path.read_text(encoding="utf-16", errors="ignore")
    if "1485698" not in report:
        report = report_path.read_text(encoding="utf-8", errors="ignore")
    assert "1485698" in report
    assert "771168477" in report


def test_prereg_discloses_adverse_prior_and_forbids_rescue() -> None:
    prereg = PREREG.read_text(encoding="utf-8")
    assert "PF `0.7466504499`" in prereg
    assert "not permission to change a threshold" in prereg
    assert "No optimization and no same-ID rerun" in prereg
    assert "Missing fill slippage is not zero" in prereg
    assert "InpEngineMode=1" in prereg
