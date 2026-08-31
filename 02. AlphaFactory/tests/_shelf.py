"""Locate an EA package whether it is on the live shelf or parked.

On 2026-08-31 the shelf was cut from 96 packages to 2 (the GOAL host
`EA_SonicR_PVSRA` plus `EA_ExecutionKernelHarness`); everything else moved to
`00. Old File/EA_Archive/`. Parking is housekeeping, not an economic verdict --
the frozen research contracts inside those packages are still the evidence a
test is asserting against, so tests resolve a package from either location.

A test that genuinely requires a package to be *live* on the shelf should read
`03. EA Developer/` directly instead of using this helper.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["REPO_ROOT", "SHELF", "GRAVEYARD", "ea_package", "ea_file"]

REPO_ROOT = Path(__file__).resolve().parents[2]
SHELF = REPO_ROOT / "03. EA Developer"
GRAVEYARD = REPO_ROOT / "00. Old File" / "EA_Archive"


def ea_package(name: str) -> Path:
    """Return the package directory, preferring the live shelf.

    Falls back to the parked copy. If neither exists the shelf path is
    returned so the caller fails with a path that names the live location.
    """
    live = SHELF / name
    if live.is_dir():
        return live
    parked = GRAVEYARD / name
    if parked.is_dir():
        return parked
    return live


def ea_file(name: str, *parts: str) -> Path:
    """Return a file inside an EA package, shelf-or-parked."""
    return ea_package(name).joinpath(*parts)
