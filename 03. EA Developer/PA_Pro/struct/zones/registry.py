"""registry.py — the frozen candidate list for the T-PAPRO-ZONE-1 bake-off.

Order is the SHORTLIST order (baseline first).  Modules are imported
explicitly so a broken candidate fails loudly instead of silently
disappearing from the tests/runner.

NOTE: extended as each shortlisted generator lands; the freeze for the
snapshots uses exactly the names returned here.
"""

__all__ = ["import_registry", "names", "get"]


def import_registry():
    from line1_cluster_zones import Line1ClusterZones
    from fractal_zones import FractalZones
    from kde_swing_zones import KdeSwingZones
    from profile_zones import ProfileZones
    from sd_base_zones import SdBaseZones
    from ref_zones import RefZones
    return [
        ("line1_cluster", Line1ClusterZones),
        ("fractal_h1", FractalZones),
        ("kde_swing", KdeSwingZones),
        ("profile_va", ProfileZones),
        ("sd_base", SdBaseZones),
        ("ref_levels", RefZones),
    ]


def names():
    return [n for n, _ in import_registry()]


def get(name):
    for n, cls in import_registry():
        if n == name:
            return cls
    raise KeyError(name)
