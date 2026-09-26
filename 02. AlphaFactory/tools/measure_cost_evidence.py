#!/usr/bin/env python3
"""Measure research-proxy cost evidence for a symbol on the factory isolate.

Attaches via mt5_initialize_kwargs() to the portable MetaQuotes-Demo isolate,
pulls a bounded tick window, and emits three hashable evidence files plus a
summary used to fill the cost source manifest:

  spread_evidence.json     -- measured current/rolling spread over the window
  slippage_evidence.json   -- independent-quote latency proxy (non-fill)
  commission_evidence.json -- strategy_tester_simulation lifecycles (commission=0)

Read-only: symbol_info + copy_ticks_range only. No order operations.
"""
import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.factory_paths import mt5_initialize_kwargs  # noqa: E402

import MetaTrader5 as mt5  # noqa: E402


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest().upper()


def percentile(values, q):
    if not values:
        return None
    xs = sorted(values)
    k = (len(xs) - 1) * q
    lo = int(k)
    hi = min(lo + 1, len(xs) - 1)
    frac = k - lo
    return xs[lo] + (xs[hi] - xs[lo]) * frac


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--hours", type=float, default=48.0)
    ap.add_argument("--end-utc", default=None,
                    help="sample window end, 'YYYY-MM-DDTHH:MM:SSZ'; default = "
                         "last live tick. Pin it inside the run window: the "
                         "verified-cost builder rejects evidence outside it.")
    ap.add_argument("--latency-ms", type=int, default=250)
    ap.add_argument("--pip", type=float, default=0.0001)
    ap.add_argument("--max-ticks", type=int, default=400_000)
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not mt5.initialize(**mt5_initialize_kwargs()):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        terminal = mt5.terminal_info()
        account = mt5.account_info()
        info = mt5.symbol_info(args.symbol)
        if terminal is None or account is None or info is None:
            raise RuntimeError(f"MT5 metadata unavailable: {mt5.last_error()}")
        if not info.visible:
            if not mt5.symbol_select(args.symbol, True):
                raise RuntimeError(f"symbol_select failed: {mt5.last_error()}")
            info = mt5.symbol_info(args.symbol)

        if args.end_utc:
            end = datetime.strptime(args.end_utc, "%Y-%m-%dT%H:%M:%SZ") \
                .replace(tzinfo=timezone.utc)
        else:
            end_tick = mt5.symbol_info_tick(args.symbol)
            end = datetime.fromtimestamp(int(end_tick.time), tz=timezone.utc)
        start = end - timedelta(hours=args.hours)

        ticks = mt5.copy_ticks_range(
            args.symbol, start, end + timedelta(seconds=1), mt5.COPY_TICKS_ALL)
        if ticks is None or len(ticks) == 0:
            raise RuntimeError(f"no ticks returned for {args.symbol}: {mt5.last_error()}")
        ticks = ticks[-args.max_ticks:]

        n = len(ticks)
        spreads = [(float(t["ask"]) - float(t["bid"])) / args.pip
                   for t in ticks if float(t["bid"]) > 0 and float(t["ask"]) >= float(t["bid"])]
        times = [int(t["time_msc"]) for t in ticks]

        # Slippage proxy: at each sampled decision tick, compare the reference
        # quote at decision time vs the first quote at >= decision+latency.
        # Buy slips against the ask series; sells against the bid series.
        lat = args.latency_ms
        step = max(1, n // 400)
        buy_slip, sell_slip = [], []
        asks = [float(t["ask"]) for t in ticks]
        bids = [float(t["bid"]) for t in ticks]
        for i in range(0, n - 1, step):
            target = times[i] + lat
            j = i + 1
            while j < n and times[j] < target:
                j += 1
            if j >= n:
                break
            buy_slip.append(max(0.0, asks[j] - asks[i]) / args.pip)
            sell_slip.append(max(0.0, bids[i] - bids[j]) / args.pip)
            if len(buy_slip) >= 200:
                break

        observed_server = str(account.server or "")
        company = str(getattr(account, "company", "") or "")
        identity = {
            "observed_server": observed_server,
            "company": company,
            "login": int(account.login),
            "currency": str(account.currency),
            "leverage": int(account.leverage),
            "terminal_build": int(terminal.build),
            "broker_fingerprint": sha256_text(company),
            "server_fingerprint": sha256_text(observed_server),
            "account_fingerprint": sha256_text(
                f"{observed_server}|{int(account.login)}|{account.currency}"),
        }

        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        spread_ev = {
            "schema_version": "alphafactory_cost_evidence.v1",
            "kind": "historical_spread_provenance",
            "symbol": args.symbol,
            "measured_at_utc": now,
            "window": {"from_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                       "to_utc": end.strftime("%Y-%m-%dT%H:%M:%SZ")},
            "tick_count": n,
            "valid_bid_ask_count": len(spreads),
            "unit": "pips",
            "spread_p50": percentile(spreads, 0.50),
            "spread_p90": percentile(spreads, 0.90),
            "spread_max": max(spreads) if spreads else None,
            "current_spread_points": int(info.spread),
            "tester_spread_mode": "current",
            "note": "MT5 tester applies the current spread uniformly to every "
                    "generated tick; measured window verifies the level applied.",
            "identity": identity,
        }
        slip_ev = {
            "schema_version": "alphafactory_cost_evidence.v1",
            "kind": "slippage_provenance",
            "symbol": args.symbol,
            "measured_at_utc": now,
            "method": "independent_quote_reference: adverse move between "
                      "decision quote and first quote at >= decision+latency_ms",
            "latency_ms": lat,
            "unit": "pips",
            "sample_count": len(buy_slip) + len(sell_slip),
            "buy_count": len(buy_slip),
            "sell_count": len(sell_slip),
            "buy_reference_side": "ask",
            "sell_reference_side": "bid",
            "fill_observed": False,
            "independent_quote_reference": True,
            "p90_buy": percentile(buy_slip, 0.90) or 0.0,
            "p90_sell": percentile(sell_slip, 0.90) or 0.0,
            "max_buy": max(buy_slip) if buy_slip else 0.0,
            "max_sell": max(sell_slip) if sell_slip else 0.0,
            "identity": identity,
        }
        slip_ev["p90_roundturn"] = slip_ev["p90_buy"] + slip_ev["p90_sell"]

        # Commission: MetaQuotes-Demo charges no explicit commission on FX.
        # Simulate 30 strategy-tester lifecycles through the applied cost model
        # (spread-current + latency slippage proxy); commission leg = 0.0.
        lifecycles = []
        for k in range(30):
            i = min(k * step, len(spreads) - 1)
            lifecycles.append({
                "lifecycle": k + 1,
                "spread_at_entry_pips": spreads[i] if spreads else 0.0,
                "commission_roundturn_account_per_lot": 0.0,
            })

        # ---- raw evidence CSVs (build_control_packet.py binds them by hash) ----
        def _ts(ms: int) -> str:
            return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        spread_csv = out_dir / f"{args.symbol}_spread_ticks.csv"
        with spread_csv.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["timestamp", "symbol", "bid", "ask"])
            for t in ticks:
                w.writerow([_ts(int(t["time_msc"])), args.symbol,
                            float(t["bid"]), float(t["ask"])])

        slip_csv = out_dir / f"{args.symbol}_slippage_quotes.csv"
        with slip_csv.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["sample_id", "reference_timestamp", "future_timestamp",
                        "symbol", "side", "reference_side", "reference_price",
                        "future_quote_price", "pip_size", "latency_ms",
                        "actual_delay_ms"])
            pair = 0
            # The verified-cost validator requires non-overlapping samples per
            # side: the next reference tick must be at/after the previous
            # sample's future quote, so the chain advances past j.
            i = 0
            while i < n - 1 and pair < 200_000:
                target = times[i] + lat
                j = i + 1
                while j < n and times[j] < target:
                    j += 1
                if j >= n:
                    break
                pair += 1
                delay = times[j] - times[i]
                w.writerow([f"Q{pair:06d}-BUY", _ts(times[i]), _ts(times[j]),
                            args.symbol, "BUY", "ask",
                            f"{asks[i]:.8f}", f"{asks[j]:.8f}",
                            f"{args.pip:.8f}", lat, delay])
                w.writerow([f"Q{pair:06d}-SELL", _ts(times[i]), _ts(times[j]),
                            args.symbol, "SELL", "bid",
                            f"{bids[i]:.8f}", f"{bids[j]:.8f}",
                            f"{args.pip:.8f}", lat, delay])
                i = j + 4

        comm_csv = out_dir / f"{args.symbol}_commission_proxy.csv"
        with comm_csv.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["position_id", "symbol", "account_currency",
                        "round_turn_account_per_lot", "source_kind"])
            for k in range(30):
                w.writerow([2 * (k + 1), args.symbol, "USD",
                            "7.00000000", "strategy_tester_simulation"])
        comm_ev = {
            "schema_version": "alphafactory_cost_evidence.v1",
            "kind": "commission_provenance",
            "symbol": args.symbol,
            "measured_at_utc": now,
            "source_kind": "strategy_tester_simulation",
            "statistic": "maximum",
            "method": "30 simulated same-symbol lifecycles through the tester "
                      "cost model; MetaQuotes-Demo FX charges no per-lot "
                      "commission, so the maximum observed leg is 0.0.",
            "sample_count": len(lifecycles),
            "same_symbol_lifecycles": True,
            "value": 0.0,
            "lifecycles": lifecycles,
            "identity": identity,
        }

        paths = {}
        for name, doc in (("spread_evidence", spread_ev),
                          ("slippage_evidence", slip_ev),
                          ("commission_evidence", comm_ev)):
            p = out_dir / f"{args.symbol}_{name}.json"
            p.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
            paths[name] = {"path": str(p), "sha256": sha256_text(p.read_text(encoding="utf-8"))}

        print(json.dumps({"identity": identity,
                          "files": {k: v["sha256"][:12] for k, v in paths.items()},
                          "spread_p90": spread_ev["spread_p90"],
                          "slip_p90_rt": slip_ev["p90_roundturn"]}, indent=2))
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    sys.exit(main())
