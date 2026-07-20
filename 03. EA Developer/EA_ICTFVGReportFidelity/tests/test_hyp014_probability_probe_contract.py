import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[1]
PLAN = ROOT / "research" / "HYP-ICT-FVG-PROB-RANK-EURUSD-M5-014_PROBE_PLAN.md"
SCRIPT = ROOT / "research" / "run_hyp014_probability_probe.py"
INPUT = (
    WORKSPACE
    / "02. AlphaFactory"
    / "runtime"
    / "ictfvg_hyp012_context_forensics"
    / "positions_with_context.csv"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_hyp014_plan_and_input_are_hash_bound() -> None:
    assert sha256(PLAN) == "A814148BFCDFFDE12F1DA49A7BF3A8C79379FEA753BEA626C248DACA4FC9AED2"
    assert INPUT.stat().st_size == 2_580_003
    assert sha256(INPUT) == "1661ECE481CC1D52BE7751F445602ECE79AC1CA1F6F92AA6C2BF28594645B5B6"


def test_model_and_trial_budget_match_the_frozen_contract() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    for token in (
        'C=0.1',
        'solver="liblinear"',
        'max_iter=2000',
        'random_state=SEED',
        'np.quantile(train_scores, 0.60, method="linear")',
        'BOOTSTRAP_SAMPLES = 10_000',
        '"trial_count": 1',
    ):
        assert token in text


def test_expanding_years_and_no_trade_denominator_are_explicit() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'train = data[data["entry_year"] < year]' in text
    assert 'test = data[data["entry_year"] == year]' in text
    assert 'frame[f"policy_r_{label}"] = frame[f"r_{label}"] * frame["accepted"]' in text
    assert 'metrics[f"r_per_opportunity_{label}"] = float(policy_returns.mean())' in text


def test_outcomes_are_targets_only_and_not_model_features() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    feature_block = text.split("BASE_FEATURES = [", 1)[1].split("]", 1)[0]
    for forbidden in ("r_gross", "r_net", "exit", "commission", "entry_year"):
        assert forbidden not in feature_block

