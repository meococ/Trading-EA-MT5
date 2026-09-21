"""R02-A F10 lock: `run_counts.py` uses the Addendum-2 control signature."""

import inspect
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PHYS = os.path.dirname(HERE)
if PHYS not in sys.path:
    sys.path.insert(0, PHYS)


def test_extract_controls_signature_is_addendum2():
    from phys_controls import extract_controls

    params = list(inspect.signature(extract_controls).parameters)
    assert params == ["events", "src", "ref", "bars", "symbol"], params


def test_run_counts_source_calls_new_signature():
    path = os.path.join(PHYS, "run_counts.py")
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    assert "extract_controls(ev, srcs[name], ref, ctx.bars," in src
    assert "r5_cap=" not in src
    assert "StructureIndex" not in src
