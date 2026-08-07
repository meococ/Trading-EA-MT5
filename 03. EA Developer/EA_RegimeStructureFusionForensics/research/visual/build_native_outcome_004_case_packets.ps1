param(
    [ValidateSet('004','005','006')]
    [string]$OutcomeId = '006'
)

$ErrorActionPreference = 'Stop'

$cases = @(
    [ordered]@{ Suffix='C01'; Index=1; From='2019.05.20'; To='2019.06.06'; Magic=5867321; Label='BREAKOUT_LONG' },
    [ordered]@{ Suffix='C02'; Index=2; From='2019.09.25'; To='2019.10.11'; Magic=5867322; Label='TREND_LONG' },
    [ordered]@{ Suffix='C03'; Index=3; From='2019.11.15'; To='2019.12.02'; Magic=5867323; Label='RANGE_LONG' },
    [ordered]@{ Suffix='C04'; Index=4; From='2020.04.06'; To='2020.04.22'; Magic=5867324; Label='TREND_SHORT' },
    [ordered]@{ Suffix='C05'; Index=5; From='2020.10.01'; To='2020.10.19'; Magic=5867325; Label='BREAKOUT_SHORT' },
    [ordered]@{ Suffix='C06'; Index=6; From='2020.12.01'; To='2020.12.18'; Magic=5867326; Label='RANGE_SHORT' },
    [ordered]@{ Suffix='C07'; Index=7; From='2022.05.30'; To='2022.06.15'; Magic=5867327; Label='EXTREME_LOSS' }
)

$deps = @(
    [ordered]@{ name='AI_Regime_Detection'; source='06.Indicator Alpha/AI_Regime_Detection.mq5'; source_sha256='C432AEF3BF7EC93EC8A64BD2806C115E71F822B2DCB438DAC22590FB978EB475'; terminal_ex5='AlphaFactory\AI_Regime_Detection.ex5' },
    [ordered]@{ name='Modern_Bollinger_Bands_GBB'; source='06.Indicator Alpha/Modern_Bollinger_Bands_GBB.mq5'; source_sha256='AC5DB6E1DDA825F6A3535E9AB1E4C9956086C7AF590E2672C71CF03D8F4E54FE'; terminal_ex5='AlphaFactory\Modern_Bollinger_Bands_GBB.ex5' },
    [ordered]@{ name='QQE_MOD'; source='06.Indicator Alpha/QQE_MOD.mq5'; source_sha256='86876D352762F6C107BC4AC886C04E901C9345C68A5C7E68C73A33696F13053F'; terminal_ex5='AlphaFactory\QQE_MOD.ex5' },
    [ordered]@{ name='TB_Smart_Money_Concept_2026'; source='06.Indicator Alpha/TB_Smart_Money_Concept_2026.mq5'; source_sha256='489B6E6B74C4FCA6624B510DC9FF38FDBBDA0584C007B8FFEE3D8339D1CB879E'; terminal_ex5='AlphaFactory\TB_Smart_Money_Concept_2026.ex5' },
    [ordered]@{ name='Volatility_Regime_Classifier_QuantRegime'; source='06.Indicator Alpha/Volatility_Regime_Classifier_QuantRegime.mq5'; source_sha256='EB81B1426CBDAF3143F553388A213E2BB5A3E33E05433991918CC5977273A087'; terminal_ex5='AlphaFactory\Volatility_Regime_Classifier_QuantRegime.ex5' }
)

$utf8 = New-Object System.Text.UTF8Encoding($false)
foreach ($case in $cases) {
    $id = "HYP-RSF-EURUSD-M5-NATIVE-OUTCOME-$OutcomeId-$($case.Suffix)"
    $externalPauseMs = if ($OutcomeId -eq '006') { 30000 } else { 0 }
    $overrides = @(
        'InpEnableTelemetry=true', 'InpExpectedSymbol=EURUSD',
        'InpForensicAttachM5Indicators=true', 'InpForensicCaptureWindows=FROZEN_13_V1',
        'InpForensicCleanChart=true', "InpForensicExternalCapturePauseMs=$externalPauseMs",
        "InpForensicNativeCaseIndex=$($case.Index)",
        'InpForensicNativeLossSchedule=FROZEN_7_LOSER_OUTCOMES_V1',
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
        'InpUseTbStructure=true', "InpVariantTag=NATIVE_OUTCOME_${OutcomeId}_$($case.Suffix)_$($case.Label)"
    ) -join ';'
    $packet = [ordered]@{
        schema_version='alphafactory_research_task_packet.v1'; hypothesis_id=$id; run_role='control'
        ea_name='EA_RegimeStructureFusionForensics'; symbol='EURUSD'; period='M5'
        from=$case.From; to=$case.To; model=1; execution_mode=0; fixed_delay_ms=0
        overrides=$overrides; telemetry_tier='trade-only'; telemetry_profile='lifecycle-v3'
        deposit=100000; leverage=100; spread='current'; visual_mode=$true
        required_sidecars=@('*_LifecycleTrades_*.csv','*_RSFForensic_*.csv','*_RunMeta_*.json','*_VisualShots_*.csv')
        indicator_dependencies=$deps
        purpose="Exact native MT5 post-exit chart for frozen case $($case.Label). Diagnostic Model 1 only."
        economic_claims_authorized=$false; promotion_eligible=$false
    }
    $path = Join-Path $PSScriptRoot ("{0}_TASK_PACKET.json" -f $id)
    [IO.File]::WriteAllText($path, ($packet | ConvertTo-Json -Depth 12), $utf8)
    Write-Host "NATIVE_OUTCOME_CASE_PACKET_OK id=$id path=$path"
}
