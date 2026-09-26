
import sys
class F:
    def find_module(self, name, path=None):
        leaf = name.split(".")[-1]
        if leaf in {"pa_eval","pa_fill","pa_random","arrival_outcome","phys_resolve"}:
            import traceback; traceback.print_stack()
        return None
sys.meta_path.insert(0, F())
import pytest
pytest.main(["tests/test_book_loader.py::test_loads_book_slice","-x","-q","-p","no:cacheprovider"])
