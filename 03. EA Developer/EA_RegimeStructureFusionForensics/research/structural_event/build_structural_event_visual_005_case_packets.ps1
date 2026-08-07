param()

$ErrorActionPreference = 'Stop'
$cases = @(
    [ordered]@{ Suffix='C01'; Index=1; From='2019.04.27'; To='2019.05.09'; Magic=5867361; Label='BREAKOUT_LONG_LOSS' },
    [ordered]@{ Suffix='C02'; Index=2; From='2018.10.06'; To='2018.10.18'; Magic=5867362; Label='BREAKOUT_LONG_WIN' },
    [ordered]@{ Suffix='C03'; Index=3; From='2017.12.25'; To='2018.01.06'; Magic=5867363; Label='BREAKOUT_SHORT_LOSS' },
    [ordered]@{ Suffix='C04'; Index=4; From='2018.05.26'; To='2018.06.07'; Magic=5867364; Label='BREAKOUT_SHORT_WIN' },
    [ordered]@{ Suffix='C05'; Index=5; From='2018.07.16'; To='2018.07.28'; Magic=5867365; Label='TREND_LONG_LOSS' },
    [ordered]@{ Suffix='C06'; Index=6; From='2018.02.24'; To='2018.03.08'; Magic=5867366; Label='TREND_LONG_WIN' },
    [ordered]@{ Suffix='C07'; Index=7; From='2019.09.14'; To='2019.09.26'; Magic=5867367; Label='TREND_SHORT_LOSS' },
    [ordered]@{ Suffix='C08'; Index=8; From='2019.03.18'; To='2019.03.30'; Magic=5867368; Label='TREND_SHORT_WIN' }
)

$deps = @(
    [ordered]@{ name='AI_Regime_Detection'; source='06.Indicator Alpha/AI_Regime_Detection.mq5'; source_sha256='C432AEF3BF7EC93EC8A64BD2806C115E71F822B2DCB438DAC22590FB978EB475'; terminal_ex5='AlphaFactory\AI_Regime_Detection.ex5' },
    [ordered]@{ name='Modern_Bollinger_Bands_GBB'; source='06.Indicator Alpha/Modern_Bollinger_Bands_GBB.mq5'; source_sha256='AC5DB6E1DDA825F6A3535E9AB1E4C9956086C7AF590E2672C71CF03D8F4E54FE'; terminal_ex5='AlphaFactory\Modern_Bollinger_Bands_GBB.ex5' },
    [ordered]@{ name='QQE_MOD'; source='06.Indicator Alpha/QQE_MOD.mq5'; source_sha256='86876D352762F6C107BC4AC886C04E901C9345C68A5C7E68C73A33696F13053F'; terminal_ex5='AlphaFactory\QQE_MOD.ex5' },
    [ordered]@{ name='TB_Smart_Money_Concept_2026'; source='06.Indicator Alpha/TB_Smart_Money_Concept_2026.mq5'; source_sha256='489B6E6B74C4FCA6624B510DC9FF38FDBBDA0584C007B8FFEE3D8339D1CB879E'; terminal_ex5='AlphaFactory\TB_Smart_Money_Concept_2026.ex5' },
    [ordered]@{ name='Volatility_Regime_Classifier_QuantRegime'; source='06.Indicator Alpha/Volatility_Regime_Classifier_QuantRegime.mq5'; source_sha256='EB81B1426CBDAF3143F553388A213E2BB5A3E33E05433991918CC5977273A087'; terminal_ex5='AlphaFactory\Volatility_Regime_Classifier_QuantRegime.ex5' }
)

$utf8 = [System.Text.UTF8Encoding]::new($false)
foreach ($case in $cases) {
    $id = "HYP-RSF-EURUSD-M5-STRUCTURAL-EVENT-VISUAL-005-$($case.Suffix)"
    $overrides = @(
        'InpAllowBreakoutMode=true', 'InpAllowRangeMode=false', 'InpAllowTrendMode=true',
        'InpEnableTelemetry=true', 'InpExpectedSymbol=EURUSD',
        'InpForensicAttachM5Indicators=true', 'InpForensicCaptureWindows=FROZEN_13_V1',
        'InpForensicCleanChart=false', 'InpForensicExternalCapturePauseMs=30000',
        "InpForensicNativeCaseIndex=$($case.Index)",
        'InpForensicNativeLossSchedule=FROZEN_STRUCTURAL_EVENT_004_OUTCOMES_V1',
        'InpForensicShotHeight=900', 'InpForensicShotSettleMs=1000',
        'InpForensicShotVerifyTicks=200', 'InpForensicShotWidth=1600',
        'InpForensicVisualScreenshots=true', "InpHypothesisId=$id", "InpMagic=$($case.Magic)",
        'InpManualModeMask=6', 'InpManualSessionMask=6', 'InpProfileMode=1',
        'InpQqeBollingerLength=50', 'InpQqeBollingerMultiplier=0.35',
        'InpQqePrimaryFactor=3.0', 'InpQqePrimaryRsiLength=6', 'InpQqePrimarySmoothing=5',
        'InpQqePrimarySource=1', 'InpQqePrimaryThreshold=3.0', 'InpQqeSecondaryFactor=1.61',
        'InpQqeSecondaryRsiLength=6', 'InpQqeSecondarySmoothing=5',
        'InpQqeSecondarySource=1', 'InpQqeSecondaryThreshold=3.0',
        'InpResearchAutoMode=true', 'InpStructuralExpiryBars=8',
        'InpStructuralInvalidationAtr=0.20', 'InpStructuralMaxExtensionAtr=0.35',
        'InpStructuralMinObjectiveR=1.25', 'InpStructuralQqeVetoThreshold=3.0',
        'InpStructuralRetestToleranceAtr=0.15', 'InpUseContextRouter=true',
        'InpUseQqeTiming=true', 'InpUseRoleAwareSequence=false',
        'InpUseStructuralEventSequence=true', 'InpUseTbStructure=true',
        'InpUseTemporalSequence=false',
        "InpVariantTag=STRUCTURAL_EVENT_VISUAL_005_$($case.Suffix)_$($case.Label)"
    ) -join ';'
    $packet = [ordered]@{
        schema_version='alphafactory_research_task_packet.v1'; hypothesis_id=$id; run_role='control'
        ea_name='EA_RegimeStructureFusionForensics'; symbol='EURUSD'; period='M5'
        from=$case.From; to=$case.To; model=1; execution_mode=0; fixed_delay_ms=0
        overrides=$overrides; telemetry_tier='trade-only'; telemetry_profile='lifecycle-v3'
        deposit=100000; leverage=100; spread='current'; visual_mode=$true
        required_sidecars=@('*_LifecycleTrades_*.csv','*_RSFForensic_*.csv','*_RunMeta_*.json','*_VisualShots_*.csv')
        indicator_dependencies=$deps
        purpose="Exact native MT5 post-exit chart for frozen STRUCTURAL-EVENT-004 paired case $($case.Suffix) $($case.Label). Diagnostic Model1 only."
        economic_claims_authorized=$false; promotion_eligible=$false
    }
    $path = Join-Path $PSScriptRoot ("{0}_TASK_PACKET.json" -f $id)
    [System.IO.File]::WriteAllText($path, ($packet | ConvertTo-Json -Depth 12) + "`n", $utf8)
    Write-Output "STRUCTURAL_EVENT_VISUAL_CASE_PACKET_OK id=$id path=$path"
}
