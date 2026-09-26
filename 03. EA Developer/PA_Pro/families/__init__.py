"""families/ — PA-PRO setup layer (lane SF01).

Detectors emit referee entry dicts (see lib/pa_eval.py): {sig, side, inv,
atr, tag, order_px?}.  Everything here is causal: signals at bar t use only
bars <= t and zone state <= t (the cached zone pass reproduces
``ZoneGen.views_at`` semantics exactly — see sf_ctx.py).
"""
