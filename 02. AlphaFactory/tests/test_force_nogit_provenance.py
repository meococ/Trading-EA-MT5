from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGETS = (
    ROOT / "alpha.ps1",
    ROOT / "tools" / "research_loop_engine.ps1",
)


def _test_nogit_function(source: str) -> str:
    marker = "function Test-NoGitWorkspace"
    start = source.index(marker)
    next_function = source.find("\nfunction ", start + len(marker))
    assert next_function > start
    return source[start:next_function]


def test_force_nogit_guard_precedes_every_git_invocation() -> None:
    for path in TARGETS:
        body = _test_nogit_function(path.read_text(encoding="utf-8-sig"))
        guard = body.index("$env:ALPHAFACTORY_FORCE_NOGIT")
        first_git = body.index("& git")
        assert guard < first_git, path
        assert "return $true" in body[guard:first_git]


def test_force_nogit_invalid_value_fails_closed() -> None:
    for path in TARGETS:
        body = _test_nogit_function(path.read_text(encoding="utf-8-sig"))
        assert "-notin @('1', 'true')" in body, path
        assert "ALPHAFACTORY_FORCE_NOGIT must be '1' or 'true'" in body, path
