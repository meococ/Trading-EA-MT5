"""Round-2C wall test: the loader guard must cover ALL 12 symbols."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from src import data as dm


def test_all_symbols_have_cost_and_pip():
    for s in dm.ALL_SYMBOLS:
        assert s in dm.PIP and s in dm.COST


def test_holdout_guard_all_symbols():
    """Requesting bars past HOLDOUT_START must raise for every symbol."""
    for s in dm.ALL_SYMBOLS:
        with pytest.raises(PermissionError):
            dm.load_m1(s, dm.DESIGN[0], dm.HOLDOUT_START + 3600)


def test_validation_also_guarded_window_end():
    for s in dm.ALL_SYMBOLS:
        with pytest.raises(PermissionError):
            dm.load_m1(s, dm.VALIDATION[0], dm.COMMON_END)
