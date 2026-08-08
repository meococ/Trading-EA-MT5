import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "EA_RegimeStructureFusion.mq5"
TEXT = SOURCE.read_text(encoding="utf-8")


class Path011StaticContract(unittest.TestCase):
    def test_path_management_is_opt_in(self):
        self.assertIn("input bool   InpUsePathManagement=false", TEXT)

    def test_closed_bar_snapshot_contract(self):
        self.assertIn("CopyBuffer(handle,buffer,1,1,data)", TEXT)
        self.assertIn("CopyBuffer(handle,buffer,2,1,data)", TEXT)
        self.assertIn("s.high_price=iHigh(_Symbol,PERIOD_M5,1)", TEXT)
        self.assertNotRegex(TEXT, r"CopyBuffer\([^\n]*,\s*0\s*,")

    def test_shadow_blocks_new_entries_until_control_release(self):
        self.assertIn('if(g_path_shadow_active || g_path_pending_exit_reason!="") return;', TEXT)
        for token in (
            "SHADOW_RELEASE_SL",
            "SHADOW_RELEASE_TP",
            "SHADOW_RELEASE_FRIDAY",
            "SHADOW_RELEASE_MAX_HOLD",
        ):
            self.assertIn(token, TEXT)

    def test_partial_or_placed_close_requires_position_readback(self):
        close_block = re.search(
            r"bool CloseOwnedPosition\(.*?\n  \}\n\n// Tighten",
            TEXT,
            flags=re.S,
        )
        self.assertIsNotNone(close_block)
        self.assertIn("PositionSelectByTicket(ticket)", close_block.group(0))
        self.assertIn("POSITION_VOLUME", close_block.group(0))

    def test_async_path_close_uses_final_deal_and_order_provenance(self):
        resolver = re.search(
            r"int ClassifyPendingPathExitDeal\(.*?\n  \}\n\nvoid PreparePendingPathExit",
            TEXT,
            flags=re.S,
        )
        self.assertIsNotNone(resolver)
        block = resolver.group(0)
        self.assertIn("position_id!=g_path_pending_position_id", block)
        self.assertIn("DEAL_COMMENT", block)
        self.assertIn("ORDER_COMMENT", block)
        self.assertIn("HistoryOrderSelect(order_id)", block)
        self.assertIn("g_path_pending_order_id", block)
        self.assertIn("g_path_pending_deal_id", block)
        self.assertIn("ClassifyPendingPathExitDeal(deal,position_id,order_id)", TEXT)
        self.assertIn("FinalizePendingPathExit(); // Handles PLACED/async completion", TEXT)

    def test_unresolved_async_provenance_fails_closed_until_history_arrives(self):
        self.assertIn("g_path_pending_final_unresolved=true", TEXT)
        self.assertIn("TRADE_TRANSACTION_HISTORY_ADD", TEXT)
        self.assertIn("ResolveDeferredPendingPathExit();", TEXT)
        self.assertIn('if(g_path_shadow_active || g_path_pending_exit_reason!="") return;', TEXT)

    def test_path_exit_finalization_is_transaction_owned(self):
        manager = re.search(
            r"void ManagePathPosition\(.*?\n  \}\n\nvoid RetryPendingPathExit",
            TEXT,
            flags=re.S,
        )
        self.assertIsNotNone(manager)
        self.assertNotIn("FinalizePendingPathExit()", manager.group(0))
        retry = re.search(r"void RetryPendingPathExit\(.*?\n  \}", TEXT, flags=re.S)
        self.assertIsNotNone(retry)
        self.assertNotIn("FinalizePendingPathExit()", retry.group(0))
        self.assertIn("if(path_class>0)", TEXT)

    def test_control_time_exit_cancels_unresolved_path_before_close(self):
        manager = re.search(
            r"bool ManagePosition\(.*?\n  \}\n\n// PATH-011",
            TEXT,
            flags=re.S,
        )
        self.assertIsNotNone(manager)
        block = manager.group(0)
        self.assertLess(block.index("ClearPendingPathExit();"), block.index('CloseOwnedPosition(ticket,"FRIDAY_FLAT")'))
        self.assertLess(block.rindex("ClearPendingPathExit();"), block.index('CloseOwnedPosition(ticket,"MAX_HOLD")'))

    def test_failed_native_time_exit_cannot_fall_through_to_path_management(self):
        self.assertIn("bool native_exit_due=ManagePosition(utc_now);", TEXT)
        self.assertIn("if(native_exit_due && active_ticket!=0) return;", TEXT)

    def test_break_even_stop_arms_original_control_shadow(self):
        self.assertIn("SeedPathBeShadowWatch(ticket,direction)", TEXT)
        self.assertIn("g_path_be_shadow_watch", TEXT)
        self.assertIn("close_reason==DEAL_REASON_SL", TEXT)
        self.assertIn('"SHADOW_ARM_BE_STOP"', TEXT)
        self.assertIn("g_path_be_sl=g_active_sl", TEXT)
        self.assertIn("g_path_be_tp=g_active_tp", TEXT)

    def test_pending_close_retry_precedes_indicator_snapshot(self):
        on_tick = re.search(r"void OnTick\(\).*?\n  \}\s*$", TEXT, flags=re.S)
        self.assertIsNotNone(on_tick)
        block = on_tick.group(0)
        self.assertLess(block.index("RetryPendingPathExit(active_ticket)"), block.index("ReadSnapshot(path_snapshot)"))

    def test_break_even_requires_stop_readback(self):
        modify_block = re.search(
            r"bool ModifyOwnedStop\(.*?\n  \}\n\nbool RemainingVolume",
            TEXT,
            flags=re.S,
        )
        self.assertIsNotNone(modify_block)
        self.assertIn("applied_sl=PositionGetDouble(POSITION_SL)", modify_block.group(0))

    def test_lifecycle_prefix_is_preserved_and_comment_appended(self):
        prefix = (
            '"event_time","utc_time","tag","action","order_type","volume",'
            '"price","sl","tp","reason","deal","order","symbol","position_id",'
            '"entry_price","initial_sl","initial_tp","risk_pts","initial_risk_account",'
            '"achievedr","net_profit","deal_net","is_final_close","engine_name",'
            '"hypothesis_id","deal_comment"'
        )
        self.assertIn(prefix, TEXT)

    def test_three_completed_bar_gate_is_explicit(self):
        self.assertIn("held_bars>=InpPathMinInvalidationBars", TEXT)
        self.assertIn("InpPathMinInvalidationBars=3", TEXT)


if __name__ == "__main__":
    unittest.main()
