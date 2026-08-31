from __future__ import annotations

from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1] / "session_trader"


def test_python_control_plane_has_no_broker_mutation_calls() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in PACKAGE.glob("*.py")
        if path.name != "collector.py"
    )
    forbidden = (
        "import MetaTrader5",
        "from MetaTrader5",
        ".order_send(",
        ".order_check(",
        "TRADE_ACTION_DEAL",
        "TRADE_ACTION_PENDING",
    )
    for token in forbidden:
        assert token not in combined


def test_read_only_collector_cannot_send_or_check_orders() -> None:
    source = (PACKAGE / "collector.py").read_text(encoding="utf-8")
    assert ".order_send(" not in source
    assert ".order_check(" not in source
    assert "TRADE_ACTION" not in source


def test_agent_layer_has_no_strategy_or_execution_mutation_adapter() -> None:
    source = (PACKAGE / "agents.py").read_text(encoding="utf-8")
    assert "subprocess" not in source
    assert "order_send" not in source
    assert "live_strategy_mutation_authorized" not in source
