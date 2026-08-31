//+------------------------------------------------------------------+
//| EA_SonicR.mq5                                                     |
//| Sonic R Flagship: Classic + Re-entry + Scout2                    |
//+------------------------------------------------------------------+
#property copyright "Max & Ngai Meo Coc"
#property version   "2.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>
#include "Include/SNR_Types.mqh"

input group "=== Engine ==="
input bool   InpEnabled              = true;
input int    InpMagic                = 20260422;
input string InpComment              = "SNR";
input string InpVariantTag           = "EUR_CLASSIC_SEED";
input string InpResearchLaneTag      = "sonic_flagship";

input group "=== Risk ==="
input double InpClassicRiskPct       = 0.50;
input double InpSecondLayerRiskPct   = 0.25;
input double InpMaxNarrativeRiskPct  = 0.75;
input bool   InpUseOrderCalcRiskSizing = true;
input bool   InpOrderCalcRiskFailClosed = true;
input double InpMaxLot               = 1.00;
input double InpDailyLossLockPct     = 2.50;
input double InpMaxEquityDrawdownPct = 12.00;
input int    InpMaxTradesPerDay      = 3;
input int    InpMaxLayers            = 2;

input group "=== Sonic Structure ==="
input int    InpDragonPeriod         = 34;
input int    InpTrendPeriod          = 89;
input int    InpATRPeriod            = 14;
input int    InpSlopeLookbackBars    = 5;
input double InpMinDragonSlopeATR    = 0.10;
input double InpMinBodyRatio         = 0.45;
input int    InpWaveLookbackBars     = 6;
input int    InpBreakoutLookbackBars = 4;
input int    InpReentryLookbackBars  = 3;
input bool   InpUseClassicTrend      = true;
input bool   InpUseClassicSourceCore = false;
input bool   InpUseClassicReversal   = false;
input bool   InpUseScoutProbe        = false;
input bool   InpUseReentry           = false;
input bool   InpUseArmedClassic      = false;
input bool   InpUseContinuationPullback = false;
input bool   InpUseDragonPullbackEntry = false;
input bool   InpUseEurLondonShortCleanRoute = false;
input int    InpClassicArmBars       = 3;
input double InpMinBreakoutDistanceATR = 0.10;
input double InpMaxClassicBreakoutExtensionATR = 1.50;
input double InpMaxPullbackDepthATR  = 1.40;
input int    InpContinuationLookbackBars = 4;
input double InpContinuationMaxPullbackATR = 1.10;
input double InpContinuationMaxExtensionATR = 0.80;
input int    InpDragonPullbackLookbackBars = 8;
input double InpDragonPullbackMaxDepthATR = 1.20;
input double InpDragonPullbackMaxExtensionATR = 0.65;
input double InpStopAtrBuffer        = 0.25;
input double InpClassicTargetRR      = 1.60;
input double InpDragonPullbackTargetRR = 1.25;
input double InpEurLondonShortRouteTargetRR = 1.25;
input double InpContinuationTargetRR = 1.20;
input double InpReentryTargetRR      = 1.35;
input double InpScout2TargetRR       = 1.10;
input bool   InpUsePvsraParity       = true;
input bool   InpUseSourcePvaParityV1 = false; // Source-auth PVA 10-bar rising/climax parity
input bool   InpUsePvsraSrContext    = false;
input bool   InpUseSourceSrInteractionV1 = false; // Source-auth WHQ S/R interaction telemetry only
input bool   InpBlockSidewayNarrow   = false; // Block entries during Sideway Narrow regime
input double InpMaxChaseDistanceAtr  = 1.0;   // Max chase distance from Dragon to trigger bar (0 = disabled)
input bool   InpUsePullbackEntry     = false; // Enter on pullback to Dragon instead of Breakout
input bool   InpRequirePvsraVolume   = false; // Require climax volume during setup phase
input int    InpVolumeLookback       = 5;     // Number of bars to check for volume climax
input double InpVolumeClimaxMultiplier = 2.0; // Climax volume multiplier (relative to 10-bar average)
input bool   InpUseRegimeRouter      = false;
input bool   InpRegimeRouterLegacyFallback = false;
input bool   InpUseXauActiveClassic  = false;
input bool   InpUseXauRangeAbsorption = false;
input bool   InpXauRangeAbsorptionAllowInnerRotation = false;
input double InpXauRangeAbsorptionMinTargetRR = 0.80;
input bool   InpUseXauSweepReclaimScanner = false;
input bool   InpUseXauSweepReclaimExecution = false;
input int    InpXauSweepReclaimDirectionMode = 0; // 0=both, 1=long only, 2=short only
input string InpXauSweepReclaimBlockedHours = "";
input string InpXauSweepReclaimBlockedWeekdays = "";
input string InpXauSweepReclaimBlockedLongHours = "";
input string InpXauSweepReclaimBlockedShortHours = "";
input string InpXauSweepReclaimBlockedLongWeekdays = "";
input string InpXauSweepReclaimBlockedShortWeekdays = "";
input double InpXauSweepReclaimMinTargetRR = 0.80;
input double InpXauSweepReclaimMaxTargetRR = 0.00; // 0 disables max-RR veto
input bool   InpUseXauLongBiasCoreGate = false;
input bool   InpEnableImpulseS1FPVeto = false; // IMPULSE S1 false positive veto
input bool   InpUseXauS1M15AtrImpulseFilter = false; // Require active closed-M15 ATR impulse for executed XAU S1
input int    InpXauS1M15AtrPeriod = 14;
input int    InpXauS1M15AtrEmaPeriod = 100;
input double InpXauS1M15AtrMultiplier = 1.20;
input bool   InpUseXauS1M5DragonAnchorCompressionFilter = false; // Block stretched Dragon-vs-Trend S1 entries
input double InpXauS1M5DragonAnchorMaxCompressionAtr = 2.20;
input bool   InpUseEurTrendClassic   = false;
input bool   InpUseEurAsianBoxRetest = false;
input double InpScalpLaneRiskPct     = 0.10;
input double InpRangeLaneRiskPct     = 0.08;
input int    InpMaxScalpTradesPerDay = 5;
input int    InpMaxLaneLossesPerSession = 2;
input string InpBlockedClassicPvsraEvents = "";
input string InpBlockedClassicLevelZones = "";
input bool   InpUseNy16ShortClimaxQuarterRoute = false;
input int    InpLevelGridMode        = 1;  // 0=whole/half, 1=quarter grid
input int    InpMinPvsraGradeClassic = 2;
input int    InpMinPvsraGradeReversal = 4;
input int    InpMinPvsraGradeScout   = 4;
input int    InpReentryMinPvsraGrade = 2;
input int    InpScoutMinPvsraGrade   = 3;

input group "=== Dynamic Quant Framework ==="
input bool   InpUseDynamicSMCStructure      = false; // Use SMC structural highs/lows for breakout trigger
input bool   InpUseVolatilitySqueeze        = false; // Volatility Squeeze filter (avoid trading inside squeeze)
input bool   InpUseLiquiditySweep           = false; // Liquidity sweep (stop hunt) context booster
input int    InpSweepLookbackBars           = 15;    // Lookback bars for liquidity sweep detection
input bool   InpUseStructuralTrailing       = false; // Trailing stop based on SMC market structure
input int    InpSMCStructureLookback        = 120;   // Lookback bars for swing high/low detection

input group "=== Context ==="
input bool   InpUseH1Bias            = true;
input bool   InpUseH4Bias            = true;
input bool   InpUseSoftHtfBias       = true;
input bool   InpUseTrendHardGate     = true;
input int    InpHtfProfileMode       = 0;  // 0=H1/H4, 1=scalp auto M15/H1 on M5
input bool   InpSourceCoreKeepsHtfGate = false;
input int    InpHtfBiasPeriod        = 89;
input double InpSpreadSoftPips       = 1.80;
input double InpSpreadHardPips       = 3.50;
input double InpWholeLevelRadiusPips = 8.0;
input double InpHalfLevelRadiusPips  = 5.0;

input group "=== Sessions ==="
input bool   InpUseLondon            = true;
input int    InpLondonStartHour      = 9;
input int    InpLondonStartMinute    = 0;
input int    InpLondonEndHour        = 12;
input int    InpLondonEndMinute      = 0;
input bool   InpUseNewYork           = true;
input int    InpNewYorkStartHour     = 15;
input int    InpNewYorkStartMinute   = 0;
input int    InpNewYorkEndHour       = 18;
input int    InpNewYorkEndMinute     = 0;
input int    InpNewYorkReversalStartHour = 14;
input int    InpNewYorkReversalEndHour   = 18;
input int    InpHardFlatHour         = 18;
input int    InpHardFlatMinute       = 45;
input int    InpFridayFlatHour       = 16;
input int    InpFridayFlatMinute     = 30;
input bool   InpSkipFridayEntries    = true;
input string InpBlockedEntryHours    = "";
input string InpBlockedEntryWeekdays = "";
input bool   InpForceFlatOutsideSession = false;
input int    InpMinMinutesToNewTrade = 75;

input group "=== Calendar ==="
input bool   InpUseNewsFilter          = true;
input string InpCalendarFile           = "SNR_FX_EVENTS.csv";
input int    InpLegacyCalendarMinImportance = 2;
input int    InpNewsBlockBeforeMin     = 45;
input int    InpNewsBlockAfterMin      = 30;
input int    InpForceFlatBeforeNewsMin = 15;
input int    InpTimeProfileMode        = 1;  // 0=fixed UTC offset, 1=broker EET/EEST
input int    InpFixedUtcOffsetHours    = 2;

input group "=== Execution ==="
input int    InpDeviation            = 30;
input int    InpRetryCount           = 0;    // validation-safe default; >0 enables blocking Sleep retry
input int    InpRetryDelayMs         = 300;
input double InpMinSLPips            = 5.0;
input double InpScalpMinSLPips       = 0.0;  // 0=use InpMinSLPips
input bool   InpUseClassicMinSLFloor = false;
input double InpContinuationMinSLPips = 0.0;  // 0=use InpMinSLPips
input double InpMaxSLPips            = 60.0;
input bool   InpPreservePrimaryExitsOnScaleIn = false;
input bool   InpModifyAllPositionsAfterEntry = true;
input bool   InpUseBreakEven         = true;
input double InpBreakEvenTriggerR    = 1.0;

input group "=== Telemetry ==="
input bool   InpEnableTelemetry      = true;
input bool   InpEnableSourceClassicDragonEdgeDistanceTelemetry = false;
input bool   InpEnableSourceH4TargetRunwayTelemetry = false;
input bool   InpEnableFxM15MtfPvaWeakeningTelemetry = false;
input bool   InpEnableOpportunityLogger = false;
input bool   InpEnableShadowNarrative = false;
input bool   InpEnableStateTelemetry = false;
input bool   InpEnableGoldRegimeTelemetry = false;
input bool   InpUseOpportunityScoreGate = false;
input int    InpMinClassicOpportunityScore = 70;
input int    InpMinReentryOpportunityScore = 75;
input bool   InpUseXauClassicStateQualityGate = true;
input int    InpXauClassicStateMinWarnings = 2;
input double InpXauClassicMinRunwayPips = 2.0;
input double InpXauClassicMaxDragonExtensionAtr = 1.50;
input double InpXauClassicMaxOverlapRatio = 0.12;
input double InpXauClassicHour15MinRunwayPips = 3.0;
input bool   InpUseFxClassicStateQualityGate = true;
input double InpFxClassicMinRunwayPips = 4.0;
input double InpFxClassicMaxDragonExtensionAtr = 1.20;
input double InpFxClassicMaxOverlapRatio = 0.35;
input bool   InpFxClassicRequireCleanWave = false;
input bool   InpFxClassicRequireHtfAlignment = true;
input bool   InpFxClassicBlockFlatDragon = true;
input bool   InpFxClassicBlockLateChase = true;
input bool   InpUseFxChaseTrapV2ADiagnostic = false;
input bool   InpEnableFxClassicNearMissTelemetry = false;
input bool   InpUseFxM15HtfClassicRoute = false;
input bool   InpFxM15RouteRequireH1H4Alignment = true;
input int    InpFxM15RouteHtfMode = 0; // 0=hard H1/H4, 1=H1 required + H4 opposite veto
input bool   InpFxM15RouteRequireCleanWave = true;
input bool   InpFxM15RouteRequireDragonExpansion = true;
input bool   InpFxM15RouteBlockLateChase = true;
input double InpFxM15RouteMinSrRunwayPips = 8.0;
input bool   InpUseXauTrapManagementRouter = false;
input double InpXauTrapManageMinScore = 67.9;
input int    InpXauTrapManageBars = 3;
input double InpXauTrapManageMinMfeR = 0.25;
input int    InpXauTrapManageLateHour = 17;
input double InpXauTrapManageThursdayExtensionAtr = 1.36;
input bool   InpUseDragonPvsraEntryProxyGate = false;
input bool   InpDragonPvsraRequireTrendPullback = true;
input bool   InpDragonPvsraBlockFlatDragon = true;
input bool   InpDragonPvsraBlockLateChase = true;
input bool   InpDragonPvsraRequirePvsraAlignment = true;
input double InpDragonPvsraMinRunwayPips = 15.0;
input group "=== Parameter Mapping & Auto-Sleeve ==="
input bool   InpUseAutoSleeveConfig  = false;
input bool   InpUseFxM15ReversalContextGate = false;
input bool   InpOnlyNewYorkReversal  = false;
input bool   InpUseDragonExpansionFilter = false;
input double InpDragonMaxExpansionRatio = 0.95;
input double InpGoldMinCompressionRatio = 0.40;
input int    InpGoldS1MinPvsraGrade  = 3;
input bool   InpXauS1RequireWholeHalf = false;
input double InpRegimeRouterMinDragonSlope = 0.08;
input double InpRegimeRouterMinTrendSlope = 0.02;

// Global runtime overrides and declarations for sleeve configs
bool   g_useRegimeRouter = false;
bool   g_onlyNewYorkReversal = false;
bool   g_useDragonExpansionFilter = false;
double g_dragonMaxExpansionRatio = 0.95;
bool   g_useClassicTrend = true;
bool   g_useClassicReversal = false;
bool   g_useFxM15ReversalContextGate = false;
double g_goldMinCompressionRatio = 0.40;
int    g_goldS1MinPvsraGrade = 3;
bool   g_xauS1RequireWholeHalf = false;
bool   g_useArmedClassic = false;
bool   g_useDragonPullbackEntry = false;
double g_regimeRouterMinDragonSlope = 0.08;
double g_regimeRouterMinTrendSlope = 0.02;
double g_minDragonSlopeATR = 0.08;
bool   g_forceFlatOutsideSession = true;

bool   g_useReentry = false;
bool   g_useContinuationPullback = false;
bool   g_useScoutProbe = false;
bool   g_useFxClassicStateQualityGate = true;
int    g_minPvsraGradeClassic = 2;
int    g_minMinutesToNewTrade = 75;
bool   g_useDynamicSMCStructure = false;
bool   g_useLiquiditySweep = false;
bool   g_useStructuralTrailing = false;
bool   g_useVolatilitySqueeze = false;
double g_stopAtrBuffer = 0.25;
bool   g_useLondon = true;
bool   g_useNewYork = true;
bool   g_useXauActiveClassic = false;
bool   g_useXauRangeAbsorption = false;
bool   g_useXauSweepReclaimExecution = false;

// Dynamic parameters added for AutoSleeve overrides
int    g_waveLookbackBars = 6;
int    g_smcStructureLookback = 120;
double g_maxClassicBreakoutExtensionATR = 1.50;
int    g_reentryMinPvsraGrade = 2;
int    g_classicArmBars = 3;
bool   g_useXauClassicStateQualityGate = true;
double g_xauRangeAbsorptionMinTargetRR = 0.80;
double g_xauSweepReclaimMinTargetRR = 0.80;

bool   g_useClassicMinSLFloor = false;
double g_classicRiskPct = 0.50;
double g_secondLayerRiskPct = 0.25;
double g_maxNarrativeRiskPct = 0.75;
double g_fxClassicMinRunwayPips = 4.0;
double g_scalpMinSLPips = 0.0;
double g_spreadSoftPips = 1.80;
string g_blockedEntryWeekdays = "";

// Dynamic parameters auto-generated for complete mapping
bool   g_enabled = true;
int    g_magic = 20260422;
string g_comment = "SNR";
string g_variantTag = "EUR_CLASSIC_SEED";
string g_researchLaneTag = "sonic_flagship";
bool   g_useOrderCalcRiskSizing = true;
bool   g_orderCalcRiskFailClosed = true;
double g_maxLot = 1.00;
double g_dailyLossLockPct = 2.50;
double g_maxEquityDrawdownPct = 12.00;
int    g_maxTradesPerDay = 3;
int    g_dragonPeriod = 34;
int    g_trendPeriod = 89;
int    g_atrPeriod = 14;
int    g_slopeLookbackBars = 5;
bool   g_useClassicSourceCore = false;
bool   g_useEurLondonShortCleanRoute = false;
double g_eurLondonShortRouteTargetRR = 1.25;
bool   g_useSourcePvaParityV1 = false;
bool   g_usePvsraSrContext = false;
bool   g_useSourceSrInteractionV1 = false;
bool   g_blockSidewayNarrow = false;
double g_maxChaseDistanceAtr = 1.0;
bool   g_usePullbackEntry = false;
bool   g_requirePvsraVolume = false;
int    g_volumeLookback = 5;
double g_volumeClimaxMultiplier = 2.0;
bool   g_regimeRouterLegacyFallback = false;
bool   g_xauRangeAbsorptionAllowInnerRotation = false;
bool   g_useXauSweepReclaimScanner = false;
int    g_xauSweepReclaimDirectionMode = 0;
string g_xauSweepReclaimBlockedHours = "";
string g_xauSweepReclaimBlockedWeekdays = "";
string g_xauSweepReclaimBlockedLongHours = "";
string g_xauSweepReclaimBlockedShortHours = "";
string g_xauSweepReclaimBlockedLongWeekdays = "";
string g_xauSweepReclaimBlockedShortWeekdays = "";
double g_xauSweepReclaimMaxTargetRR = 0.00;
bool   g_useXauLongBiasCoreGate = false;
bool   g_enableImpulseS1FPVeto = false;
bool   g_useXauS1M15AtrImpulseFilter = false;
int    g_xauS1M15AtrPeriod = 14;
int    g_xauS1M15AtrEmaPeriod = 100;
double g_xauS1M15AtrMultiplier = 1.20;
bool   g_useXauS1M5DragonAnchorCompressionFilter = false;
double g_xauS1M5DragonAnchorMaxCompressionAtr = 2.20;
bool   g_useEurTrendClassic = false;
bool   g_useEurAsianBoxRetest = false;
double g_scalpLaneRiskPct = 0.10;
double g_rangeLaneRiskPct = 0.08;
int    g_maxScalpTradesPerDay = 5;
int    g_maxLaneLossesPerSession = 2;
string g_blockedClassicPvsraEvents = "";
string g_blockedClassicLevelZones = "";
bool   g_useNy16ShortClimaxQuarterRoute = false;
int    g_minPvsraGradeReversal = 4;
int    g_minPvsraGradeScout = 4;
int    g_scoutMinPvsraGrade = 3;
int    g_sweepLookbackBars = 15;
bool   g_useH1Bias = true;
bool   g_useH4Bias = true;
int    g_htfProfileMode = 0;
bool   g_sourceCoreKeepsHtfGate = false;
int    g_htfBiasPeriod = 89;
double g_wholeLevelRadiusPips = 8.0;
double g_halfLevelRadiusPips = 5.0;
int    g_londonStartHour = 9;
int    g_londonStartMinute = 0;
int    g_londonEndHour = 12;
int    g_londonEndMinute = 0;
int    g_newYorkStartHour = 15;
int    g_newYorkStartMinute = 0;
int    g_newYorkEndHour = 18;
int    g_newYorkEndMinute = 0;
int    g_newYorkReversalStartHour = 14;
int    g_newYorkReversalEndHour = 18;
int    g_hardFlatHour = 18;
int    g_hardFlatMinute = 45;
int    g_fridayFlatHour = 16;
int    g_fridayFlatMinute = 30;
bool   g_skipFridayEntries = true;
string g_blockedEntryHours = "";
bool   g_useNewsFilter = true;
string g_calendarFile = "SNR_FX_EVENTS.csv";
int    g_legacyCalendarMinImportance = 2;
int    g_newsBlockBeforeMin = 45;
int    g_newsBlockAfterMin = 30;
int    g_forceFlatBeforeNewsMin = 15;
int    g_timeProfileMode = 1;
int    g_fixedUtcOffsetHours = 2;
int    g_deviation = 30;
int    g_retryCount = 0;
int    g_retryDelayMs = 300;
double g_minSLPips = 5.0;
double g_continuationMinSLPips = 0.0;
double g_maxSLPips = 60.0;
bool   g_preservePrimaryExitsOnScaleIn = false;
bool   g_modifyAllPositionsAfterEntry = true;
bool   g_useBreakEven = true;
double g_breakEvenTriggerR = 1.0;
bool   g_enableTelemetry = true;
bool   g_enableSourceClassicDragonEdgeDistanceTelemetry = false;
bool   g_enableSourceH4TargetRunwayTelemetry = false;
bool   g_enableFxM15MtfPvaWeakeningTelemetry = false;
bool   g_enableOpportunityLogger = false;
bool   g_enableShadowNarrative = false;
bool   g_enableStateTelemetry = false;
bool   g_enableGoldRegimeTelemetry = false;
bool   g_useOpportunityScoreGate = false;
int    g_minClassicOpportunityScore = 70;
int    g_minReentryOpportunityScore = 75;
int    g_xauClassicStateMinWarnings = 2;
double g_xauClassicMinRunwayPips = 2.0;
double g_xauClassicMaxDragonExtensionAtr = 1.50;
double g_xauClassicMaxOverlapRatio = 0.12;
double g_xauClassicHour15MinRunwayPips = 3.0;
double g_fxClassicMaxDragonExtensionAtr = 1.20;
double g_fxClassicMaxOverlapRatio = 0.35;
bool   g_fxClassicRequireCleanWave = false;
bool   g_fxClassicRequireHtfAlignment = true;
bool   g_fxClassicBlockFlatDragon = true;
bool   g_fxClassicBlockLateChase = true;
bool   g_useFxChaseTrapV2ADiagnostic = false;
bool   g_enableFxClassicNearMissTelemetry = false;
bool   g_useFxM15HtfClassicRoute = false;
bool   g_fxM15RouteRequireH1H4Alignment = true;
int    g_fxM15RouteHtfMode = 0;
bool   g_fxM15RouteRequireCleanWave = true;
bool   g_fxM15RouteRequireDragonExpansion = true;
bool   g_fxM15RouteBlockLateChase = true;
double g_fxM15RouteMinSrRunwayPips = 8.0;
bool   g_useXauTrapManagementRouter = false;
double g_xauTrapManageMinScore = 67.9;
int    g_xauTrapManageBars = 3;
double g_xauTrapManageMinMfeR = 0.25;
int    g_xauTrapManageLateHour = 17;
double g_xauTrapManageThursdayExtensionAtr = 1.36;
bool   g_useDragonPvsraEntryProxyGate = false;
bool   g_dragonPvsraRequireTrendPullback = true;
bool   g_dragonPvsraBlockFlatDragon = true;
bool   g_dragonPvsraBlockLateChase = true;
bool   g_dragonPvsraRequirePvsraAlignment = true;
double g_dragonPvsraMinRunwayPips = 15.0;

// Dynamic parameters added for AutoSleeve overrides (22 unmapped)
int    g_levelGridMode = 1;
bool   g_usePvsraParity = true;
double g_classicTargetRR = 1.60;
double g_dragonPullbackTargetRR = 1.25;
double g_continuationTargetRR = 1.20;
double g_reentryTargetRR = 1.35;
double g_scout2TargetRR = 1.10;
double g_dragonPullbackMaxExtensionATR = 0.65;
double g_dragonPullbackMaxDepthATR = 1.20;
double g_continuationMaxPullbackATR = 1.10;
double g_continuationMaxExtensionATR = 0.80;
double g_minBreakoutDistanceATR = 0.10;
double g_maxPullbackDepthATR = 1.40;
int    g_breakoutLookbackBars = 4;
int    g_reentryLookbackBars = 3;
int    g_continuationLookbackBars = 4;
int    g_dragonPullbackLookbackBars = 8;
double g_minBodyRatio = 0.45;
int    g_maxLayers = 2;
bool   g_useSoftHtfBias = true;
bool   g_useTrendHardGate = true;
double g_spreadHardPips = 3.50;

#include "Include/SNR_TimeCompliance.mqh"
#include "Include/SNR_Telemetry.mqh"
#include "Include/SNR_Context.mqh"
#include "Include/SNR_GoldRegime.mqh"
#include "Include/SNR_Signals.mqh"
#include "Include/SNR_Opportunity.mqh"

CTrade        g_trade;
CPositionInfo g_pos;
CSymbolInfo   g_sym;

int           g_hDragonHigh = INVALID_HANDLE;
int           g_hDragonMid  = INVALID_HANDLE;
int           g_hDragonLow  = INVALID_HANDLE;
int           g_hTrend      = INVALID_HANDLE;
int           g_hATR        = INVALID_HANDLE;
int           g_hH1Bias     = INVALID_HANDLE;
int           g_hH4Bias     = INVALID_HANDLE;

double        g_pipSize = 0.0;
int           g_digits  = 0;
datetime      g_lastBar = 0;
datetime      g_lastTradeDay = 0;
int           g_tradesToday = 0;
datetime      g_laneLossDay = 0;
string        g_laneLossSession = "";
int           g_laneLossXauT1 = 0;
int           g_laneLossXauR1 = 0;
int           g_laneLossXauS1 = 0;
int           g_laneLossEurT1 = 0;
int           g_laneLossEurB1 = 0;
double        g_dayStartEquity = 0.0;
double        g_peakEquity = 0.0;
string        g_lastStatus = "BOOT";
SnrNarrative  g_narrative;
SnrOpenTrade  g_openTrades[];
SnrClassicArm g_classicArm;
SnrClassicArm g_xauT1Arm;
SnrShadowNarrative g_shadowLong;
SnrShadowNarrative g_shadowShort;

void SNR_LogFxChaseTrapV2ADiagnostic(const SnrContext &ctx,
                                     const SnrDecision &decision,
                                     const string outcome,
                                     const SnrPvsraSrFields &fields)
{
   if(!g_enableTelemetry || !g_useFxChaseTrapV2ADiagnostic)
      return;
   if(!decision.fx_v2a_evaluated)
      return;

   int handle = SNR_OpenAppendCsv(g_snrFxV2aDiagnosticLogFile);
   if(handle == INVALID_HANDLE)
      return;

   string setup_type = SNR_OpportunitySetupType(decision.mode, ctx);
   string wave_id = SNR_OpportunityWaveId(ctx, decision, setup_type, decision.direction);
   datetime closed_bar = (fields.bar_time > 0 ? fields.bar_time : SNR_OpportunityClosedBarTime(ctx));
   string candidate_id = SNR_OpportunityCandidateId(g_snrRunId, closed_bar, setup_type, decision.direction, wave_id);

   double entry_price = (decision.direction > 0 ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID));
   double planned_sl = decision.stop_price;
   double risk_points = 0.0;
   double risk_pips = 0.0;
   double planned_tp = 0.0;
   if(entry_price > 0.0 && planned_sl > 0.0 && _Point > 0.0 && g_pipSize > 0.0)
   {
      double risk_price = MathAbs(entry_price - planned_sl);
      risk_points = risk_price / _Point;
      risk_pips = risk_price / g_pipSize;
      if(decision.target_rr > 0.0)
         planned_tp = (decision.direction > 0 ? entry_price + risk_price * decision.target_rr : entry_price - risk_price * decision.target_rr);
   }

   double min_sl_pips = g_minSLPips;
   if(g_scalpMinSLPips > 0.0 &&
      (decision.mode == SNR_MODE_XAU_ACTIVE_CLASSIC ||
       decision.mode == SNR_MODE_XAU_SWEEP_RECLAIM ||
       decision.mode == SNR_MODE_EUR_TREND_CLASSIC ||
       decision.mode == SNR_MODE_EUR_ASIAN_BOX_RETEST))
      min_sl_pips = g_scalpMinSLPips;
   if(decision.mode == SNR_MODE_CONTINUATION && g_continuationMinSLPips > 0.0)
      min_sl_pips = g_continuationMinSLPips;

   long stop_level_pts = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   long freeze_level_pts = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL);
   double min_dist = (double)MathMax(stop_level_pts, freeze_level_pts) * _Point;
   string min_stop_check = "not_planned";
   if(entry_price > 0.0 && planned_sl > 0.0 && planned_tp > 0.0)
   {
      min_stop_check = "ok";
      if(risk_pips < min_sl_pips || risk_pips > g_maxSLPips)
         min_stop_check = "sl_range_fail";
      else if(min_dist > 0.0 &&
              (MathAbs(entry_price - planned_sl) < min_dist || MathAbs(entry_price - planned_tp) < min_dist))
         min_stop_check = "broker_stop_fail";
   }

   string order_send_attempted = ((outcome == "FIRED" || outcome == "ORDER_REJECT") ? "true" : "false");
   string order_send_result = (outcome == "ORDER_REJECT" && decision.block_reason != "" ? decision.block_reason : outcome);
   string fail_closed_reason = ((outcome == "BLOCKED" || outcome == "ORDER_REJECT") ? decision.block_reason : "");
   double dragon_extension = SNR_StateTelemetryExtensionFromDragonAtr(ctx, fields, decision.direction);
   double dragon_overlap = SNR_StateTelemetryDragonOverlapRatio(ctx, fields);
   double sr_runway_pips = SNR_StateTelemetrySrRunwayPips(fields, decision.direction, g_pipSize);
   string v2a_wave = SNR_FxV2AWaveState(fields);
   string v2a_runway = SNR_FxV2ASrRunway(ctx, fields, decision.direction, g_pipSize, decision.block_reason);
   string v2a_trend = SNR_FxV2ATrendHtfState(ctx, decision.direction);
   int v2a_risk_score = SNR_FxV2APublicRiskScore(ctx, fields, v2a_runway, v2a_trend, v2a_wave, decision.direction);
   string v2a_chase = SNR_FxV2AChaseRisk(ctx, fields, v2a_runway, v2a_trend, v2a_wave, v2a_risk_score, decision.direction);
   string v2a_trap = SNR_FxV2ATrapBuildRun(ctx, fields, v2a_runway, v2a_trend, v2a_wave, v2a_risk_score, decision.direction);

   FileWrite(handle,
             g_snrRunId,
             candidate_id,
             TimeToString(ctx.decision_time_server, TIME_DATE | TIME_MINUTES | TIME_SECONDS),
             TimeToString(ctx.decision_time_utc, TIME_DATE | TIME_MINUTES | TIME_SECONDS),
             _Symbol,
             EnumToString(_Period),
             TimeToString(closed_bar, TIME_DATE | TIME_MINUTES | TIME_SECONDS),
             SNR_DirectionName(decision.direction),
             ctx.session_bucket,
             SNR_CleanTesterString(g_variantTag),
             SNR_CleanTesterString(g_researchLaneTag),
             decision.setup_state,
             setup_type,
             decision.fx_v2a_old_state_gate_reason,
             decision.fx_v2a_old_late_chase_trap_reason,
             "true",
             decision.fx_v2a_decision,
             decision.fx_v2a_reason_codes,
             decision.fx_v2a_final_action,
             order_send_attempted,
             order_send_result,
             v2a_wave,
             DoubleToString(fields.source_classic_wave_smoothness, 3),
             fields.source_classic_dragon_state,
             DoubleToString(fields.source_classic_dragon_expansion, 3),
             DoubleToString(dragon_extension, 3),
             DoubleToString(dragon_overlap, 4),
             DoubleToString(sr_runway_pips, 2),
             fields.source_sr_interaction,
             DoubleToString(ctx.level_distance_pips, 2),
             v2a_chase,
             v2a_trap,
             fields.source_classic_session_runway,
             v2a_trend,
             ctx.h1_bias,
             ctx.h4_bias,
             DoubleToString(fields.seq_5_close_delta_pips, 2),
             DoubleToString(fields.seq_5_net_range_atr, 3),
             fields.source_pva_event,
             ctx.pvsra_event,
             ctx.spread_regime,
             ctx.minutes_to_forced_flat,
             DoubleToString(entry_price, _Digits),
             DoubleToString(planned_sl, _Digits),
             DoubleToString(planned_tp, _Digits),
             DoubleToString(risk_points, 1),
             DoubleToString(risk_pips, 2),
             min_stop_check,
             (g_useOrderCalcRiskSizing ? "order_calc" : "tick_value"),
             fail_closed_reason);
   FileClose(handle);
}

void SNR_LogDecisionBundle(const SnrContext &ctx, const SnrDecision &decision, const string outcome)
{
//if(outcome == "BLOCKED" && decision.wave_id == "" && !decision.fx_v2a_evaluated)
//return;

   SNR_LogDecision(ctx, decision, outcome);
   SnrPvsraSrFields pvsra_sr_fields;
   SNR_BuildPvsraSrFields(g_pipSize, ctx.atr, pvsra_sr_fields);
   SNR_AnnotateSourceClassicFields(ctx, decision.direction, pvsra_sr_fields);
   SNR_AnnotateSonicTraderState(ctx, decision.direction, pvsra_sr_fields);
   SNR_LogPvsraSrFields(ctx, decision, outcome, pvsra_sr_fields);
   SNR_LogFxChaseTrapV2ADiagnostic(ctx, decision, outcome, pvsra_sr_fields);
   SNR_LogGoldRegimeContext(ctx, decision, outcome);
   SNR_LogOpportunityBundle(ctx, decision, outcome, g_shadowLong, g_shadowShort);
   if(decision.mode != SNR_MODE_BLOCKED || outcome != "BLOCKED")
      SNR_LogRegimeState(ctx, "CANDIDATE");
}

ENUM_ORDER_TYPE_FILLING SNR_DetectFillMode()
{
   long modes = SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
   if((modes & SYMBOL_FILLING_FOK) != 0) return ORDER_FILLING_FOK;
   if((modes & SYMBOL_FILLING_IOC) != 0) return ORDER_FILLING_IOC;
   return ORDER_FILLING_RETURN;
}

void SNR_DailyReset(const datetime server_time)
{
   MqlDateTime now;
   TimeToStruct(server_time, now);
   datetime today = StringToTime(StringFormat("%04d.%02d.%02d", now.year, now.mon, now.day));
   if(today != g_lastTradeDay)
   {
      g_lastTradeDay = today;
      g_tradesToday = 0;
      g_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   }
}

void SNR_ResetLaneLosses(const datetime server_time, const string session_bucket)
{
   MqlDateTime now;
   TimeToStruct(server_time, now);
   datetime today = StringToTime(StringFormat("%04d.%02d.%02d", now.year, now.mon, now.day));
   if(today == g_laneLossDay && session_bucket == g_laneLossSession)
      return;

   g_laneLossDay = today;
   g_laneLossSession = session_bucket;
   g_laneLossXauT1 = 0;
   g_laneLossXauR1 = 0;
   g_laneLossXauS1 = 0;
   g_laneLossEurT1 = 0;
   g_laneLossEurB1 = 0;
}

double SNR_CalcInitialRiskAccount(const int direction,
                                  const double volume,
                                  const double entry_price,
                                  const double stop_loss)
{
   if(direction == SNR_DIR_NONE || volume <= 0.0 || entry_price <= 0.0 || stop_loss <= 0.0 ||
      MathAbs(entry_price - stop_loss) < _Point)
      return 0.0;

   ENUM_ORDER_TYPE order_type = (direction > 0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double stop_pnl = 0.0;
   ResetLastError();
   if(!OrderCalcProfit(order_type, _Symbol, volume, entry_price, stop_loss, stop_pnl) ||
      !MathIsValidNumber(stop_pnl))
      return 0.0;
   return MathAbs(stop_pnl);
}

void SNR_ResetOpenTrade(SnrOpenTrade &trade)
{
   trade.active = false;
   trade.position_id = 0;
   trade.entry_deal = 0;
   trade.order_ticket = 0;
   trade.entry_server_ts = 0;
   trade.entry_utc_ts = 0;
   trade.direction = SNR_DIR_NONE;
   trade.mode = SNR_MODE_BLOCKED;
   trade.wave_id = "";
   trade.entry_reason = "";
   trade.archetype = "";
   trade.level_zone = "";
   trade.session_bucket = "";
   trade.news_distance_min = 0;
   trade.pvsra_grade = 0;
   trade.context_score = 0.0;
   trade.quality_score = 0.0;
   trade.volume = 0.0;
   trade.entry_price = 0.0;
   trade.stop_loss = 0.0;
   trade.take_profit = 0.0;
   trade.risk_points = 0.0;
   trade.initial_risk_account = 0.0;
   trade.max_favorable_r = 0.0;
   trade.trap_manage = false;
   trade.trap_manage_bars = 0;
   trade.trap_manage_min_mfe_r = 0.0;
   trade.pending_close_reason = "";
   trade.last_modify_time = 0;
}

SnrMode SNR_ModeFromPositionComment(const string comment)
{
   string text = SNR_ToUpper(comment);
   if(StringFind(text, "XAU_S1_SWEEP_RECLAIM_SCAN") >= 0)
      return SNR_MODE_XAU_SWEEP_RECLAIM_SCAN;
   if(StringFind(text, "XAU_S1_SWEEP_RECLAIM") >= 0)
      return SNR_MODE_XAU_SWEEP_RECLAIM;
   if(StringFind(text, "XAU_T1_ACTIVE_CLASSIC") >= 0)
      return SNR_MODE_XAU_ACTIVE_CLASSIC;
   if(StringFind(text, "XAU_R1_RANGE_ABSORPTION") >= 0)
      return SNR_MODE_XAU_RANGE_ABSORPTION;
   if(StringFind(text, "EUR_T1_CLASSIC") >= 0)
      return SNR_MODE_EUR_TREND_CLASSIC;
   if(StringFind(text, "EUR_B1_ASIAN_BOX_RETEST") >= 0)
      return SNR_MODE_EUR_ASIAN_BOX_RETEST;
   if(StringFind(text, "CONTINUATION") >= 0)
      return SNR_MODE_CONTINUATION;
   if(StringFind(text, "REENTRY") >= 0)
      return SNR_MODE_REENTRY;
   if(StringFind(text, "SCOUT2") >= 0)
      return SNR_MODE_SCOUT2;
   return SNR_MODE_CLASSIC;
}

void SNR_RebuildOpenTradesFromPositions()
{
   ArrayResize(g_openTrades, 0);
   int rebuilt = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket))
         continue;
      if((int)PositionGetInteger(POSITION_MAGIC) != g_magic || PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;

      int idx = ArraySize(g_openTrades);
      ArrayResize(g_openTrades, idx + 1);
      SNR_ResetOpenTrade(g_openTrades[idx]);

      ENUM_POSITION_TYPE pos_type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      double open_price = PositionGetDouble(POSITION_PRICE_OPEN);
      double stop_loss = PositionGetDouble(POSITION_SL);
      double current_price = (pos_type == POSITION_TYPE_BUY ? g_sym.Bid() : g_sym.Ask());

      g_openTrades[idx].active = true;
      g_openTrades[idx].position_id = (ulong)PositionGetInteger(POSITION_IDENTIFIER);
      g_openTrades[idx].order_ticket = ticket;
      g_openTrades[idx].entry_server_ts = (datetime)PositionGetInteger(POSITION_TIME);
      g_openTrades[idx].entry_utc_ts = SNR_ServerToUTC(g_openTrades[idx].entry_server_ts);
      g_openTrades[idx].direction = (pos_type == POSITION_TYPE_BUY ? SNR_DIR_LONG : SNR_DIR_SHORT);
      g_openTrades[idx].mode = SNR_ModeFromPositionComment(PositionGetString(POSITION_COMMENT));
      g_openTrades[idx].wave_id = "RESTORED";
      g_openTrades[idx].entry_reason = "RESTORED_POSITION";
      g_openTrades[idx].archetype = "RestoredLivePosition";
      g_openTrades[idx].session_bucket = "RESTORED";
      g_openTrades[idx].volume = PositionGetDouble(POSITION_VOLUME);
      g_openTrades[idx].entry_price = open_price;
      g_openTrades[idx].stop_loss = stop_loss;
      g_openTrades[idx].take_profit = PositionGetDouble(POSITION_TP);
      g_openTrades[idx].risk_points = (stop_loss > 0.0 ? MathAbs(open_price - stop_loss) / _Point : 0.0);
      g_openTrades[idx].initial_risk_account = SNR_CalcInitialRiskAccount(g_openTrades[idx].direction,
                                                                          g_openTrades[idx].volume,
                                                                          open_price,
                                                                          stop_loss);
      if(g_openTrades[idx].risk_points > 0.0)
      {
         double move_points = (g_openTrades[idx].direction > 0 ?
                               (current_price - open_price) :
                               (open_price - current_price)) / _Point;
         g_openTrades[idx].max_favorable_r = MathMax(0.0, move_points / g_openTrades[idx].risk_points);
      }
      rebuilt++;
   }
   if(rebuilt > 0)
      PrintFormat("[SNR] Rebuilt %d managed open trade record(s) from live positions", rebuilt);
}

bool SNR_XauTrapManagementCandidate(const SnrContext &ctx, const SnrDecision &decision)
{
   if(!g_useXauTrapManagementRouter)
      return false;
   if(!SNR_XauClassicStateQualitySymbol() || _Period != PERIOD_M5)
      return false;
   if(!SNR_XauClassicStateQualityMode(decision.mode))
      return false;
   if(decision.direction == SNR_DIR_NONE || ctx.atr <= 0.0)
      return false;

   string block_reason = SNR_OpportunityBlockReason(ctx, decision);
   double structure_score = SNR_OpportunityStructureScore(ctx, decision.direction);
   double htf_score = SNR_OpportunityHtfScore(ctx, decision.direction);
   double pvsra_score = SNR_OpportunityPvsraScore(ctx, decision.direction);
   double level_score = SNR_OpportunityLevelScore(ctx);
   double time_safety_score = SNR_OpportunityTimeSafetyScore(ctx);
   double penalty = SNR_OpportunityPenalty(ctx, block_reason);
   double scalp_score = SNR_Clamp(structure_score + htf_score + pvsra_score + level_score + time_safety_score - penalty, 0.0, 100.0);
   if(scalp_score < g_xauTrapManageMinScore)
      return false;

   MqlDateTime dt;
   TimeToStruct(ctx.decision_time_server, dt);

   bool ny_long = (decision.direction > 0 && ctx.session_bucket == "NEWYORK");
   bool late_hour = (g_xauTrapManageLateHour >= 0 && dt.hour >= g_xauTrapManageLateHour);
   bool thursday_extension = false;
   if(g_xauTrapManageThursdayExtensionAtr > 0.0 && SNR_WeekdayTag(ctx.decision_time_server) == "Thursday")
   {
      double pip_size = SNR_CurrentPipSize();
      SnrPvsraSrFields fields;
      if(pip_size > 0.0 && SNR_BuildPvsraSrFields(pip_size, ctx.atr, fields) && fields.data_available)
      {
         double extension = SNR_StateTelemetryExtensionFromDragonAtr(ctx, fields, decision.direction);
         thursday_extension = (extension >= g_xauTrapManageThursdayExtensionAtr);
      }
   }

   return (ny_long || late_hour || thursday_extension);
}

int SNR_FindOpenTradeIndex(const ulong position_id)
{
   for(int i = 0; i < ArraySize(g_openTrades); i++)
   {
      if(g_openTrades[i].active && g_openTrades[i].position_id == position_id)
         return i;
   }
   return -1;
}

bool SNR_PositionIdStillOpen(const ulong position_id)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket))
         continue;
      if((ulong)PositionGetInteger(POSITION_IDENTIFIER) == position_id &&
         (int)PositionGetInteger(POSITION_MAGIC) == g_magic &&
         PositionGetString(POSITION_SYMBOL) == _Symbol)
      {
         return true;
      }
   }
   return false;
}

void SNR_SetPendingCloseReason(const ulong position_id, const string reason)
{
   int idx = SNR_FindOpenTradeIndex(position_id);
   if(idx >= 0)
      g_openTrades[idx].pending_close_reason = reason;
}

void SNR_RemoveOpenTrade(const ulong position_id)
{
   int idx = SNR_FindOpenTradeIndex(position_id);
   if(idx >= 0)
      SNR_ResetOpenTrade(g_openTrades[idx]);
}

bool SNR_GetOpenTrade(const ulong position_id, SnrOpenTrade &trade)
{
   int idx = SNR_FindOpenTradeIndex(position_id);
   if(idx < 0)
      return false;
   trade = g_openTrades[idx];
   return true;
}

void SNR_RegisterOpenTrade(const SnrContext &ctx,
                           const SnrDecision &decision,
                           const ulong deal_ticket,
                           const ulong order_ticket,
                           const double stop_loss,
                           const double take_profit,
                           const bool preserve_existing_metadata)
{
   if(!HistoryDealSelect(deal_ticket))
      return;

   ulong position_id = (ulong)HistoryDealGetInteger(deal_ticket, DEAL_POSITION_ID);
   if(position_id == 0)
      return;

   double fill_volume = HistoryDealGetDouble(deal_ticket, DEAL_VOLUME);
   double fill_price = HistoryDealGetDouble(deal_ticket, DEAL_PRICE);
   datetime fill_server_ts = (datetime)HistoryDealGetInteger(deal_ticket, DEAL_TIME);
   ulong fill_order_ticket = (ulong)HistoryDealGetInteger(deal_ticket, DEAL_ORDER);
   ENUM_DEAL_TYPE fill_type = (ENUM_DEAL_TYPE)HistoryDealGetInteger(deal_ticket, DEAL_TYPE);
   int fill_direction = (fill_type == DEAL_TYPE_BUY ? SNR_DIR_LONG :
                         fill_type == DEAL_TYPE_SELL ? SNR_DIR_SHORT : SNR_DIR_NONE);
   if(fill_volume <= 0.0 || fill_price <= 0.0 || fill_server_ts <= 0 ||
      fill_direction == SNR_DIR_NONE || fill_direction != decision.direction)
      return;
   if(fill_order_ticket == 0)
      fill_order_ticket = order_ticket;

   double effective_stop_loss = stop_loss;
   double effective_take_profit = take_profit;
   for(int position_index = PositionsTotal() - 1; position_index >= 0; position_index--)
   {
      ulong position_ticket = PositionGetTicket(position_index);
      if(position_ticket == 0 || !PositionSelectByTicket(position_ticket))
         continue;
      if((ulong)PositionGetInteger(POSITION_IDENTIFIER) != position_id ||
         (int)PositionGetInteger(POSITION_MAGIC) != g_magic ||
         PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      effective_stop_loss = PositionGetDouble(POSITION_SL);
      effective_take_profit = PositionGetDouble(POSITION_TP);
      break;
   }

   // One immutable OPEN row per actual deal. This stays deal-level even when
   // the account nets multiple fills into one position or IOC returns a
   // partial volume.
   SnrOpenTrade fill_log;
   SNR_ResetOpenTrade(fill_log);
   fill_log.active = true;
   fill_log.position_id = position_id;
   fill_log.entry_deal = deal_ticket;
   fill_log.order_ticket = fill_order_ticket;
   fill_log.entry_server_ts = fill_server_ts;
   fill_log.entry_utc_ts = SNR_ServerToUTC(fill_server_ts);
   fill_log.direction = fill_direction;
   fill_log.mode = decision.mode;
   fill_log.wave_id = decision.wave_id;
   fill_log.entry_reason = SNR_DecisionReasonKey(decision);
   fill_log.archetype = decision.archetype;
   fill_log.level_zone = decision.level_zone;
   fill_log.session_bucket = ctx.session_bucket;
   fill_log.news_distance_min = ctx.news_distance_min;
   fill_log.pvsra_grade = decision.pvsra_grade;
   fill_log.context_score = decision.context_score;
   fill_log.quality_score = decision.quality_score;
   fill_log.volume = fill_volume;
   fill_log.entry_price = fill_price;
   fill_log.stop_loss = effective_stop_loss;
   fill_log.take_profit = effective_take_profit;
   fill_log.risk_points = MathAbs(fill_price - effective_stop_loss) / _Point;
   fill_log.initial_risk_account = SNR_CalcInitialRiskAccount(fill_direction,
                                                              fill_volume,
                                                              fill_price,
                                                              effective_stop_loss);
   fill_log.max_favorable_r = 0.0;
   fill_log.trap_manage = SNR_XauTrapManagementCandidate(ctx, decision);
   fill_log.trap_manage_bars = MathMax(1, g_xauTrapManageBars);
   fill_log.trap_manage_min_mfe_r = MathMax(0.0, g_xauTrapManageMinMfeR);

   int idx = SNR_FindOpenTradeIndex(position_id);
   bool existing_record = (idx >= 0);
   bool preserve_record = (preserve_existing_metadata && existing_record);
   if(idx < 0)
   {
      int size = ArraySize(g_openTrades);
      for(int i = 0; i < size; i++)
      {
         if(!g_openTrades[i].active)
         {
            idx = i;
            break;
         }
      }
      if(idx < 0)
      {
         idx = size;
         ArrayResize(g_openTrades, idx + 1);
      }
      g_openTrades[idx] = fill_log;
   }
   else
   {
      double old_volume = g_openTrades[idx].volume;
      double new_volume = old_volume + fill_volume;
      if(new_volume > 0.0)
         g_openTrades[idx].entry_price = ((g_openTrades[idx].entry_price * old_volume) + (fill_price * fill_volume)) / new_volume;
      g_openTrades[idx].volume = new_volume;
      if(!preserve_record)
      {
         g_openTrades[idx].mode = decision.mode;
         g_openTrades[idx].wave_id = decision.wave_id;
         g_openTrades[idx].entry_reason = SNR_DecisionReasonKey(decision);
         g_openTrades[idx].context_score = decision.context_score;
         g_openTrades[idx].quality_score = decision.quality_score;
         g_openTrades[idx].pvsra_grade = decision.pvsra_grade;
         g_openTrades[idx].news_distance_min = ctx.news_distance_min;
         g_openTrades[idx].session_bucket = ctx.session_bucket;
         g_openTrades[idx].trap_manage = SNR_XauTrapManagementCandidate(ctx, decision);
         g_openTrades[idx].trap_manage_bars = MathMax(1, g_xauTrapManageBars);
         g_openTrades[idx].trap_manage_min_mfe_r = MathMax(0.0, g_xauTrapManageMinMfeR);
      }
   }

   if(!preserve_record)
   {
      g_openTrades[idx].stop_loss = effective_stop_loss;
      g_openTrades[idx].take_profit = effective_take_profit;
   }
   double aggregate_stop = (preserve_record ? g_openTrades[idx].stop_loss : effective_stop_loss);
   g_openTrades[idx].risk_points = MathAbs(g_openTrades[idx].entry_price - aggregate_stop) / _Point;
   g_openTrades[idx].initial_risk_account = SNR_CalcInitialRiskAccount(g_openTrades[idx].direction,
                                                                       g_openTrades[idx].volume,
                                                                       g_openTrades[idx].entry_price,
                                                                       aggregate_stop);

   SNR_LogPx6TradeOpen(fill_log);
}

double SNR_ModeRiskPct(const SnrMode mode)
{
   if(mode == SNR_MODE_XAU_RANGE_ABSORPTION)
      return g_rangeLaneRiskPct;
   if(mode == SNR_MODE_XAU_ACTIVE_CLASSIC ||
      mode == SNR_MODE_XAU_SWEEP_RECLAIM ||
      mode == SNR_MODE_EUR_TREND_CLASSIC ||
      mode == SNR_MODE_EUR_ASIAN_BOX_RETEST)
      return g_scalpLaneRiskPct;
   if(mode == SNR_MODE_CLASSIC)
      return g_classicRiskPct;
   if(mode == SNR_MODE_BLOCKED || mode == SNR_MODE_XAU_SWEEP_RECLAIM_SCAN)
      return 0.0;
   return g_secondLayerRiskPct;
}

int SNR_CountManagedPositions()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!g_pos.SelectByIndex(i))
         continue;
      if(g_pos.Magic() == g_magic && g_pos.Symbol() == _Symbol)
         count++;
   }
   return count;
}

double SNR_CurrentNarrativeRiskUsedPct()
{
   double risk_used = 0.0;
   for(int i = 0; i < ArraySize(g_openTrades); i++)
   {
      if(!g_openTrades[i].active)
         continue;
      if(!SNR_PositionIdStillOpen(g_openTrades[i].position_id))
         continue;
      risk_used += SNR_ModeRiskPct(g_openTrades[i].mode);
   }
   if(risk_used > 0.0)
      return risk_used;

   if(g_narrative.layers_opened <= 0)
      return 0.0;
   if(g_narrative.layers_opened == 1)
      return g_classicRiskPct;
   return g_classicRiskPct + g_secondLayerRiskPct;
}

int SNR_CurrentLaneLosses(const SnrMode mode)
{
   if(mode == SNR_MODE_XAU_ACTIVE_CLASSIC)
      return g_laneLossXauT1;
   if(mode == SNR_MODE_XAU_RANGE_ABSORPTION)
      return g_laneLossXauR1;
   if(mode == SNR_MODE_XAU_SWEEP_RECLAIM)
      return g_laneLossXauS1;
   if(mode == SNR_MODE_EUR_TREND_CLASSIC)
      return g_laneLossEurT1;
   if(mode == SNR_MODE_EUR_ASIAN_BOX_RETEST)
      return g_laneLossEurB1;
   return 0;
}

bool SNR_LaneLossLimitHit(const SnrMode mode)
{
   if(!g_useRegimeRouter || g_maxLaneLossesPerSession <= 0)
      return false;
   if(mode != SNR_MODE_XAU_ACTIVE_CLASSIC &&
      mode != SNR_MODE_XAU_RANGE_ABSORPTION &&
      mode != SNR_MODE_XAU_SWEEP_RECLAIM &&
      mode != SNR_MODE_EUR_TREND_CLASSIC &&
      mode != SNR_MODE_EUR_ASIAN_BOX_RETEST)
      return false;
   return (SNR_CurrentLaneLosses(mode) >= g_maxLaneLossesPerSession);
}

void SNR_NoteLaneLoss(const SnrMode mode)
{
   if(mode == SNR_MODE_XAU_ACTIVE_CLASSIC)
      g_laneLossXauT1++;
   else if(mode == SNR_MODE_XAU_RANGE_ABSORPTION)
      g_laneLossXauR1++;
   else if(mode == SNR_MODE_XAU_SWEEP_RECLAIM)
      g_laneLossXauS1++;
   else if(mode == SNR_MODE_EUR_TREND_CLASSIC)
      g_laneLossEurT1++;
   else if(mode == SNR_MODE_EUR_ASIAN_BOX_RETEST)
      g_laneLossEurB1++;
}

void SNR_SyncNarrative()
{
   if(SNR_CountManagedPositions() <= 0)
   {
      SNR_ResetNarrative(g_narrative);
   }
}

void SNR_ArmClassicSetup(const SnrContext &ctx,
                         const SnrSignal &candidate)
{
   if(!g_useArmedClassic || !candidate.valid)
      return;

   int arm_seconds = MathMax(1, g_classicArmBars) * PeriodSeconds(PERIOD_CURRENT);
   if(arm_seconds <= 0)
      arm_seconds = MathMax(1, g_classicArmBars) * 60;

   g_classicArm.active = true;
   g_classicArm.direction = candidate.direction;
   g_classicArm.armed_at = ctx.decision_time_server;
   g_classicArm.expires_at = ctx.decision_time_server + arm_seconds;
   g_classicArm.wave_id = candidate.wave_id;
   g_classicArm.archetype = candidate.archetype;
   g_classicArm.setup_state = "ARMED";
   g_classicArm.level_zone = ctx.level_zone;
   g_classicArm.pvsra_grade = SNR_DirectionalPvsraGrade(ctx, candidate.direction);
   g_classicArm.context_score = ctx.context_score;
   g_classicArm.quality_score = candidate.quality_score;
   g_classicArm.pullback_depth_atr = candidate.pullback_depth_atr;
   g_classicArm.trigger_price = candidate.trigger_price;
   g_classicArm.stop_price = candidate.stop_price;
   g_classicArm.target_rr = candidate.target_rr;
}

void SNR_ConsiderClassicArm(const SnrContext &ctx)
{
   if(!g_useArmedClassic || g_narrative.active)
      return;
   if(ctx.entry_blocked || ctx.force_flat_now || ctx.session_bucket == "OFF")
      return;

   SnrSignal best;
   SNR_ResetSignal(best, SNR_MODE_BLOCKED, SNR_DIR_NONE);

   SnrSignal long_arm, short_arm;
   SNR_FindClassicArmCandidate(ctx, SNR_DIR_LONG, g_hDragonHigh, g_hDragonMid, g_hDragonLow, g_hATR, long_arm);
   SNR_FindClassicArmCandidate(ctx, SNR_DIR_SHORT, g_hDragonHigh, g_hDragonMid, g_hDragonLow, g_hATR, short_arm);
   SNR_ChooseSignal(long_arm, best);
   SNR_ChooseSignal(short_arm, best);

   if(!best.valid)
      return;

   bool replace = !g_classicArm.active ||
                  g_classicArm.wave_id != best.wave_id ||
                  best.quality_score > g_classicArm.quality_score;
   if(replace)
      SNR_ArmClassicSetup(ctx, best);
}

bool SNR_BuildArmedClassicDecision(const SnrContext &ctx, SnrDecision &decision)
{
   if(!g_useArmedClassic || !g_classicArm.active)
      return false;
   if(g_narrative.active)
   {
      SNR_ResetClassicArm(g_classicArm);
      return false;
   }
   if(ctx.decision_time_server > g_classicArm.expires_at || ctx.force_flat_now)
   {
      SNR_ResetClassicArm(g_classicArm);
      return false;
   }
   if(ctx.entry_blocked || ctx.session_bucket == "OFF")
   {
      SNR_ResetClassicArm(g_classicArm);
      return false;
   }

   bool context_ok = (g_classicArm.direction > 0 ? ctx.allow_long : ctx.allow_short);
   if(!context_ok)
   {
      SNR_ResetClassicArm(g_classicArm);
      return false;
   }

   MqlRates rates[];
   if(!SNR_CopyClosedRates(1, rates))
      return false;

   bool triggered = (g_classicArm.direction > 0 ?
                     rates[0].close >= g_classicArm.trigger_price :
                     rates[0].close <= g_classicArm.trigger_price);
   if(!triggered)
      return false;

   bool candle_confirms = (g_classicArm.direction > 0 ?
                           rates[0].close > rates[0].open :
                           rates[0].close < rates[0].open);
   if(!candle_confirms)
      return false;

   decision.should_trade = true;
   decision.mode = SNR_MODE_CLASSIC;
   decision.direction = g_classicArm.direction;
   decision.block_reason = "";
   decision.wave_id = g_classicArm.wave_id;
   decision.archetype = g_classicArm.archetype;
   decision.setup_state = "TRIGGER";
   decision.invalidate_reason = "";
   decision.context_score = ctx.context_score;
   decision.pvsra_grade = MathMax(g_classicArm.pvsra_grade, SNR_DirectionalPvsraGrade(ctx, g_classicArm.direction));
   decision.level_zone = g_classicArm.level_zone;
   decision.stop_price = g_classicArm.stop_price;
   decision.target_rr = g_classicArm.target_rr;
   decision.quality_score = g_classicArm.quality_score + 0.20 * decision.pvsra_grade;
   decision.pullback_depth_atr = g_classicArm.pullback_depth_atr;
   SNR_ResetFxChaseTrapV2ADiagnostic(decision);
   return true;
}

double SNR_NormalizeLots(const double raw_lots)
{
   if(raw_lots <= 0.0)
      return 0.0;

   double lot_min  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double lot_max  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lot_step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(lot_step <= 0.0)
      lot_step = 0.01;

   double lots = MathFloor((raw_lots + 1e-9) / lot_step) * lot_step;
   lots = MathMin(lots, MathMin(lot_max, g_maxLot));
   
   if(lots < lot_min)
      lots = 0.0;

   int lot_digits = 0;
   double step_val = lot_step;
   while(step_val < 0.9999 && lot_digits < 8)
   {
      step_val *= 10.0;
      lot_digits++;
   }
   lots = NormalizeDouble(lots, lot_digits);
   
   return lots;
}

int SNR_RequiredWarmupBars()
{
   int warmup = 60;
   warmup = MathMax(warmup, g_dragonPeriod + g_slopeLookbackBars + 12);
   warmup = MathMax(warmup, g_trendPeriod + 12);
   warmup = MathMax(warmup, g_atrPeriod + 12);
   warmup = MathMax(warmup, g_waveLookbackBars + 24);
   warmup = MathMax(warmup, g_breakoutLookbackBars + 24);
   warmup = MathMax(warmup, g_reentryLookbackBars + 24);
   warmup = MathMax(warmup, g_continuationLookbackBars + 24);
   warmup = MathMax(warmup, g_dragonPullbackLookbackBars + 24);
   return MathMax(120, warmup);
}

bool SNR_MarginPrecheck(const int direction,
                        const double lots,
                        const double entry_price,
                        double &margin_required,
                        double &margin_free)
{
   margin_required = 0.0;
   margin_free = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   ENUM_ORDER_TYPE calc_type = (direction > 0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   ResetLastError();
   if(!OrderCalcMargin(calc_type, _Symbol, lots, entry_price, margin_required) ||
      margin_required <= 0.0 ||
      margin_free <= 0.0 ||
      margin_required > margin_free)
   {
      int err = GetLastError();
      PrintFormat("[SNR] Margin precheck blocked | symbol=%s lots=%.2f entry=%.5f required=%.2f free=%.2f err=%d",
                  _Symbol,
                  lots,
                  entry_price,
                  margin_required,
                  margin_free,
                  err);
      return false;
   }
   return true;
}

bool SNR_ModifyAllManagedPositions(const double stop_loss, const double take_profit)
{
   bool ok_all = true;
   bool touched = false;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!g_pos.SelectByIndex(i))
         continue;
      if(g_pos.Magic() != g_magic || g_pos.Symbol() != _Symbol)
         continue;
      touched = true;
      if(!g_trade.PositionModify(g_pos.Ticket(),
                                 NormalizeDouble(stop_loss, g_digits),
                                 NormalizeDouble(take_profit, g_digits)))
      {
         ok_all = false;
      }
   }
   if(touched)
      SNR_NoteModify(ok_all);
   return ok_all;
}

void SNR_CaptureManagedPositionExits(ulong &tickets[], double &stop_losses[], double &take_profits[])
{
   ArrayResize(tickets, 0);
   ArrayResize(stop_losses, 0);
   ArrayResize(take_profits, 0);

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!g_pos.SelectByIndex(i))
         continue;
      if(g_pos.Magic() != g_magic || g_pos.Symbol() != _Symbol)
         continue;

      int idx = ArraySize(tickets);
      ArrayResize(tickets, idx + 1);
      ArrayResize(stop_losses, idx + 1);
      ArrayResize(take_profits, idx + 1);
      tickets[idx] = g_pos.Ticket();
      stop_losses[idx] = g_pos.StopLoss();
      take_profits[idx] = g_pos.TakeProfit();
   }
}

bool SNR_RestoreManagedPositionExits(const ulong &tickets[], const double &stop_losses[], const double &take_profits[])
{
   bool ok_all = true;
   bool touched = false;
   int count = MathMin(ArraySize(tickets), MathMin(ArraySize(stop_losses), ArraySize(take_profits)));
   for(int i = 0; i < count; i++)
   {
      if(tickets[i] == 0 || !PositionSelectByTicket(tickets[i]))
         continue;
      if((int)PositionGetInteger(POSITION_MAGIC) != g_magic || PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;

      touched = true;
      if(!g_trade.PositionModify(tickets[i],
                                 NormalizeDouble(stop_losses[i], g_digits),
                                 NormalizeDouble(take_profits[i], g_digits)))
      {
         ok_all = false;
      }
   }
   if(touched)
      SNR_NoteModify(ok_all);
   return ok_all;
}

void SNR_CloseManagedPositions(const string reason)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!g_pos.SelectByIndex(i))
         continue;
      if(g_pos.Magic() != g_magic || g_pos.Symbol() != _Symbol)
         continue;

      ulong ticket = g_pos.Ticket();
      ulong position_id = (ulong)PositionGetInteger(POSITION_IDENTIFIER);
      SNR_SetPendingCloseReason(position_id, reason);
      bool ok = g_trade.PositionClose(ticket);
      SNR_NoteCloseRequest(ok);
      if(!ok)
         SNR_SetPendingCloseReason(position_id, "");
      if(ok)
         PrintFormat("[SNR] FLAT %s | ticket=%I64u", reason, ticket);
      else
         PrintFormat("[SNR] FLAT FAIL %s | ticket=%I64u | retcode=%d %s",
                     reason,
                     ticket,
                     g_trade.ResultRetcode(),
                     g_trade.ResultRetcodeDescription());
   }
}

bool SNR_CloseManagedPositionId(const ulong position_id, const string reason)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket))
         continue;
      if((ulong)PositionGetInteger(POSITION_IDENTIFIER) != position_id)
         continue;
      if((int)PositionGetInteger(POSITION_MAGIC) != g_magic || PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;

      SNR_SetPendingCloseReason(position_id, reason);
      bool ok = g_trade.PositionClose(ticket);
      SNR_NoteCloseRequest(ok);
      if(!ok)
         SNR_SetPendingCloseReason(position_id, "");
      if(ok)
         PrintFormat("[SNR] FLAT %s | ticket=%I64u", reason, ticket);
      else
         PrintFormat("[SNR] FLAT FAIL %s | ticket=%I64u | retcode=%d %s",
                     reason,
                     ticket,
                     g_trade.ResultRetcode(),
                     g_trade.ResultRetcodeDescription());
      return ok;
   }
   return false;
}

bool SNR_RiskLocked()
{
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_dayStartEquity > 0.0)
   {
      double dd_day = (g_dayStartEquity - equity) / g_dayStartEquity * 100.0;
      if(dd_day >= g_dailyLossLockPct)
      {
         g_lastStatus = "DAILY_LOSS_LOCK";
         return true;
      }
   }
   if(g_peakEquity > 0.0)
   {
      double dd_total = (g_peakEquity - equity) / g_peakEquity * 100.0;
      if(dd_total >= g_maxEquityDrawdownPct)
      {
         g_lastStatus = "EQUITY_DD_LOCK";
         return true;
      }
   }
   return false;
}

bool SNR_ShouldClockForceFlat(const datetime server_time, string &reason)
{
   MqlDateTime dt;
   TimeToStruct(server_time, dt);
   int now_min = SNR_ServerMinutesOfDay(server_time);

   if(dt.day_of_week == 0 || dt.day_of_week == 6)
   {
      reason = "WEEKEND";
      return true;
   }

   if(dt.day_of_week == 5 && now_min >= SNR_MinutesOfDay(g_fridayFlatHour, g_fridayFlatMinute))
   {
      reason = "FRIDAY_FLAT";
      return true;
   }

   // Tránh tự động đóng vị thế trong giờ Rollover spread giãn rộng (23:45 - 01:15)
   if(now_min >= 1425 || now_min < 75)
   {
      return false;
   }

   int hard_flat_min = SNR_MinutesOfDay(g_hardFlatHour, g_hardFlatMinute);
   if(now_min >= hard_flat_min)
   {
      reason = "HARD_FLAT";
      return true;
   }

   if(g_forceFlatOutsideSession && SNR_SessionBucket(server_time) == "OFF")
   {
      reason = "SESSION_END";
      return true;
   }

   return false;
}

void SNR_ManageBreakEven()
{
   if(!g_useBreakEven)
      return;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!g_pos.SelectByIndex(i))
         continue;
      if(g_pos.Magic() != g_magic || g_pos.Symbol() != _Symbol)
         continue;

      double open_price = g_pos.PriceOpen();
      double stop_loss  = g_pos.StopLoss();
      double take_profit = g_pos.TakeProfit();
      double current_price = (g_pos.PositionType() == POSITION_TYPE_BUY) ? g_sym.Bid() : g_sym.Ask();

      double risk_dist = MathAbs(open_price - stop_loss);
      if(risk_dist <= 0.0)
         continue;

      bool already_be = false;
      if(g_pos.PositionType() == POSITION_TYPE_BUY)
         already_be = (stop_loss >= open_price);
      else
         already_be = (stop_loss > 0.0 && stop_loss <= open_price);
      if(already_be)
         continue;

      double trigger_dist = risk_dist * g_breakEvenTriggerR;
      bool triggered = false;
      if(g_pos.PositionType() == POSITION_TYPE_BUY)
         triggered = (current_price - open_price >= trigger_dist);
      else
         triggered = (open_price - current_price >= trigger_dist);
      if(!triggered)
         continue;

      ulong position_id = g_pos.Identifier();
      int trade_idx = SNR_FindOpenTradeIndex(position_id);
      if(trade_idx >= 0)
      {
         if(TimeCurrent() - g_openTrades[trade_idx].last_modify_time < 15)
         {
            continue;
         }
      }

      double new_sl = (g_pos.PositionType() == POSITION_TYPE_BUY) ?
                      NormalizeDouble(open_price + _Point, g_digits) :
                      NormalizeDouble(open_price - _Point, g_digits);
      bool ok = g_trade.PositionModify(g_pos.Ticket(), new_sl, take_profit);
      SNR_NoteModify(ok);

      if(trade_idx >= 0)
      {
         g_openTrades[trade_idx].last_modify_time = TimeCurrent();
      }
   }
}

void SNR_ManageScalpTimeStop()
{
   if(!g_useRegimeRouter && !g_useXauTrapManagementRouter)
      return;

   int period_seconds = PeriodSeconds(PERIOD_M5);
   if(period_seconds <= 0)
      period_seconds = 300;

   for(int i = 0; i < ArraySize(g_openTrades); i++)
   {
      if(!g_openTrades[i].active)
         continue;

      bool default_time_stop = (g_useRegimeRouter && g_openTrades[i].mode == SNR_MODE_XAU_ACTIVE_CLASSIC);
      bool trap_time_stop = (g_useXauTrapManagementRouter && g_openTrades[i].trap_manage);
      if(!default_time_stop && !trap_time_stop)
         continue;
      if(g_openTrades[i].risk_points <= 0.0)
         continue;

      ulong position_id = g_openTrades[i].position_id;
      if(!SNR_PositionIdStillOpen(position_id))
         continue;

      double current_price = (g_openTrades[i].direction > 0 ? g_sym.Bid() : g_sym.Ask());
      double move_points = (g_openTrades[i].direction > 0 ?
                            (current_price - g_openTrades[i].entry_price) :
                            (g_openTrades[i].entry_price - current_price)) / _Point;
      double current_r = move_points / g_openTrades[i].risk_points;
      if(current_r > g_openTrades[i].max_favorable_r)
         g_openTrades[i].max_favorable_r = current_r;

      int stop_bars = (trap_time_stop ? g_openTrades[i].trap_manage_bars : 6);
      double min_mfe_r = (trap_time_stop ? g_openTrades[i].trap_manage_min_mfe_r : 0.40);
      if(stop_bars < 1)
         stop_bars = 1;

      int bars_held = (int)((TimeCurrent() - g_openTrades[i].entry_server_ts) / period_seconds);
      if(bars_held >= stop_bars && g_openTrades[i].max_favorable_r < min_mfe_r)
      {
         string close_reason = (trap_time_stop ? "TRAP_TIME_STOP_NO_MFE" : "TIME_STOP_NO_MFE");
         g_lastStatus = close_reason;
         SNR_CloseManagedPositionId(position_id, close_reason);
      }
   }
}

void SNR_ManageStructuralTrailing(const SnrContext &ctx)
{
   if(!g_useStructuralTrailing)
      return;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!g_pos.SelectByIndex(i))
         continue;
      if(g_pos.Magic() != g_magic || g_pos.Symbol() != _Symbol)
         continue;

      double open_price = g_pos.PriceOpen();
      double stop_loss  = g_pos.StopLoss();
      double take_profit = g_pos.TakeProfit();
      double current_price = (g_pos.PositionType() == POSITION_TYPE_BUY) ? g_sym.Bid() : g_sym.Ask();

      double min_dist = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
      if(min_dist <= 0.0)
         min_dist = 2.0 * g_pipSize; // Safe fallback

      if(g_pos.PositionType() == POSITION_TYPE_BUY)
      {
         // Propose SL below current SMC Market Structure Low
         double proposed_sl = ctx.market_structure_low - g_stopAtrBuffer * ctx.atr;
         proposed_sl = NormalizeDouble(proposed_sl, g_digits);
         
         // Only trail up: proposed_sl must be higher than current stop_loss, and lower than current price by min_dist
         if(proposed_sl > stop_loss && current_price - proposed_sl >= min_dist)
         {
            bool ok = g_trade.PositionModify(g_pos.Ticket(), proposed_sl, take_profit);
            SNR_NoteModify(ok);
            if(ok)
               PrintFormat("[SNR] Trailed Long SL dynamically to structural low: %.5f | ticket=%I64u", proposed_sl, g_pos.Ticket());
         }
      }
      else
      {
         // Propose SL above current SMC Market Structure High
         double proposed_sl = ctx.market_structure_high + g_stopAtrBuffer * ctx.atr;
         proposed_sl = NormalizeDouble(proposed_sl, g_digits);
         
         // Only trail down: proposed_sl must be lower than current stop_loss (or stop_loss == 0), and higher than current price by min_dist
         if((stop_loss <= 0.0 || proposed_sl < stop_loss) && proposed_sl - current_price >= min_dist)
         {
            bool ok = g_trade.PositionModify(g_pos.Ticket(), proposed_sl, take_profit);
            SNR_NoteModify(ok);
            if(ok)
               PrintFormat("[SNR] Trailed Short SL dynamically to structural high: %.5f | ticket=%I64u", proposed_sl, g_pos.Ticket());
         }
      }
   }
}

void SNR_UpdateComment()
{
   if(MQLInfoInteger(MQL_TESTER))
      return;

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double dd_total = 0.0;
   if(g_peakEquity > 0.0)
      dd_total = (g_peakEquity - equity) / g_peakEquity * 100.0;

   string comment =
      StringFormat("[SNR v2] %s %s\n", _Symbol, EnumToString(_Period)) +
      StringFormat("Status: %s | Session: %s\n", g_lastStatus, SNR_SessionBucket(TimeCurrent())) +
      StringFormat("Trades today: %d/%d | Layers: %d/%d\n",
                   g_tradesToday, (g_useRegimeRouter ? g_maxScalpTradesPerDay : g_maxTradesPerDay), g_narrative.layers_opened, g_maxLayers) +
      StringFormat("Equity: %.2f | Peak DD: %.2f%%\n", equity, dd_total) +
      StringFormat("Narrative: %s %s",
                   SNR_DirectionName(g_narrative.direction),
                   g_narrative.wave_id);
   Comment(comment);
}

double SNR_MinSLPipsForDecision(const SnrDecision &decision)
{
   double min_sl_pips = g_minSLPips;
   if(g_scalpMinSLPips > 0.0 &&
      (decision.mode == SNR_MODE_XAU_ACTIVE_CLASSIC ||
       decision.mode == SNR_MODE_XAU_SWEEP_RECLAIM ||
       decision.mode == SNR_MODE_EUR_TREND_CLASSIC ||
       decision.mode == SNR_MODE_EUR_ASIAN_BOX_RETEST))
      min_sl_pips = g_scalpMinSLPips;
   if(decision.mode == SNR_MODE_CONTINUATION && g_continuationMinSLPips > 0.0)
      min_sl_pips = g_continuationMinSLPips;
   return min_sl_pips;
}

bool SNR_PrepareOrderParameters(const SnrDecision &decision,
                                const double risk_pct,
                                double &entry_price,
                                double &stop_loss,
                                double &take_profit,
                                double &lots,
                                double &sl_pips)
{
   entry_price = (decision.direction > 0 ? g_sym.Ask() : g_sym.Bid());
   stop_loss   = NormalizeDouble(decision.stop_price, g_digits);
   double sl_dist = (decision.direction > 0 ? entry_price - stop_loss : stop_loss - entry_price);
   sl_pips = sl_dist / g_pipSize;

   double min_sl_pips = SNR_MinSLPipsForDecision(decision);
   if(sl_pips < min_sl_pips && g_useClassicMinSLFloor)
   {
      sl_dist = min_sl_pips * g_pipSize;
      stop_loss = NormalizeDouble((decision.direction > 0 ? entry_price - sl_dist : entry_price + sl_dist), g_digits);
      sl_pips = min_sl_pips;
   }
   if(sl_pips < min_sl_pips || sl_pips > g_maxSLPips)
   {
      g_lastStatus = StringFormat("SL_REJECT %.1f", sl_pips);
      return false;
   }

   take_profit = (decision.direction > 0) ?
                 NormalizeDouble(entry_price + sl_dist * decision.target_rr, g_digits) :
                 NormalizeDouble(entry_price - sl_dist * decision.target_rr, g_digits);

   long stop_level_pts = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   long freeze_level_pts = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL);
   double min_dist = (double)MathMax(stop_level_pts, freeze_level_pts) * _Point;
   if(MathAbs(entry_price - stop_loss) < min_dist || MathAbs(entry_price - take_profit) < min_dist)
   {
      g_lastStatus = "BROKER_STOP_BLOCK";
      return false;
   }

   double risk_money = AccountInfoDouble(ACCOUNT_EQUITY) * risk_pct / 100.0;
   double raw_lots = 0.0;
   bool order_calc_failed = false;
   if(g_useOrderCalcRiskSizing)
   {
      double one_lot_sl_pnl = 0.0;
      ENUM_ORDER_TYPE calc_type = (decision.direction > 0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
      if(OrderCalcProfit(calc_type, _Symbol, 1.0, entry_price, stop_loss, one_lot_sl_pnl) &&
         one_lot_sl_pnl < 0.0)
         raw_lots = risk_money / MathAbs(one_lot_sl_pnl);
      else
         order_calc_failed = true;
   }

   bool is_gold = (StringFind(_Symbol, "XAU") >= 0);
   if(order_calc_failed && (g_orderCalcRiskFailClosed || is_gold))
   {
      g_lastStatus = "ORDERCALC_RISK_INVALID";
      PrintFormat("SNR risk sizing blocked: OrderCalcProfit invalid for %s entry %.5f stop %.5f. Fallback forbidden on Gold.",
                  _Symbol,
                  entry_price,
                  stop_loss);
      return false;
   }

   double tick_value = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tick_size  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(raw_lots <= 0.0 && (tick_value <= 0.0 || tick_size <= 0.0))
   {
      g_lastStatus = "TICKVALUE_INVALID";
      return false;
   }
   if(raw_lots <= 0.0)
      raw_lots = risk_money / (sl_dist / tick_size * tick_value);

   lots = SNR_NormalizeLots(raw_lots);
   if(lots < SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN))
   {
      g_lastStatus = "LOT_TOO_SMALL";
      return false;
   }

   double margin_required = 0.0;
   double margin_free = 0.0;
   if(!SNR_MarginPrecheck(decision.direction, lots, entry_price, margin_required, margin_free))
   {
      g_lastStatus = "MARGIN_PRECHECK_BLOCK";
      return false;
   }

   return true;
}

bool SNR_ExecuteDecision(const SnrContext &ctx, const SnrDecision &decision)
{
   double risk_pct = SNR_ModeRiskPct(decision.mode);
   if(SNR_LaneLossLimitHit(decision.mode))
   {
      g_lastStatus = "LANE_SESSION_LOSS_LIMIT";
      return false;
   }
   if(SNR_CurrentNarrativeRiskUsedPct() + risk_pct > g_maxNarrativeRiskPct)
   {
      g_lastStatus = "RISK_BUDGET_BLOCK";
      return false;
   }

   double entry_price = 0.0;
   double stop_loss = 0.0;
   double take_profit = 0.0;
   double lots = 0.0;
   double sl_pips = 0.0;
   if(!SNR_PrepareOrderParameters(decision, risk_pct, entry_price, stop_loss, take_profit, lots, sl_pips))
      return false;

   bool success = false;
   ulong deal_ticket = 0;
   ulong order_ticket = 0;
   uint fill_retcode = 0;
   string order_comment = SNR_CleanTesterString(g_comment) + "_" + SNR_ModeName(decision.mode);
   double request_price = entry_price;
   bool preserve_primary_exits = (g_preservePrimaryExitsOnScaleIn &&
                                  decision.mode != SNR_MODE_CLASSIC &&
                                  SNR_CountManagedPositions() > 0);
   ulong preserve_tickets[];
   double preserve_stop_losses[];
   double preserve_take_profits[];
   if(preserve_primary_exits)
      SNR_CaptureManagedPositionExits(preserve_tickets, preserve_stop_losses, preserve_take_profits);

   for(int attempt = 0; attempt <= g_retryCount; attempt++)
   {
      bool ok = false;
      g_sym.RefreshRates();
      if(!SNR_PrepareOrderParameters(decision, risk_pct, entry_price, stop_loss, take_profit, lots, sl_pips))
         break;
      request_price = entry_price;
      if(decision.direction > 0)
         ok = g_trade.Buy(lots, _Symbol, 0.0, stop_loss, take_profit, order_comment);
      else
         ok = g_trade.Sell(lots, _Symbol, 0.0, stop_loss, take_profit, order_comment);

      uint retcode = g_trade.ResultRetcode();
      if(ok && (retcode == TRADE_RETCODE_DONE || retcode == TRADE_RETCODE_DONE_PARTIAL))
      {
         success = true;
         deal_ticket = g_trade.ResultDeal();
         order_ticket = g_trade.ResultOrder();
         fill_retcode = retcode;
         break;
      }

      if(attempt < g_retryCount &&
         (retcode == TRADE_RETCODE_REQUOTE ||
          retcode == TRADE_RETCODE_PRICE_CHANGED ||
          retcode == TRADE_RETCODE_PRICE_OFF ||
          retcode == TRADE_RETCODE_TIMEOUT ||
          retcode == TRADE_RETCODE_CONNECTION))
      {
         Sleep(g_retryDelayMs * (attempt + 1));
         g_sym.RefreshRates();
         continue;
      }

      g_lastStatus = StringFormat("ORDER_REJECT_%d", retcode);
      PrintFormat("[SNR] ORDER FAIL | mode=%s | retcode=%d %s",
                  SNR_ModeName(decision.mode),
                  retcode,
                  g_trade.ResultRetcodeDescription());
      break;
   }

   if(!success)
      return false;

   double filled_volume = g_trade.ResultVolume();
   double filled_price = g_trade.ResultPrice();
   if(HistoryDealSelect(deal_ticket))
   {
      double deal_volume = HistoryDealGetDouble(deal_ticket, DEAL_VOLUME);
      double deal_price = HistoryDealGetDouble(deal_ticket, DEAL_PRICE);
      if(deal_volume > 0.0)
         filled_volume = deal_volume;
      if(deal_price > 0.0)
         filled_price = deal_price;
   }
   if(filled_volume <= 0.0)
      filled_volume = lots;
   if(filled_price <= 0.0)
      filled_price = entry_price;

   if(preserve_primary_exits)
      SNR_RestoreManagedPositionExits(preserve_tickets, preserve_stop_losses, preserve_take_profits);
   else if(g_modifyAllPositionsAfterEntry)
      SNR_ModifyAllManagedPositions(stop_loss, take_profit);
   SNR_RegisterOpenTrade(ctx, decision, deal_ticket, order_ticket, stop_loss, take_profit, preserve_primary_exits);
   SNR_LogExecEvent(ctx.decision_time_server,
                    "FILL",
                    decision.direction,
                    filled_volume,
                    request_price,
                    filled_price,
                    stop_loss,
                    take_profit,
                    SNR_DecisionReasonKey(decision),
                    fill_retcode,
                    deal_ticket,
                    order_ticket);

   g_tradesToday++;
   if(!g_narrative.active || decision.mode == SNR_MODE_CLASSIC)
   {
      g_narrative.active = true;
      g_narrative.classic_seeded = true;
      g_narrative.direction = decision.direction;
      g_narrative.layers_opened = 1;
      g_narrative.seeded_at = ctx.decision_time_server;
      g_narrative.wave_id = decision.wave_id;
   }
   else
   {
      g_narrative.layers_opened++;
   }
   g_narrative.last_entry_time = ctx.decision_time_server;
   g_narrative.last_entry_price = filled_price;
   g_narrative.anchor_stop = stop_loss;
   g_narrative.anchor_target = take_profit;

   g_lastStatus = StringFormat("FIRED %s %s", SNR_ModeName(decision.mode), SNR_DirectionName(decision.direction));
   return true;
}

double OnTester()
{
   double profit = TesterStatistics(STAT_PROFIT);
   double trades = TesterStatistics(STAT_TRADES);
   double dd_pct = TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
   double pf     = TesterStatistics(STAT_PROFIT_FACTOR);
   if(trades < 50 || pf <= 0.0)
      return -10000.0;

   return (profit * pf * MathSqrt(trades)) / (1.0 + dd_pct);
}

int OnInit()
{
   // Reset all global indicator handles to prevent stale states during reinitialization
   g_hDragonHigh = INVALID_HANDLE;
   g_hDragonMid  = INVALID_HANDLE;
   g_hDragonLow  = INVALID_HANDLE;
   g_hTrend      = INVALID_HANDLE;
   g_hATR        = INVALID_HANDLE;
   g_hH1Bias     = INVALID_HANDLE;
   g_hH4Bias     = INVALID_HANDLE;

   g_sym.Name(_Symbol);
   
   // Apply configurations and override mappings first to establish true runtime parameters
   SNR_ApplyAutoSleeveConfig(_Symbol);

   // Hard calibration check for XAUUSD risk sizing safety
   if(StringFind(_Symbol, "XAU") >= 0)
   {
      if(!g_useOrderCalcRiskSizing)
      {
         Print("[SNR] CRITICAL SECURITY FAULT: Legacy Tick Value sizing is forbidden on Gold (XAUUSD) due to contract size multiplier discrepancy. You must enable g_useOrderCalcRiskSizing=true.");
         return INIT_PARAMETERS_INCORRECT;
      }
   }
   g_digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   if(_Point <= 0.0)
      return INIT_FAILED;

   if(g_digits <= 2)
      g_pipSize = _Point * 100.0;
   else if(g_digits == 3 || g_digits == 5)
      g_pipSize = _Point * 10.0;
   else
      g_pipSize = _Point;

   g_hDragonHigh = iMA(_Symbol, PERIOD_CURRENT, g_dragonPeriod, 0, MODE_EMA, PRICE_HIGH);
   g_hDragonMid  = iMA(_Symbol, PERIOD_CURRENT, g_dragonPeriod, 0, MODE_EMA, PRICE_CLOSE);
   g_hDragonLow  = iMA(_Symbol, PERIOD_CURRENT, g_dragonPeriod, 0, MODE_EMA, PRICE_LOW);
   g_hTrend      = iMA(_Symbol, PERIOD_CURRENT, g_trendPeriod, 0, MODE_EMA, PRICE_CLOSE);
   g_hATR        = iATR(_Symbol, PERIOD_CURRENT, g_atrPeriod);
   ENUM_TIMEFRAMES htf_fast_tf = PERIOD_H1;
   ENUM_TIMEFRAMES htf_slow_tf = PERIOD_H4;
   SNR_SelectHtfBiasTimeframes(htf_fast_tf, htf_slow_tf);
   if(g_useH1Bias)
      g_hH1Bias = iMA(_Symbol, htf_fast_tf, g_htfBiasPeriod, 0, MODE_EMA, PRICE_CLOSE);
   if(g_useH4Bias)
      g_hH4Bias = iMA(_Symbol, htf_slow_tf, g_htfBiasPeriod, 0, MODE_EMA, PRICE_CLOSE);

   if(g_hDragonHigh == INVALID_HANDLE || g_hDragonMid == INVALID_HANDLE ||
      g_hDragonLow == INVALID_HANDLE || g_hTrend == INVALID_HANDLE || g_hATR == INVALID_HANDLE)
      return INIT_FAILED;

   g_trade.SetExpertMagicNumber(g_magic);
   g_trade.SetDeviationInPoints(g_deviation);
   g_trade.SetTypeFilling(SNR_DetectFillMode());

   SNR_ResetNarrative(g_narrative);
   SNR_ResetClassicArm(g_classicArm);
   SNR_ResetClassicArm(g_xauT1Arm);
   SNR_ResetShadowNarrative(g_shadowLong);
   SNR_ResetShadowNarrative(g_shadowShort);
   SNR_RebuildOpenTradesFromPositions();
   g_lastTradeDay = 0;
   g_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   g_peakEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   g_lastStatus = "INIT";

   SNR_LoadCalendar(g_calendarFile);
   SNR_InitTelemetry(g_magic);
   SNR_WriteRunMetaJson();

   PrintFormat("[SNR] EA_SonicR v2.0 | Symbol=%s | TF=%s | Variant=%s",
               _Symbol, EnumToString(_Period), SNR_CleanTesterString(g_variantTag));
   PrintFormat("[SNR] Calendar loaded=%s | source=%s | events=%d | fallback=%s",
               SNR_BoolLabel(g_snrCalendarMeta.loaded),
               g_snrCalendarMeta.source_file,
               g_snrCalendarMeta.total_events,
               SNR_BoolLabel(g_snrCalendarMeta.used_legacy_fallback));

   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_hDragonHigh != INVALID_HANDLE) { IndicatorRelease(g_hDragonHigh); g_hDragonHigh = INVALID_HANDLE; }
   if(g_hDragonMid  != INVALID_HANDLE) { IndicatorRelease(g_hDragonMid);  g_hDragonMid  = INVALID_HANDLE; }
   if(g_hDragonLow  != INVALID_HANDLE) { IndicatorRelease(g_hDragonLow);  g_hDragonLow  = INVALID_HANDLE; }
   if(g_hTrend      != INVALID_HANDLE) { IndicatorRelease(g_hTrend);      g_hTrend      = INVALID_HANDLE; }
   if(g_hATR        != INVALID_HANDLE) { IndicatorRelease(g_hATR);        g_hATR        = INVALID_HANDLE; }
   if(g_hH1Bias     != INVALID_HANDLE) { IndicatorRelease(g_hH1Bias);     g_hH1Bias     = INVALID_HANDLE; }
   if(g_hH4Bias     != INVALID_HANDLE) { IndicatorRelease(g_hH4Bias);     g_hH4Bias     = INVALID_HANDLE; }

   SNR_WriteRunMetaJson();
   Comment("");
}

void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
{
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD)
      return;
   if(!HistoryDealSelect(trans.deal))
      return;

   long magic = HistoryDealGetInteger(trans.deal, DEAL_MAGIC);
   if((int)magic != g_magic)
      return;
   string symbol = HistoryDealGetString(trans.deal, DEAL_SYMBOL);
   if(symbol != _Symbol)
      return;

   ENUM_DEAL_ENTRY entry_type = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(trans.deal, DEAL_ENTRY);
   if(entry_type != DEAL_ENTRY_OUT && entry_type != DEAL_ENTRY_OUT_BY)
      return;

   ulong position_id = (ulong)HistoryDealGetInteger(trans.deal, DEAL_POSITION_ID);
   SnrOpenTrade trade;
   if(!SNR_GetOpenTrade(position_id, trade))
      return;

   datetime close_server_ts = (datetime)HistoryDealGetInteger(trans.deal, DEAL_TIME);
   datetime close_utc_ts    = SNR_ServerToUTC(close_server_ts);
   double close_price       = HistoryDealGetDouble(trans.deal, DEAL_PRICE);
   double volume            = HistoryDealGetDouble(trans.deal, DEAL_VOLUME);
   double deal_profit       = HistoryDealGetDouble(trans.deal, DEAL_PROFIT);
   double commission        = HistoryDealGetDouble(trans.deal, DEAL_COMMISSION);
   double swap              = HistoryDealGetDouble(trans.deal, DEAL_SWAP);
   double fee               = HistoryDealGetDouble(trans.deal, DEAL_FEE);
   ulong order_ticket       = (ulong)HistoryDealGetInteger(trans.deal, DEAL_ORDER);
   string comment           = HistoryDealGetString(trans.deal, DEAL_COMMENT);
   string lower_comment     = comment;
   StringToLower(lower_comment);

   string exit_reason = comment;
   string close_source = "market_exit";
   if(StringFind(lower_comment, "tp") == 0)
   {
      exit_reason = "tp";
      close_source = "target";
   }
   else if(StringFind(lower_comment, "sl") == 0)
   {
      exit_reason = "sl";
      close_source = "stop";
   }
   else if(lower_comment == "")
   {
      exit_reason = (trade.pending_close_reason != "" ? trade.pending_close_reason : "manual_close");
      close_source = "market_exit";
   }

   bool is_final_close = !SNR_PositionIdStillOpen(position_id);
   // Preserve the frozen strategy behavior: lane-loss routing remains based on
   // DEAL_PROFIT exactly as before telemetry v3 added separate cost fields.
   if(is_final_close && deal_profit < 0.0 && g_useRegimeRouter)
      SNR_NoteLaneLoss(trade.mode);
   SNR_LogExecEvent(close_server_ts,
                    "CLOSE_ACK",
                    trade.direction,
                    volume,
                    trade.entry_price,
                    close_price,
                    trade.stop_loss,
                    trade.take_profit,
                    exit_reason,
                    0,
                    trans.deal,
                    order_ticket);
   SNR_LogTradeClose(trade,
                     trans.deal,
                     order_ticket,
                     close_server_ts,
                     close_utc_ts,
                     close_price,
                     volume,
                     deal_profit,
                     commission,
                     swap,
                     fee,
                     exit_reason,
                     close_source,
                     is_final_close);

   if(is_final_close)
      SNR_RemoveOpenTrade(position_id);
}

bool SNR_CanTryContinuationFallback(const string reject_reason, const SnrDecision &decision)
{
   if(!g_useContinuationPullback)
      return false;
   if(decision.mode == SNR_MODE_CONTINUATION)
      return false;
   if(!g_narrative.active || !g_narrative.classic_seeded)
      return false;

   string reason = SNR_ToUpper(reject_reason);
   return (StringFind(reason, "SL_REJECT") == 0 || reason == "BROKER_STOP_BLOCK");
}

void OnTick()
{
   if(!g_enabled)
      return;

   g_sym.RefreshRates();
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity > g_peakEquity)
      g_peakEquity = equity;

   datetime now_server = TimeCurrent();
   SNR_DailyReset(now_server);
   SNR_SyncNarrative();
   SNR_ManageScalpTimeStop();
   SNR_ManageBreakEven();

   if(SNR_RiskLocked() && SNR_CountManagedPositions() > 0)
      SNR_CloseManagedPositions(g_lastStatus);

   string flat_reason = "";
   if(SNR_CountManagedPositions() > 0 && SNR_ShouldClockForceFlat(now_server, flat_reason))
      SNR_CloseManagedPositions(flat_reason);

   datetime bar_time = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(bar_time == g_lastBar)
   {
      SNR_UpdateComment();
      return;
   }
   g_lastBar = bar_time;

   if(Bars(_Symbol, PERIOD_CURRENT) < SNR_RequiredWarmupBars())
      return;

   SnrContext ctx;
   if(!SNR_BuildContext(bar_time,
                        g_hDragonHigh,
                        g_hDragonMid,
                        g_hDragonLow,
                        g_hTrend,
                        g_hATR,
                        g_hH1Bias,
                        g_hH4Bias,
                        g_pipSize,
                        g_narrative,
                        ctx))
      return;
   SNR_ManageStructuralTrailing(ctx);
   SNR_ResetLaneLosses(ctx.decision_time_server, ctx.session_bucket);
   SNR_LogRegimeState(ctx, "REGIME_CHANGE");

   if(ctx.force_flat_now && SNR_CountManagedPositions() > 0)
   {
      SNR_CloseManagedPositions(ctx.block_reason != "" ? ctx.block_reason : "NEWS_FORCE_FLAT");
      g_lastStatus = (ctx.block_reason != "" ? ctx.block_reason : "NEWS_FORCE_FLAT");
      SNR_UpdateComment();
      return;
   }

   if(SNR_RiskLocked())
   {
      SnrDecision locked;
      locked.should_trade = false;
      locked.mode = SNR_MODE_BLOCKED;
      locked.direction = SNR_DIR_NONE;
      locked.block_reason = g_lastStatus;
      locked.wave_id = "";
      locked.archetype = "";
      locked.setup_state = "INVALIDATE";
      locked.invalidate_reason = g_lastStatus;
      locked.context_score = ctx.context_score;
      locked.pvsra_grade = ctx.pvsra_grade;
      locked.level_zone = ctx.level_zone;
      locked.stop_price = 0.0;
      locked.target_rr = 0.0;
      locked.quality_score = 0.0;
      locked.pullback_depth_atr = 0.0;
      SNR_ResetFxChaseTrapV2ADiagnostic(locked);
      SNR_LogDecisionBundle(ctx, locked, "BLOCKED");
      SNR_UpdateComment();
      return;
   }

   int max_trades_today = (g_useRegimeRouter ? g_maxScalpTradesPerDay : g_maxTradesPerDay);
   if(g_tradesToday >= max_trades_today)
   {
      SnrDecision daily_limit;
      daily_limit.should_trade = false;
      daily_limit.mode = SNR_MODE_BLOCKED;
      daily_limit.direction = SNR_DIR_NONE;
      daily_limit.block_reason = "DAILY_TRADE_LIMIT";
      daily_limit.wave_id = "";
      daily_limit.archetype = "";
      daily_limit.setup_state = "INVALIDATE";
      daily_limit.invalidate_reason = "DAILY_TRADE_LIMIT";
      daily_limit.context_score = ctx.context_score;
      daily_limit.pvsra_grade = ctx.pvsra_grade;
      daily_limit.level_zone = ctx.level_zone;
      daily_limit.stop_price = 0.0;
      daily_limit.target_rr = 0.0;
      daily_limit.quality_score = 0.0;
      daily_limit.pullback_depth_atr = 0.0;
      SNR_ResetFxChaseTrapV2ADiagnostic(daily_limit);
      SNR_LogDecisionBundle(ctx, daily_limit, "BLOCKED");
      g_lastStatus = "DAILY_TRADE_LIMIT";
      SNR_UpdateComment();
      return;
   }

   SnrDecision decision;
   if(!SNR_BuildArmedClassicDecision(ctx, decision))
   {
      SNR_BuildDecision(ctx,
                        g_narrative,
                        g_hDragonHigh,
                        g_hDragonMid,
                        g_hDragonLow,
                        g_hTrend,
                        g_hATR,
                        g_xauT1Arm,
                        decision);
      if(!decision.should_trade && !g_narrative.active)
         SNR_ConsiderClassicArm(ctx);
   }
   SNR_ApplyOpportunityScoreGate(ctx, decision);

   if(!decision.should_trade)
   {
      if(g_classicArm.active && !g_narrative.active)
      {
         g_lastStatus = "ARMED_CLASSIC_WAIT";
         decision.direction = g_classicArm.direction;
         decision.wave_id = g_classicArm.wave_id;
         decision.archetype = g_classicArm.archetype;
         decision.setup_state = "ARM";
         decision.block_reason = "ARMED_CLASSIC_WAIT";
         decision.invalidate_reason = "";
         decision.pvsra_grade = g_classicArm.pvsra_grade;
         decision.level_zone = g_classicArm.level_zone;
         decision.quality_score = g_classicArm.quality_score;
         decision.pullback_depth_atr = g_classicArm.pullback_depth_atr;
      }
      else
         g_lastStatus = (decision.block_reason != "" ? decision.block_reason : "NO_SIGNAL");
      SNR_LogDecisionBundle(ctx, decision, "BLOCKED");
      SNR_UpdateComment();
      return;
   }

   if(SNR_ExecuteDecision(ctx, decision))
   {
      if(decision.mode == SNR_MODE_CLASSIC)
         SNR_ResetClassicArm(g_classicArm);
      if(decision.mode == SNR_MODE_XAU_ACTIVE_CLASSIC)
         SNR_ResetClassicArm(g_xauT1Arm);
      SNR_LogDecisionBundle(ctx, decision, "FIRED");
   }
   else
   {
      string original_reject = g_lastStatus;
      decision.should_trade = false;
      decision.block_reason = original_reject;
      SNR_LogDecisionBundle(ctx, decision, "ORDER_REJECT");

      if(SNR_CanTryContinuationFallback(original_reject, decision))
      {
         SnrDecision fallback;
         if(SNR_BuildContinuationFallbackDecision(ctx,
                                                  g_narrative,
                                                  g_hDragonHigh,
                                                  g_hDragonMid,
                                                  g_hDragonLow,
                                                  g_hTrend,
                                                  g_hATR,
                                                  fallback))
         {
            SNR_ApplyOpportunityScoreGate(ctx, fallback);
            if(fallback.should_trade && SNR_ExecuteDecision(ctx, fallback))
            {
               SNR_LogDecisionBundle(ctx, fallback, "FIRED");
            }
            else
            {
               string fallback_reject = (fallback.block_reason != "" ? fallback.block_reason : g_lastStatus);
               fallback.should_trade = false;
               fallback.block_reason = fallback_reject;
               SNR_LogDecisionBundle(ctx, fallback, (fallback.block_reason == "OPPORTUNITY_SCORE_LOW" ? "BLOCKED" : "ORDER_REJECT"));
            }
         }
      }
   }

   SNR_UpdateComment();
}
