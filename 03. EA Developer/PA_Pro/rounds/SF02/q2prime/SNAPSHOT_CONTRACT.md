# Snapshot contract used by Q2' drafts (pre-P-FREEZE stand-in)

The real Snapshot API lives in research/perception (PERCEPTION lane,
not yet frozen). Until P-FREEZE these drafts consume a minimal dict
that mirrors spec §2/§4; when the API freezes, only fixture
construction changes — detector logic is written against these fields.

    snap = {
      "t": int,                       # bar index (closed bar)
      "o","h","l","c": np.ndarray,    # causal bar arrays (<= t)
      "ema25": np.ndarray, "abr": float (pips), "pip": float,
      "utc_min": int, "dow": int,
      "pressure": {"state": "UP"|"DOWN"|"NEUTRAL", "conf": float},
      "objects": [ {
          "id": int, "type": "BOX"|"PATTERN_LINE"|"MINI_LEVEL"|
                  "LEVEL_CARRIED"|"SQUEEZE"|"RANGE_OPEN"|...,
          "lo": float, "hi": float,           # horizontal objects
          "a": float, "b": float,             # line: px = a*t + b
          "t_birth": int, "t_left": int, "t_right": int|None,
          "state": "live"|"broken"|"consumed"|"pierced",
          "role": str|None, "touches": [...], "events": [...],
          "why": str } ],
      "facts": {
          "obstacles_up": [{"px": float, "kind": str, "dist_pips": f}],
          "obstacles_dn": [...],
          "break_class": {"obj_id": int, "cls": "proper"|"tease"|"false"}|None,
          "squeeze": {"obj_ids": [...]}|None,
          "tf": {edge_id: ["T","F",...]},
          "stand_aside": [reasons],
          "first_pullback": bool|None,
          "ema_retouch_count": int|None,
      },
    }
