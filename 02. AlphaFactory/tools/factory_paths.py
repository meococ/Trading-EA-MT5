"""Single source of truth for AlphaFactory machine paths, for Python callers.

Why this exists
---------------
`mt5.initialize()` with no arguments attaches to whichever MetaTrader 5
terminal is already running. On the Owner machine that is the GUI terminal the
Owner trades from, not the factory isolate. Every bare call is therefore a
silent retarget: research reads the Owner's history, competes with live
charts, and produces numbers that no other machine can reproduce.

`alpha.ps1` already refuses any compile/backtest target outside
`02. AlphaFactory/runtime/`. This module gives Python the same contract.

Usage
-----
    from tools.factory_paths import mt5_initialize_kwargs
    import MetaTrader5 as mt5

    if not mt5.initialize(**mt5_initialize_kwargs()):
        raise SystemExit(f"MT5 init failed: {mt5.last_error()}")

Nothing here executes PowerShell. `alpha.local.ps1` is parsed as text, so a
malformed or hostile local config cannot run code through this path.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

__all__ = [
    "FactoryPathError",
    "find_repo_root",
    "load_alpha_local",
    "factory_install_root",
    "factory_mt5_terminal",
    "factory_metaeditor",
    "mt5_initialize_kwargs",
]

# A directory is the repo root when it holds all three of these.
_ROOT_MARKERS = ("AGENTS.md", "02. AlphaFactory", "03. EA Developer")

_ASSIGN_RE = re.compile(
    r'^\s*\$(?P<name>MT5[A-Za-z0-9_]*)\s*=\s*"(?P<value>[^"]*)"\s*$'
)
_BOOL_RE = re.compile(
    r'^\s*\$(?P<name>MT5[A-Za-z0-9_]*)\s*=\s*\$(?P<value>true|false)\s*$',
    re.IGNORECASE,
)


class FactoryPathError(RuntimeError):
    """The factory target could not be resolved, or is not an isolate."""


def _is_repo_root(path: Path) -> bool:
    return all((path / marker).exists() for marker in _ROOT_MARKERS)


def find_repo_root(start: Path | str | None = None) -> Path:
    """Walk parents from `start` (default: this file) until the markers match.

    `ALPHAFACTORY_REPO_ROOT` overrides the walk, but only if it also carries
    the markers — an env var may not point at an arbitrary directory.
    """
    override = os.environ.get("ALPHAFACTORY_REPO_ROOT")
    if override:
        candidate = Path(override).expanduser().resolve()
        if not _is_repo_root(candidate):
            raise FactoryPathError(
                f"ALPHAFACTORY_REPO_ROOT={candidate} is not a repo root; "
                f"expected {', '.join(_ROOT_MARKERS)} inside it."
            )
        return candidate

    here = Path(start).resolve() if start else Path(__file__).resolve()
    for directory in (here, *here.parents):
        if directory.is_dir() and _is_repo_root(directory):
            return directory
    raise FactoryPathError(
        f"No repo root above {here}. Expected a directory holding "
        f"{', '.join(_ROOT_MARKERS)}."
    )


def load_alpha_local(repo_root: Path | None = None) -> dict[str, object]:
    """Parse `02. AlphaFactory/alpha.local.ps1` without executing it."""
    root = repo_root or find_repo_root()
    local = root / "02. AlphaFactory" / "alpha.local.ps1"
    if not local.is_file():
        raise FactoryPathError(
            f"Machine pin is missing: {local}\n"
            f'Generate it with:  & ".\02. AlphaFactory\tools\init_machine_paths.ps1"'
        )

    values: dict[str, object] = {}
    for raw in local.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw.split("#", 1)[0]
        match = _ASSIGN_RE.match(line)
        if match:
            values[match.group("name")] = match.group("value")
            continue
        match = _BOOL_RE.match(line)
        if match:
            values[match.group("name")] = match.group("value").lower() == "true"
    return values


def factory_install_root(repo_root: Path | None = None) -> Path:
    """Resolve the pinned portable isolate and assert it really is one."""
    root = repo_root or find_repo_root()
    values = load_alpha_local(root)

    install = values.get("MT5InstallRoot")
    if not install:
        raise FactoryPathError(
            "alpha.local.ps1 does not set $MT5InstallRoot. "
            "Regenerate it with tools/init_machine_paths.ps1."
        )

    install_path = Path(str(install)).resolve()
    runtime = (root / "02. AlphaFactory" / "runtime").resolve()

    # Same rule alpha.ps1 enforces: the factory target lives under runtime/.
    # This is what keeps research off the Owner GUI (e.g. D:\Meta 5) and off
    # %APPDATA%\MetaQuotes\Terminal\<32-hex>.
    if runtime not in install_path.parents and install_path != runtime:
        raise FactoryPathError(
            f"Refusing '{install_path}' as the factory target: it is outside "
            f"'{runtime}'. A terminal64.exe outside that tree is an Owner GUI "
            f"or a foreign install."
        )

    if values.get("MT5PortableMode") is not True:
        raise FactoryPathError(
            f"alpha.local.ps1 must set $MT5PortableMode = $true for "
            f"'{install_path}', otherwise MT5 clones profiles into AppData."
        )

    data = values.get("MT5DataRoot")
    if data and Path(str(data)).resolve() != install_path:
        raise FactoryPathError(
            f"DataRoot must equal InstallRoot. Install='{install_path}' "
            f"Data='{Path(str(data)).resolve()}'."
        )

    return install_path


def factory_mt5_terminal(repo_root: Path | None = None) -> Path:
    terminal = factory_install_root(repo_root) / "terminal64.exe"
    if not terminal.is_file():
        raise FactoryPathError(f"Factory terminal is missing: {terminal}")
    return terminal


def factory_metaeditor(repo_root: Path | None = None) -> Path:
    editor = factory_install_root(repo_root) / "metaeditor64.exe"
    if not editor.is_file():
        raise FactoryPathError(f"Factory MetaEditor is missing: {editor}")
    return editor


def mt5_initialize_kwargs(
    repo_root: Path | None = None, timeout_ms: int = 60_000
) -> dict[str, object]:
    """Keyword arguments that pin `mt5.initialize()` to the factory isolate."""
    return {
        "path": str(factory_mt5_terminal(repo_root)),
        "portable": True,
        "timeout": timeout_ms,
    }
