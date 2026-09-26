"""Sweep engine: cell -> governed-style stats -> duckdb results store.

Every cell evaluated lands in lab.duckdb (results table) including negatives —
the falsification ledger is the dataset. Cells are deduped by a hash of their
definition, so nothing is ever re-measured.
"""
import hashlib
import json
import os

import duckdb
import numpy as np

import labels
import stats

LAB = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(LAB, "lab.duckdb")

DDL = """
CREATE TABLE IF NOT EXISTS results (
  cell_hash TEXT PRIMARY KEY,
  family TEXT, symbol TEXT, side INT,
  params_json TEXT,
  n_events INT, n_kept INT, dropped INT,
  mean_p DOUBLE, t_stat DOUBLE, p_val DOUBLE, q_val DOUBLE,
  pf DOUBLE, win_rate DOUBLE,
  h1_mean DOUBLE, h2_mean DOUBLE, min_half_t DOUBLE,
  pos_year_frac DOUBLE, per_year_json TEXT,
  exit_mix_json TEXT, mae_med DOUBLE, mfe_med DOUBLE,
  cost_rt DOUBLE, run_at TEXT, sim_version INT,
  verdict TEXT
);
"""


def cell_hash(cell):
    # sim_version participates so a simulator fix re-measures every cell;
    # old-version rows stay in the ledger as falsification history.
    s = json.dumps(cell, sort_keys=True) + f"::sim{labels.SIM_VERSION}"
    return hashlib.sha256(s.encode()).hexdigest()[:16]


class Lab:
    def __init__(self, db=DB):
        self.db = duckdb.connect(db)
        self.db.execute(DDL)
        try:
            self.db.execute(
                "ALTER TABLE results ADD COLUMN sim_version INT")
        except Exception:
            pass

    def done(self, cell):
        h = cell_hash(cell)
        r = self.db.execute("SELECT 1 FROM results WHERE cell_hash=?",
                            [h]).fetchone()
        return r is not None

    def record(self, cell, ev, cost_rt, min_events=60):
        """Compute stats for an eval_events() result and store the row."""
        ret = ev["ret"]
        kept = len(ret)
        t, p = stats.welch_t(ret) if kept >= 30 else (np.nan, np.nan)
        py = stats.per_year(ret, ev["ctm"]) if kept else {}
        m1, m2, min_t = stats.split_half(ret, ev["ctm"]) if kept else (
            np.nan, np.nan, np.nan)
        exits, counts = np.unique(ev["exit"], return_counts=True)
        exit_mix = {e: int(c) for e, c in zip(exits, counts)}
        # invariant: a spec with finite SL/TP must produce non-TIME exits;
        # 100% TIME with sl/tp set once caught a pips-vs-price unit bug.
        if kept and (cell.get("sl") or cell.get("tp")):
            nontime = sum(v for k2, v in exit_mix.items() if k2 != "TIME")
            if nontime == 0 and kept >= 200:
                row_exit = "WARN_ALL_TIME_EXITS"
            else:
                row_exit = None
        else:
            row_exit = None
        pos = [v[0] for v in py.values() if v[1] >= 10]
        pos_frac = (sum(1 for x in pos if x > 0) / len(pos)) if pos else np.nan
        wins = ret[ret > 0]
        row = {
            "cell_hash": cell_hash(cell),
            "family": cell["family"],
            "symbol": cell["symbol"],
            "side": int(cell.get("side", 0)),
            "params_json": json.dumps(cell, sort_keys=True),
            "n_events": int(ev["n_events"]),
            "n_kept": kept,
            "dropped": int(ev["dropped_entry"] + ev["dropped_path"]
                           + ev["dropped_tail"]),
            "mean_p": float(ret.mean()) if kept else np.nan,
            "t_stat": float(t) if t == t else None,
            "p_val": float(p) if p == p else None,
            "q_val": None,
            "pf": float(labels.pf(ret)) if kept else np.nan,
            "win_rate": float(len(wins) / kept) if kept else np.nan,
            "h1_mean": float(m1) if m1 == m1 else None,
            "h2_mean": float(m2) if m2 == m2 else None,
            "min_half_t": float(min_t) if min_t == min_t else None,
            "pos_year_frac": float(pos_frac) if pos_frac == pos_frac else None,
            "per_year_json": json.dumps(py),
            "exit_mix_json": json.dumps(exit_mix),
            "mae_med": float(np.median(ev["mae"])) if kept else np.nan,
            "mfe_med": float(np.median(ev["mfe"])) if kept else np.nan,
            "cost_rt": float(cost_rt),
            "run_at": __import__("datetime").datetime.utcnow().isoformat(),
            "sim_version": int(ev.get("sim_version", labels.SIM_VERSION)),
            "verdict": row_exit,
        }
        cols = ",".join(row.keys())
        ph = ",".join(["?"] * len(row))
        self.db.execute(
            f"INSERT OR REPLACE INTO results ({cols}) VALUES ({ph})",
            list(row.values()))
        # mirror to append-only CSV so progress is readable while the
        # duckdb writer lock is held
        import csv as _csv
        csvp = os.path.join(LAB, "results_log.csv")
        new = not os.path.exists(csvp)
        with open(csvp, "a", newline="") as f:
            w = _csv.DictWriter(f, fieldnames=list(row.keys()))
            if new:
                w.writeheader()
            w.writerow(row)
        return row

    def apply_fdr(self, family=None):
        """Recompute BH q-values over stored p-values (per family or all).
        Restricted to the current sim_version — stale-version rows are
        history, not evidence."""
        w = (f"WHERE sim_version={labels.SIM_VERSION}"
             + (f" AND family='{family}'" if family else ""))
        df = self.db.execute(
            f"SELECT cell_hash,p_val FROM results {w}").df()
        q = stats.bh_fdr(df["p_val"].to_numpy())
        for h, qv in zip(df["cell_hash"], q):
            if qv == qv:
                self.db.execute("UPDATE results SET q_val=? WHERE cell_hash=?",
                                [float(qv), h])

    def survivors(self, family=None, t_min=2.8, pf_min=1.3,
                  min_kept=120, pos_frac=0.6):
        w = f"AND family='{family}'" if family else ""
        return self.db.execute(f"""
          SELECT symbol, side, params_json, n_kept, mean_p, t_stat, q_val,
                 pf, win_rate, pos_year_frac, min_half_t
          FROM results
          WHERE sim_version={labels.SIM_VERSION}
            AND n_kept>={min_kept} AND t_stat>={t_min} AND pf>={pf_min}
            AND pos_year_frac>={pos_frac} AND min_half_t>0 {w}
          ORDER BY t_stat DESC""").df()

    def close(self):
        self.db.close()
