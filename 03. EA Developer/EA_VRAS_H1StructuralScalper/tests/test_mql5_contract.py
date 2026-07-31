import os
import re
import pytest

EA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MQ5_FILE = os.path.join(EA_DIR, "EA_VRAS_H1StructuralScalper.mq5")
CONTRACT_FILE = os.path.join(EA_DIR, "ALPHAFACTORY_EA_CONTRACT.json")

def test_mq5_file_exists():
    assert os.path.exists(MQ5_FILE), f"Missing {MQ5_FILE}"

def test_contract_file_exists():
    assert os.path.exists(CONTRACT_FILE), f"Missing {CONTRACT_FILE}"

def test_closed_bar_non_repaint_contract():
    with open(MQ5_FILE, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    assert "iTime" in content, "MQ5 must check bar time to enforce closed-bar evaluation"
    assert "PERIOD_H1" in content, "MQ5 must inspect H1 timeframe for structural bias"
    assert "InpRiskPercent" in content, "MQ5 must define risk percent parameter"
    assert "InpHypothesisId" in content, "MQ5 must declare hypothesis ID input"

if __name__ == "__main__":
    pytest.main([__file__])
