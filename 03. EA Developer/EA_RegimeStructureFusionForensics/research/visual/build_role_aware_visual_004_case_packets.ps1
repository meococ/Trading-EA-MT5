param()

$ErrorActionPreference = 'Stop'
$cases = @(
    [ordered]@{ Suffix='C01'; Index=1; From='2018.04.10'; To='2018.04.25'; Magic=5867341; Label='BREAKOUT_LONG_LOSS' },
    [ordered]@{ Suffix='C02'; Index=2; From='2020.12.10'; To='2020.12.20'; Magic=5867342; Label='BREAKOUT_LONG_WIN' },
    [ordered]@{ Suffix='C03'; Index=3; From='2020.05.25'; To='2020.06.06'; Magic=5867343; Label='BREAKOUT_SHORT_LOSS' },
    [ordered]@{ Suffix='C04'; Index=4; From='2020.05.04'; To='2020.05.13'; Magic=5867344; Label='BREAKOUT_SHORT_WIN' },
    [ordered]@{ Suffix='C05'; Index=5; From='2019.01.02'; To='2019.01.14'; Magic=5867345; Label='TREND_LONG_LOSS' },
    [ordered]@{ Suffix='C06'; Index=6; From='2018.05.20'; To='2018.06.01'; Magic=5867346; Label='TREND_LONG_WIN' },
    [ordered]@{ Suffix='C07'; Index=7; From='2019.07.15'; To='2019.07.27'; Magic=5867347; Label='TREND_SHORT_LOSS' },
    [ordered]@{ Suffix='C08'; Index=8; From='2018.01.25'; To='2018.02.08'; Magic=5867348; Label='TREND_SHORT_WIN' }
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
    $id = "HYP-RSF-EURUSD-M5-ROLE-AWARE-VISUAL-004-$($case.Suffix)"
    $overrides = @(
        'InpEnableTelemetry=true', 'InpExpectedSymbol=EURUSD',
        'InpForensicAttachM5Indicators=true', 'InpForensicCaptureWindows=FROZEN_13_V1',
        'InpForensicCleanChart=true', 'InpForensicExternalCapturePauseMs=30000',
        "InpForensicNativeCaseIndex=$($case.Index)",
        'InpForensicNativeLossSchedule=FROZEN_ROLE_AWARE_003_OUTCOMES_V1',
        'InpForensicShotHeight=900', 'InpForensicShotSettleMs=1000',
        'InpForensicShotVerifyTicks=200', 'InpForensicShotWidth=1600',
        'InpForensicVisualScreenshots=true', "InpHypothesisId=$id", "InpMagic=$($case.Magic)",
        'InpManualModeMask=7', 'InpManualSessionMask=6', 'InpProfileMode=1',
        'InpQqeBollingerLength=50', 'InpQqeBollingerMultiplier=0.35',
        'InpQqePrimaryFactor=3.0', 'InpQqePrimaryRsiLength=6', 'InpQqePrimarySmoothing=5',
        'InpQqePrimarySource=1', 'InpQqePrimaryThreshold=3.0', 'InpQqeSecondaryFactor=1.61',
        'InpQqeSecondaryRsiLength=6', 'InpQqeSecondarySmoothing=5',
        'InpQqeSecondarySource=1', 'InpQqeSecondaryThreshold=3.0',
        'InpResearchAutoMode=true', 'InpUseContextRouter=true', 'InpUseQqeTiming=true',
        'InpUseTbStructure=true', "InpVariantTag=ROLE_AWARE_VISUAL_004_$($case.Suffix)_$($case.Label)"
    ) -join ';'
    $packet = [ordered]@{
        schema_version='alphafactory_research_task_packet.v1'; hypothesis_id=$id; run_role='control'
        ea_name='EA_RegimeStructureFusionForensics'; symbol='EURUSD'; period='M5'
        from=$case.From; to=$case.To; model=1; execution_mode=0; fixed_delay_ms=0
        overrides=$overrides; telemetry_tier='trade-only'; telemetry_profile='lifecycle-v3'
        deposit=100000; leverage=100; spread='current'; visual_mode=$true
        required_sidecars=@('*_LifecycleTrades_*.csv','*_RSFForensic_*.csv','*_RunMeta_*.json','*_VisualShots_*.csv')
        indicator_dependencies=$deps
        purpose="Exact native MT5 post-exit chart for frozen paired case $($case.Suffix) $($case.Label). Diagnostic Model1 only."
        economic_claims_authorized=$false; promotion_eligible=$false
    }
    $path = Join-Path $PSScriptRoot ("{0}_TASK_PACKET.json" -f $id)
    [System.IO.File]::WriteAllText($path, ($packet | ConvertTo-Json -Depth 12) + "`n", $utf8)
    Write-Output "ROLE_AWARE_VISUAL_CASE_PACKET_OK id=$id path=$path"
}
