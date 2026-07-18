param(
    [string]$EaName = "",
    [string]$HypothesisId = "",
    [string]$RegistryPath = "",
    [string]$TaskPacket = "",
    [ValidateSet("control", "challenger")]
    [string]$RunRole = "challenger",
    [string]$Symbol = "XAUUSD",
    [string]$Period = "M5",
    [string]$From = "2024.01.01",
    [string]$To = "2025.12.31",
    [ValidateSet(0, 1, 2, 4)]
    [int]$Model = 0,
    [int]$ExecutionMode = 0,
    [int]$FixedDelayMs = 0,
    [int]$TimeoutSec = 7200,
    [string]$Overrides = "",
    [string]$VariantTag = "",
    [ValidateSet("off", "trade-only", "state-lite", "state-full", "snapshot-casebook")]
    [string]$TelemetryTier = "off",
    [int]$Deposit = 10000,
    [int]$Leverage = 100,
    [string]$Spread = "",
    [ValidateSet("challenger", "confirmed")]
    [string]$ValidationStage = "challenger",
    [ValidateSet("scalp", "non_scalp")]
    [string]$HoldingContract = "scalp",
    [string]$CostSourceManifest = "",
    [string]$WfaArtifact = "",
    [string]$VariantsDir = "",
    [string]$MatchedControlRunId = "",
    [switch]$SkipCompile,
    [switch]$SkipValidate,
    [switch]$SkipCostStress,
    [switch]$SkipMarketPhase,
    [switch]$SkipCompare,
    [switch]$CleanupCommonFiles,
    [switch]$AllowResearchCostProxy,
    [switch]$Execute
)

$ErrorActionPreference = "Stop"
$runner = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "research_loop_engine.ps1"
if (-not (Test-Path -LiteralPath $runner -PathType Leaf)) {
    throw "AlphaFactory research-loop engine is missing: $runner"
}

& $runner @PSBoundParameters
exit $LASTEXITCODE
