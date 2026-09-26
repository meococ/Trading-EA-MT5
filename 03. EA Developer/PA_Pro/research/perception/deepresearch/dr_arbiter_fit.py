"""dr_arbiter_fit.py -- DETERMINISTIC stub for the ESCALATE: FIT item.

Goal (fit on a machine where fitting is allowed, Ruling 58): learn a
binary arbiter "use the event-channel pick (keep-last-1) vs fall back
to the structural box@1 pick" maximizing realized golden hits.

Input : deepresearch/arbiter_rows.pkl  (one row per (panel,tau) golden;
        ev_* = features of the freshest event candidate; *_hit = did
        that channel's box@1 hit the golden under eval_v2)
Label : choose event iff expected to hit. Realized score of a policy
        pi(row) = sum( ev_hit if pi else v1_hit ).

Protocol (stated, no tuning on the TUNE labels beyond this):
  1. 5-fold panel-grouped CV (group by 'panel').
  2. Candidate models, all deterministic seeds: logistic regression on
     [ev_exists, ev_age, ev_span, ev_height, ev_leg, ev_prom, ev_pxin,
     ev_bst, ev_ovl, ev_pxfrac, route==rd]; depth<=3 decision tree;
     threshold rules on single features.
  3. Report CV mean hits/119 vs baselines always-event (20) and
     always-v1 (10). Oracle union on this file = 27 (event+v1),
     32 (event+hybrid).
  4. Guard: if CV mean < 24, the arbitration gap is not learnable from
     event-side features -> declare semantic, stop.
Output: prints CV table; writes arbiter_fit_report.txt.
"""
import pickle, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
rows = pickle.load(open(os.path.join(HERE, "arbiter_rows.pkl"), "rb"))


def score(policy):
    return sum(r["ev_hit"] if (r.get("ev_exists") and policy(r))
               else r["v1_hit"] for r in rows)


if __name__ == "__main__":
    print("baselines: always-event", score(lambda r: True),
          "| always-v1", score(lambda r: False))
    print("oracle union:", sum(1 for r in rows
                               if r.get("ev_hit") or r["v1_hit"]))
    print("FIT not run on this PC -- see docstring for protocol.")
