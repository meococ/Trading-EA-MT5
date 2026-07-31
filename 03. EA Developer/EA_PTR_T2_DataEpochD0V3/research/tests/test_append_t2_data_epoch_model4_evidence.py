from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "append_t2_data_epoch_model4_evidence.py"
SPEC = importlib.util.spec_from_file_location("append_t2_data_epoch_model4_evidence", MODULE_PATH)
assert SPEC and SPEC.loader
SUT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUT)


def test_wrapper_freezes_model4_epoch_identity() -> None:
    assert SUT.CORE.HYPOTHESIS_ID == "HYP-PTR-T2-DATA-EPOCH-D0-M5-004"
    assert SUT.CORE.EA_NAME == "EA_PTR_T2_DataEpochD0V3"
    assert SUT.CORE.MODEL == 4
    assert SUT.CORE.AUTHORITY == "DATA_ACQUISITION_ONLY_NO_PERFORMANCE"
    assert SUT.CORE.EPOCH_SHA256 == "88F6281385DED567E05B23BB6347F2A91B768C8B5653DAC394751D06003901C8"
