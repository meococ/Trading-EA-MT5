"""Fail-closed session trading control plane for AlphaFactory.

The package deliberately separates AI-authored proposals from deterministic
risk and execution authority.  Importing it never connects to MT5.
"""

from .models import (
    AccountSnapshot,
    ArtifactRef,
    Candidate,
    Critique,
    MarketSnapshot,
    RiskDecision,
    RiskPolicy,
    RiskState,
    SessionPlan,
    TradeIntent,
)
from .artifacts import ArtifactStore, HashChainLedger
from .executor import build_execution_attempt
from .risk_gateway import RiskGateway, evaluate_risk
from .watcher import DeterministicWatcher, evaluate_watch

__all__ = [
    "AccountSnapshot",
    "ArtifactRef",
    "Candidate",
    "Critique",
    "MarketSnapshot",
    "RiskDecision",
    "RiskPolicy",
    "RiskState",
    "SessionPlan",
    "TradeIntent",
    "ArtifactStore",
    "HashChainLedger",
    "DeterministicWatcher",
    "RiskGateway",
    "build_execution_attempt",
    "evaluate_risk",
    "evaluate_watch",
]
