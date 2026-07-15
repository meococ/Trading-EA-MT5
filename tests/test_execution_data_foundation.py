import csv
import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "02. AlphaFactory" / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import execution_data_foundation as foundation  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class ExecutionDataFoundationTests(unittest.TestCase):
    def fixture(self, root: Path) -> Path:
        base = 1_700_000_000_000
        ticks = root / "ticks.csv"
        write_csv(
            ticks,
            sorted(foundation.TICK_FIELDS),
            [
                {
                    "time_msc": base + offset,
                    "time_utc": iso(base + offset),
                    "symbol": "XAUUSD",
                    "bid": 2000.0 + offset / 100_000,
                    "ask": 2000.2 + offset / 100_000,
                    "last": 0,
                    "volume_real": 0,
                    "flags": 0,
                }
                for offset in (0, 1000)
            ],
        )
        heartbeats = root / "heartbeats.csv"
        server_hash = foundation.sha256_text("Fixture-Server")
        write_csv(
            heartbeats,
            sorted(foundation.HEARTBEAT_FIELDS),
            [
                {
                    "time_msc": base + offset,
                    "time_utc": iso(base + offset),
                    "connected": 1,
                    "server_fingerprint": server_hash,
                    "terminal_build": 5998,
                }
                for offset in (0, 1000)
            ],
        )
        commission = root / "commission.csv"
        write_csv(
            commission,
            sorted(foundation.COMMISSION_FIELDS),
            [
                {
                    "position_id": "P1",
                    "symbol": "XAUUSD",
                    "account_currency": "USD",
                    "round_turn_account_per_lot": 7.0,
                    "conversion_method": "per_trade_contemporaneous",
                    "open_time_utc": iso(base),
                    "close_time_utc": iso(base + 1000),
                    "source": "fixture",
                }
            ],
        )
        slippage = root / "slippage.csv"
        write_csv(
            slippage,
            sorted(foundation.SLIPPAGE_FIELDS),
            [
                {
                    "fill_id": "B1",
                    "symbol": "XAUUSD",
                    "side": "BUY",
                    "reference_side": "ASK",
                    "reference_time_msc": base,
                    "request_time_msc": base + 100,
                    "fill_time_msc": base + 300,
                    "reference_price": 2000.20,
                    "fill_price": 2000.25,
                    "pip_size": 0.01,
                    "source": "fixture",
                },
                {
                    "fill_id": "S1",
                    "symbol": "XAUUSD",
                    "side": "SELL",
                    "reference_side": "BID",
                    "reference_time_msc": base + 400,
                    "request_time_msc": base + 500,
                    "fill_time_msc": base + 700,
                    "reference_price": 2000.00,
                    "fill_price": 1999.97,
                    "pip_size": 0.01,
                    "source": "fixture",
                },
            ],
        )

        def ref(path: Path, method: str) -> dict:
            return {
                "status": "AVAILABLE",
                "completeness_method": method,
                "path": path.name,
                "sha256": sha(path),
                "row_count": sum(1 for _ in path.open(encoding="utf-8")) - 1,
            }

        manifest = {
            "schema_version": foundation.MANIFEST_SCHEMA,
            "created_at_utc": iso(base),
            "capture_id": "FIXTURE-001",
            "purpose": "GVBCI_DATA_FEASIBILITY_ONLY",
            "capture_mode": "PASSIVE_READ_ONLY",
            "broker_identity": {
                "expected_server": "Fixture-Server",
                "observed_server": "Fixture-Server",
                "server_fingerprint": server_hash,
                "account_fingerprint": foundation.sha256_text("fixture-account"),
                "account_currency": "USD",
                "terminal_build": 5998,
            },
            "research_gates": {
                "minimum_quote_elapsed_days": 90,
                "minimum_quote_rows_per_elapsed_day": 1000,
                "minimum_connected_heartbeat_ratio": 0.95,
                "maximum_heartbeat_gap_ms": 60000,
                "minimum_commission_lifecycles_per_symbol": 30,
                "minimum_slippage_fills_per_symbol": 100,
                "minimum_slippage_buys_per_symbol": 30,
                "minimum_slippage_sells_per_symbol": 30,
                "maximum_reference_age_ms": 1000,
            },
            "symbols": [
                {
                    "symbol": "XAUUSD",
                    "digits": 2,
                    "point": 0.01,
                    "pip_size": 0.01,
                    "quote_ticks": ref(ticks, "PASSIVE_HEARTBEAT"),
                    "heartbeats": ref(heartbeats, "PASSIVE_HEARTBEAT"),
                    "commission_lifecycles": ref(commission, "ACCOUNT_HISTORY"),
                    "slippage_fills": ref(
                        slippage, "INDEPENDENT_PRE_SEND_REFERENCE"
                    ),
                }
            ],
            "safety": {
                "read_only": True,
                "orders_sent": 0,
                "positions_opened": 0,
                "live_trading_authorized": False,
            },
        }
        manifest_path = root / "fixture.manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        return manifest_path

    def test_structurally_valid_short_bundle_stops_frontier(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = foundation.validate_bundle(self.fixture(Path(tmp)))
            self.assertEqual(result["verdict"], "STOP_DATA_FRONTIER")
            symbol = result["symbols"][0]
            self.assertIn("QUOTE_WINDOW_TOO_SHORT", symbol["blockers"])
            self.assertIn("COMMISSION_SAMPLE_TOO_SMALL", symbol["blockers"])
            self.assertIn("SLIPPAGE_SAMPLE_TOO_SMALL", symbol["blockers"])
            self.assertFalse(result["authorization"]["ea_edit_compile_backtest"])

    def test_hash_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self.fixture(root)
            (root / "ticks.csv").write_text("tampered", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "sha256 mismatch"):
                foundation.validate_bundle(manifest_path)

    def test_future_or_post_request_reference_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self.fixture(root)
            slip_path = root / "slippage.csv"
            with slip_path.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            rows[0]["reference_time_msc"] = str(
                int(rows[0]["request_time_msc"]) + 1
            )
            write_csv(slip_path, list(rows[0]), rows)
            manifest = json.loads(manifest_path.read_text())
            manifest["symbols"][0]["slippage_fills"]["sha256"] = sha(slip_path)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "decision-time safe"):
                foundation.validate_bundle(manifest_path)

    def test_research_gates_cannot_be_relaxed_below_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = self.fixture(Path(tmp))
            manifest = json.loads(manifest_path.read_text())
            manifest["research_gates"]["minimum_quote_elapsed_days"] = 1
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "manifest schema invalid"):
                foundation.validate_bundle(manifest_path)

    def test_mt5_probe_has_no_mutating_trade_call_surface(self) -> None:
        source = (
            ROOT / "02. AlphaFactory" / "tools" / "execution_data_foundation.py"
        ).read_text(encoding="utf-8")
        for forbidden in (".order_send(", ".positions_close(", ".order_delete("):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
