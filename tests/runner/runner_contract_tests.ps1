param(
    [switch]$StaticOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$alphaPath = Join-Path $repoRoot "02. AlphaFactory\alpha.ps1"
$loopPath = Join-Path $repoRoot "02. AlphaFactory\tools\sonic_research_loop.ps1"
$eaContractPath = Join-Path $repoRoot "02. AlphaFactory\tools\ea_contract.ps1"
$registryPath = Join-Path $repoRoot "03. EA Developer\EA_SonicR\research\CANDIDATE_REGISTRY.jsonl"
$failures = New-Object System.Collections.Generic.List[string]
$passes = 0

function Assert-Contract([bool]$Condition, [string]$Message) {
    if ($Condition) {
        $script:passes++
        Write-Host "[PASS] $Message" -ForegroundColor Green
        return
    }

    $script:failures.Add($Message)
    Write-Host "[FAIL] $Message" -ForegroundColor Red
}

function Invoke-ScriptProcess([string]$ScriptPath, [string[]]$Arguments) {
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $ScriptPath @Arguments 2>&1
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
    }

    return [pscustomobject]@{
        ExitCode = $exitCode
        Output = (($output | ForEach-Object { $_.ToString() }) -join [Environment]::NewLine)
    }
}

function Get-FunctionDefinitionText([string]$ScriptPath, [string[]]$Names) {
    $tokens = $null
    $errors = $null
    $ast = [System.Management.Automation.Language.Parser]::ParseFile($ScriptPath, [ref]$tokens, [ref]$errors)
    if ($errors.Count -gt 0) { throw "Cannot extract functions from invalid script: $ScriptPath" }
    $definitions = @($ast.FindAll({
        param($node)
        ($node -is [System.Management.Automation.Language.FunctionDefinitionAst]) -and
            ($node.Name -in $Names)
    }, $true))
    foreach ($name in $Names) {
        $match = @($definitions | Where-Object { $_.Name -ceq $name })
        if ($match.Count -ne 1) { throw "Expected exactly one function '$name' in $ScriptPath; found $($match.Count)." }
        $match[0].Extent.Text
    }
}

foreach ($path in @($alphaPath, $loopPath, $eaContractPath)) {
    $tokens = $null
    $errors = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile($path, [ref]$tokens, [ref]$errors)
    Assert-Contract ($errors.Count -eq 0) "PowerShell parser accepts $path"
}

$alpha = Get-Content -LiteralPath $alphaPath -Raw
$loop = Get-Content -LiteralPath $loopPath -Raw
$eaContract = Get-Content -LiteralPath $eaContractPath -Raw
$backtestBody = [regex]::Match(
    $alpha,
    '(?s)function\s+Do-Backtest\b.*?(?=\r?\nfunction\s+Do-Analyze\b)'
).Value

Assert-Contract (-not [string]::IsNullOrWhiteSpace($backtestBody)) "contract test isolates the Do-Backtest body"

Assert-Contract ($alpha -match '\[string\]\$HypothesisId') "alpha backtest accepts hypothesis_id"
Assert-Contract ($alpha -match '\[string\]\$Symbol\s*=\s*"XAUUSD"') "alpha default symbol uses canonical unsuffixed XAUUSD"
Assert-Contract ($alpha -match '\[string\]\$TelemetryTier') "alpha backtest accepts telemetry tier"
Assert-Contract ($alpha -match '\[int\]\$Leverage') "alpha backtest accepts leverage"
Assert-Contract ($alpha -match '\[string\]\$RunRole') "alpha backtest binds control versus challenger role"
Assert-Contract ($alpha -match 'function\s+Enter-GlobalBacktestLock') "alpha defines a global backtest lock"
Assert-Contract ($alpha -match '\[System\.IO\.FileMode\]::CreateNew') "global backtest lock uses atomic CreateNew"
Assert-Contract ($alpha -match 'function\s+Register-RunnerOwnedTerminal') "alpha tracks runner-owned terminal PIDs"
Assert-Contract ($alpha -match 'function\s+Test-RunnerOwnedTerminalIdentity') "terminal ownership validates full process identity"
Assert-Contract ($alpha -match 'StartTimeUtc') "terminal ownership binds process start time"
Assert-Contract ($alpha -match 'ExecutablePath') "terminal ownership binds executable path"
Assert-Contract ($alpha -match 'Refusing to stop.*identity') "terminal stop refuses PID reuse or identity mismatch"
Assert-Contract ($alpha -match 'Stop-Process\s+-Id\s+\$ProcessId\s+-Force\s+-ErrorAction\s+Stop') "runner-owned terminal stop fails closed when termination fails"
Assert-Contract ($alpha -match 'WaitForExit') "runner verifies its owned terminal actually exited before dropping identity"
Assert-Contract ($alpha -notmatch '\$existingMT5\s*\|\s*Stop-Process') "alpha never kills pre-existing terminal64 processes"
Assert-Contract ($alpha -match 'Unrelated terminal64 process') "alpha fails closed when an unrelated terminal is running"
Assert-Contract ($alpha -match 'throw\s+"Compile failed') "compile failure throws"
Assert-Contract ($alpha -match 'ExitCode\s+-notin\s+@\(0,\s*1\)') "MetaEditor accepts only documented/observed CLI exit 0 or 1 after artifact proof"
Assert-Contract (
    $alpha.IndexOf('compiler log does not prove zero errors') -lt $alpha.IndexOf('ExitCode -notin @(0, 1)') -and
    $alpha.IndexOf('EX5 is empty or stale') -lt $alpha.IndexOf('ExitCode -notin @(0, 1)')
) "MetaEditor exit 1 is accepted only after fresh log and EX5 proof"
Assert-Contract ($alpha -match 'throw\s+"Backtest failed') "backtest failure throws"
Assert-Contract ($alpha -match 'ALPHA_RUN_DIR=') "alpha emits an exact run-directory marker only on success"
Assert-Contract ($alpha -match 'function\s+New-RunSnapshot') "alpha snapshots source, includes, EX5, and config"
Assert-Contract ($alpha -match 'function\s+Assert-NonArchiveInclude') "alpha defines an archive-include rejection gate"
Assert-Contract ($alpha -match 'Archived include dependency is forbidden') "archive include dependencies fail closed"
Assert-Contract ($alpha -notmatch 'phoenix_legacy_20260312') "strict compiler has no phoenix archive include fallback"
Assert-Contract ($alpha -notmatch '/inc:') "strict compiler never adds an archive include search path"
Assert-Contract ($alpha -match 'contract_symbol_geometry') "run manifest preserves task-packet-bound symbol geometry"
Assert-Contract ($alpha -match "symbol_geometry_source = 'task_packet_bound_execution_receipt'") "fingerprint basis declares symbol-geometry provenance"
Assert-Contract ($alpha -match 'function\s+Resolve-TelemetryTierOverrides') "alpha resolves deterministic telemetry-tier overrides"
Assert-Contract ($alpha -match 'ea_contract\.ps1') "alpha loads the shared EA source contract resolver"
Assert-Contract ($alpha -match 'Resolve-EaSourceContract') "alpha resolves an exact EA main source contract"
Assert-Contract ($loop -match 'ea_contract\.ps1') "research loop loads the shared EA source contract resolver"
Assert-Contract ($loop -match 'Resolve-EaSourceContract') "research loop resolves the same exact EA main source contract"
Assert-Contract ($loop -notmatch '"03\. EA Developer/\$RequestedEaName/\$RequestedEaName\.mq5"') "research loop does not hard-code an EAName.mq5 source path"
Assert-Contract ($eaContract -match "EA_SilverBullet.*EA_SilverBullet_v2\.mq5") "shared source contract pins the SilverBullet v2 main file"
Assert-Contract ($eaContract -match "EA_OpenHalfMom.*EA_OpenHalfMomentum\.mq5") "shared source contract preserves the OpenHalfMom naming exception"
Assert-Contract ($alpha -match 'function\s+Assert-BacktestScalarContract') "alpha rejects unsafe INI-bound scalar values"
foreach ($telemetryInput in @(
    'InpEnableTelemetry',
    'InpEnableOpportunityLogger',
    'InpEnableShadowNarrative',
    'InpEnableStateTelemetry',
    'InpEnableGoldRegimeTelemetry',
    'InpEnableSourceClassicDragonEdgeDistanceTelemetry',
    'InpEnableSourceH4TargetRunwayTelemetry',
    'InpEnableFxM15MtfPvaWeakeningTelemetry',
    'InpEnableFxClassicNearMissTelemetry'
)) {
    Assert-Contract ($alpha -match [regex]::Escape($telemetryInput)) "telemetry mapping binds $telemetryInput"
}
Assert-Contract ($alpha -match 'EA input.*required for telemetry tier') "telemetry mapping fails when a required EA input is absent"
Assert-Contract ($alpha -match 'off.*trade-only.*state-lite.*state-full.*snapshot-casebook') "all telemetry tiers are mapped explicitly"
Assert-Contract ($alpha -match 'function\s+Assert-ContractReceipt') "alpha revalidates contract receipt under the global lock"
Assert-Contract ($alpha -match 'function\s+Complete-RunManifest') "alpha finalizes run identity and sidecar evidence before success"
Assert-Contract ($backtestBody -match '\$stagedEx5Path') "alpha stages a run-unique EX5 for tester execution"
Assert-Contract ($backtestBody -match 'Get-RelativePathUnderRoot\s+\$stagedEx5Path\s+\$expertsRoot') "tester Expert path is derived from the staged EX5"
Assert-Contract ($backtestBody -match 'Staged EX5 changed') "staged EX5 is rehashed around MT5 execution"
Assert-Contract (
    $backtestBody.IndexOf('Assert-ContractReceipt') -ge 0 -and
    $backtestBody.IndexOf('Assert-ContractReceipt') -lt $backtestBody.IndexOf('Do-Compile $EAName')
) "alpha revalidates packet-bound evidence immediately before compile"
Assert-Contract (
    $backtestBody.IndexOf('Assert-ReceiptSourceMatchesMain') -ge 0 -and
    $backtestBody.IndexOf('Assert-ReceiptSourceMatchesMain') -lt $backtestBody.IndexOf('Do-Compile $EAName')
) "alpha binds receipt source evidence to the resolved EA main before compile"
Assert-Contract ($backtestBody -match '\$ex5\s*=\s*\[IO\.Path\]::ChangeExtension\(\$main,\s*"\.ex5"\)\s*\r?\n\s*Do-Compile\s+\$EAName\s*\|\s*Out-Null') "every backtest compiles unconditionally before using EX5"
Assert-Contract (($backtestBody.IndexOf('Do-Compile $EAName')) -ge 0 -and ($backtestBody.IndexOf('Do-Compile $EAName')) -lt ($backtestBody.IndexOf('$snapshot = New-RunSnapshot'))) "compile occurs before the run snapshot"
Assert-Contract ($backtestBody -notmatch '\$testerCacheDir') "backtest does not purge the global Tester cache"
Assert-Contract ($backtestBody -notmatch '\$testerProfileDir') "backtest does not purge global Tester .set files"
Assert-Contract ($backtestBody -notmatch '\$purgePatterns') "backtest does not select Common Files sidecars for deletion"
Assert-Contract ($backtestBody -notmatch '\bRemove-Item\b') "backtest never deletes shared cache, profile, or sidecar evidence"
Assert-Contract ($backtestBody -match 'LastWriteTimeUtc\s*-ge\s*\$runStartUtc') "sidecar collection uses the recorded UTC run boundary"
Assert-Contract (
    $backtestBody.IndexOf('Complete-RunManifest') -ge 0 -and
    $backtestBody.IndexOf('Complete-RunManifest') -lt $backtestBody.IndexOf('ALPHA_RUN_DIR=')
) "alpha verifies the completed manifest before emitting success"

foreach ($field in @(
    'hypothesis_id',
    'run_role',
    'deposit',
    'leverage',
    'spread',
    'telemetry_tier',
    'source_sha256',
    'ex5_sha256',
    'config_sha256',
    'report_sha256',
    'includes_sha256',
    'tester_ex5_path',
    'tester_ex5_sha256',
    'git_commit',
    'git_status',
    'git_status_sha256',
    'broker_fingerprint',
    'server_fingerprint',
    'account_fingerprint',
    'data_fingerprint',
    'required_sidecars',
    'sidecars',
    'artifact_collection_not_before_utc',
    'generated_at_utc'
)) {
    Assert-Contract ($alpha -match ("(?m)^\s*" + [regex]::Escape($field) + "\s*=")) "run manifest includes $field"
}

Assert-Contract ($loop -match '\[string\]\$HypothesisId') "research loop accepts hypothesis_id"
Assert-Contract ($loop -match 'function\s+Resolve-ResearchContract') "research loop validates registry and prereg evidence"
Assert-Contract ($loop -match 'CANDIDATE_REGISTRY\.jsonl') "research loop reads the canonical registry"
Assert-Contract ($loop -match 'validate_candidate_registry\.py') "research loop invokes the canonical semantic registry validator"
Assert-Contract ($loop -match 'function\s+Assert-CandidateRegistryValid') "research loop has a fail-closed registry validation gate"
Assert-Contract ($loop -match '(?s)Assert-CandidateRegistryValid.*?\$LASTEXITCODE.*?throw') "registry validator nonzero is propagated before registry use"
Assert-Contract ($loop -match 'prereg_path') "research loop resolves the registered prereg"
Assert-Contract ($loop -match 'function\s+Invoke-RequiredStep') "research loop aborts on failed required steps"
Assert-Contract ($loop -match 'function\s+Add-StateTransition') "research loop records state transitions"
Assert-Contract ($loop -notmatch 'Find-LatestRunDir') "research loop has no latest-run resolver"
Assert-Contract ($loop -notmatch 'falling back to latest') "research loop has no latest-run fallback"
Assert-Contract ($loop -match 'ALPHA_RUN_DIR=') "research loop consumes only the exact run marker"
Assert-Contract ($loop -match 'DRY RUN') "research loop remains dry-run by default"
Assert-Contract ($loop -match '\[string\]\$TaskPacket') "research loop accepts an optional task packet"
Assert-Contract ($loop -match '\[string\]\$ValidationStage') "research loop exposes validation stage for packet matching"
Assert-Contract ($loop -match '\[string\]\$HoldingContract') "research loop exposes holding contract for packet matching"
Assert-Contract ($loop -match '\[string\]\$CostSourceManifest') "research loop exposes cost-source manifest for packet matching"
Assert-Contract ($loop -match '\[string\]\$MatchedControlRunId') "research loop exposes matched control for packet matching"
Assert-Contract ($loop -match '\[int\]\$ExecutionMode') "research loop binds execution mode"
Assert-Contract ($loop -match '\[int\]\$FixedDelayMs') "research loop binds fixed execution delay"
Assert-Contract ($loop -match '\[ValidateSet\("control",\s*"challenger"\)\]') "research loop exposes bounded control bootstrap role"
Assert-Contract ($loop -match 'LatestRow\s*=') "research contract returns the latest registry row"
Assert-Contract ($loop -match '(?i)killed.*parked|parked.*killed') "research contract blocks latest terminal registry states"
Assert-Contract ($loop -match 'function\s+Resolve-TaskPacket') "research loop validates immutable task packets"
Assert-Contract ($loop -match 'source_sha256') "research loop binds current source SHA256"
Assert-Contract ($loop -match 'include_closure_sha256') "task packet binds the pre-compile include closure"
Assert-Contract ($loop -match 'prereg_sha256') "task packet binds prereg SHA256"
Assert-Contract ($loop -match 'cost_source_manifest_sha256') "task packet binds verified cost-source provenance"
Assert-Contract ($loop -match 'historical_spread_provenance') "cost source manifest requires historical-spread provenance"
Assert-Contract ($loop -match 'commission_provenance') "cost source manifest requires commission provenance"
Assert-Contract ($loop -match 'slippage_provenance') "cost source manifest requires slippage provenance"
Assert-Contract ($loop -match 'provenance_status.*VERIFIED') "cost source manifest requires overall VERIFIED provenance"
Assert-Contract ($loop -match 'verification_status') "each cost provenance node requires VERIFIED status"
Assert-Contract ($loop -match 'direction_aware_methodology') "cost source manifest requires direction-aware methodology"
Assert-Contract ($loop -match 'function\s+Resolve-CostEvidenceFile') "cost source preflight recomputes referenced evidence hashes"
Assert-Contract ($loop -match 'coverage_ratio.*0\.99|0\.99.*coverage_ratio') "cost source spread coverage requires at least 99 percent"
Assert-Contract ($loop -match 'same-symbol.*30|30.*same-symbol') "cost source commission requires 30 same-symbol lifecycles"
Assert-Contract ($loop -match 'independent-reference.*100|100.*independent-reference') "cost source slippage requires 100 independent-reference samples"
Assert-Contract ($loop -match 'buy_count.*30|30.*buy_count') "cost source slippage requires at least 30 buy references"
Assert-Contract ($loop -match 'sell_count.*30|30.*sell_count') "cost source slippage requires at least 30 sell references"
Assert-Contract ($loop -match '(?s)p90_buy.*p90_sell.*p90_roundturn') "cost source slippage binds side-specific and round-turn P90"
Assert-Contract ($loop -match 'buy_reference_side.*ask') "cost source slippage binds buy references to ask"
Assert-Contract ($loop -match 'sell_reference_side.*bid') "cost source slippage binds sell references to bid"
Assert-Contract ($loop -match 'slippage_unit.*pips') "cost source slippage uses an explicit pip unit"
foreach ($geometryField in @('digits', 'point', 'pip_size')) {
    Assert-Contract ($loop -match ("symbol_geometry(?s).*" + [regex]::Escape($geometryField))) "cost source binds symbol geometry $geometryField"
    Assert-Contract ($loop -match ("fingerprint_basis(?s).*" + [regex]::Escape($geometryField))) "post-run manifest binds report geometry $geometryField"
}
foreach ($contractField in @(
    'broker_fingerprint', 'server_fingerprint', 'account_fingerprint', 'symbol',
    'account_currency', 'per_lot_basis', 'round_turn_account_per_lot', 'from', 'to', 'conversion_method'
)) {
    Assert-Contract ($loop -match ("broker_contract(?s).*" + [regex]::Escape($contractField))) "commission broker contract binds $contractField"
}
Assert-Contract ($loop -match 'broker_fingerprint.*server_fingerprint.*account_fingerprint.*data_fingerprint') "cost source manifest binds all execution fingerprints"
Assert-Contract ($loop -match "label = \('cost_evidence_") "execution receipt rehashes cost-source evidence files"
Assert-Contract ($loop -match 'matched_control_run_id') "task packet binds the matched control"
Assert-Contract ($loop -match 'matched_control_manifest_sha256') "task packet binds matched-control manifest hash"
Assert-Contract ($loop -match 'matched_control_report_sha256') "task packet binds matched-control report hash"
Assert-Contract ($loop -match 'matched_control_sidecar') "execution receipt binds matched-control sidecar files"
Assert-Contract ($loop -match 'matched_control_artifact') "execution receipt binds matched-control source/config/EX5/include artifacts"
Assert-Contract ($loop -match 'function\s+Resolve-MatchedControl') "research loop resolves matched control inside the EA runs root"
Assert-Contract ($loop -match "RunRole -ceq 'challenger'") "matched-control evidence is conditional only for challenger role"
Assert-Contract ($loop -match 'Control run id contains unsupported characters') "matched-control path traversal is rejected"
Assert-Contract ($loop -match '(?s)\$expectedFields\s*=.*deposit.*leverage.*source_sha256') "matched control verifies economic contract fields"
Assert-Contract ($loop -match '(?s)\$expectedFields\s*=.*execution_mode.*fixed_delay_ms.*spread') "matched control binds execution and spread settings"
Assert-Contract ($loop -match '(?s)\$expectedFields\s*=.*overrides.*config_sha256.*report_sha256.*git_commit.*git_status_sha256') "matched control binds authoritative hashes and git identity"
Assert-Contract ($loop -match '(?s)\$expectedFields\s*=.*broker_fingerprint.*server_fingerprint.*account_fingerprint.*data_fingerprint') "matched control binds broker, server, account, and data fingerprints"
Assert-Contract ($loop -match "Matched control sidecar hash mismatch") "matched-control sidecar contents are rehashed against the manifest"
Assert-Contract ($loop -match 'Matched control completion attestation') "matched control requires a final completed research-loop attestation"
foreach ($completionArtifact in @('verified_cost_artifact', 'validation_summary', 'research_loop_summary')) {
    Assert-Contract ($loop -match $completionArtifact) "matched control binds completion artifact $completionArtifact"
}
Assert-Contract ($loop -match 'required_sidecars') "task packet binds required sidecars"
Assert-Contract ($loop -match 'required_manifest_hashes') "task packet requires post-run source/config/report hash proof"
Assert-Contract ($loop -match "'ex5_sha256'.*'includes_sha256'") "task packet requires post-run EX5 and include-closure hash proof"
Assert-Contract ($loop -match 'function\s+New-ExecutionReceipt') "research loop creates a hash-bound execution receipt"
Assert-Contract ($loop -match "label = \('include_") "execution receipt rehashes every packet-bound include"
Assert-Contract ($loop -match 'function\s+Assert-EvidenceUnchanged') "research loop revalidates evidence against TOCTOU"
Assert-Contract ($loop -match 'function\s+Assert-RunManifestMatchesPacket') "research loop verifies post-run manifest against task packet"
Assert-Contract ($loop -match "(?s)Resolve-ExactRunDir.*?Assert-RunManifestMatchesPacket.*?Build report-bound verified cost artifact") "post-run manifest is checked before downstream evidence builders"
Assert-Contract ($loop -match 'Evidence revalidation before validation') "evidence is revalidated immediately before validation"
Assert-Contract ($loop -match 'function\s+Enter-GlobalValidationLock') "validation evidence recheck reacquires the global AlphaFactory lock"
Assert-Contract ($loop -match 'alpha_backtest\.lock') "validation lock shares the global backtest lock path"
$validationSection = [regex]::Match($loop, '(?s)# Evidence revalidation before validation.*?unified_validation_succeeded').Value
Assert-Contract (
    -not [string]::IsNullOrWhiteSpace($validationSection) -and
    $validationSection.IndexOf('Enter-GlobalValidationLock') -ge 0 -and
    $validationSection.IndexOf('Enter-GlobalValidationLock') -lt $validationSection.IndexOf('Assert-EvidenceUnchanged')
) "global validation lock is acquired before evidence revalidation"
$cleanupSection = [regex]::Match($loop, '(?s)if \(\$CleanupCommonFiles\).*?Exit-GlobalValidationLock').Value
Assert-Contract (-not [string]::IsNullOrWhiteSpace($cleanupSection)) "global AlphaFactory lock is held through Common Files cleanup"
Assert-Contract ($loop -match 'Common Files cleanup refused.*terminal64') "Common Files cleanup refuses to run while any terminal is active"
Assert-Contract ($loop -match 'execution_blockers') "dry-run exposes execution blockers"
Assert-Contract ($loop -match 'TaskPacket is required for -Execute') "execute requires a task packet"
Assert-Contract ($loop -match 'SkipCompile.*SkipValidate.*SkipCostStress.*SkipCompare') "strict execution rejects evidence skip flags"
Assert-Contract ($loop -notmatch '\$BaselineRun') "strict path has no stale baseline default"
Assert-Contract ($loop -notmatch '\$CostPerTrade') "strict path has no fixed cost-per-trade proxy"
Assert-Contract ($loop -notmatch 'sonic_cost_stress\.py') "strict path never generates proxy cost-stress evidence"
Assert-Contract ($loop -match 'analysis\\unified_validation\.py') "research loop invokes unified validator directly"
Assert-Contract ($loop -match '"--stage"') "research loop forwards validation stage"
Assert-Contract ($loop -match '"--holding-contract"') "research loop forwards holding contract"
Assert-Contract ($loop -match '"--cost-artifact"') "research loop forwards verified cost artifact"
Assert-Contract ($loop -match 'build_verified_cost_artifact\.py') "strict path requires a report-bound verified cost builder"
Assert-Contract ($loop -match '"--cost-source-manifest"') "cost builder receives the packet-bound cost source manifest"
Assert-Contract ($loop -match 'Verified cost builder is missing') "missing verified cost builder is an explicit execution blocker"
Assert-Contract ($loop -match 'ValidationStage=confirmed cannot create a new run') "strict run loop blocks impossible same-invocation confirmed promotion"
Assert-Contract ($loop -match 'requires MT5 Model=0 \(real ticks\)') "strict research loop blocks non-Model-0 execution"
Assert-Contract ($loop -match 'audit_mql5_nonrepaint\.py') "strict research loop invokes the snapshot-bound non-repaint auditor"
Assert-Contract ($loop -match 'nonrepaint_audit_passed') "research completion records a passed non-repaint transition"
Assert-Contract ($loop -match "verdict -cne 'RESEARCH_PASS'") "challenger comparison requires the semantic RESEARCH_PASS verdict"
Assert-Contract ($loop -match 'candidate\.run_id -cne \$runId') "challenger comparison binds the candidate run id"
Assert-Contract ($loop -match 'baseline\.run_id -cne \$packetResult\.MatchedControlRunId') "challenger comparison binds the matched-control run id"
Assert-Contract ($loop -match '"--wfa-artifact"') "research loop can forward WFA artifact"
Assert-Contract ($loop -match '"--variants-dir"') "research loop can forward tried variants"
Assert-Contract ($loop -notmatch '&\s+\$alphaPs1\s+validate-full') "research loop does not route strict validation through legacy alpha defaults"

Assert-Contract ($alpha -match '\[string\]\$ValidationStage') "alpha validate-full exposes validation stage"
Assert-Contract ($alpha -match '\[string\]\$HoldingContract') "alpha validate-full exposes holding contract"
Assert-Contract ($alpha -match '\[string\]\$CostArtifact') "alpha validate-full exposes cost artifact"
Assert-Contract ($alpha -match '\[string\]\$WfaArtifact') "alpha validate-full exposes WFA artifact"
Assert-Contract ($alpha -match '\[string\]\$VariantsDir') "alpha validate-full exposes variants directory"
Assert-Contract ($alpha -match 'Unified validation failed with exit code') "alpha validate-full throws on validator nonzero"
Assert-Contract ($alpha -match 'audit_mql5_nonrepaint\.py') "alpha validate-full regenerates the snapshot-bound non-repaint artifact"
Assert-Contract ($alpha -match 'Non-repaint audit failed with exit code') "alpha validate-full fails closed on non-repaint audit failure"

if (-not $StaticOnly) {
    foreach ($definition in (Get-FunctionDefinitionText $alphaPath @(
        'Get-TextSha256',
        'Assert-BacktestScalarContract',
        'ConvertTo-NormalizedOverrideMap',
        'ConvertFrom-NormalizedOverrideMap',
        'Get-TelemetryInputNames',
        'Resolve-TelemetryTierOverrides',
        'Assert-ReceiptSourceMatchesMain',
        'Get-ReportLabeledValue',
        'Get-ReportIdentity',
        'Get-RelativePathUnderRoot',
        'Assert-NonArchiveInclude',
        'Resolve-IncludeDependency',
        'Get-IncludeDependencyClosure',
        'Get-RunnerTerminalProcessIdentity',
        'Test-RunnerOwnedTerminalIdentity'
    ))) { Invoke-Expression $definition }
    . $eaContractPath
    foreach ($definition in (Get-FunctionDefinitionText $loopPath @(
        'Get-Sha256IfExists',
        'Get-DirectoryTreeSha256',
        'Get-PathHashSetSha256',
        'Get-ManifestIncludeSetSha256',
        'Test-Sha256Text',
        'Test-IntegerValue',
        'Test-NonNegativeNumber',
        'Test-ProvenanceObject',
        'Get-ObjectProperty',
        'Assert-EvidenceUnchanged',
        'Assert-RunManifestMatchesPacket'
    ))) { Invoke-Expression $definition }

    $hardeningTemp = Join-Path $env:TEMP ("runner_hardening_contract_{0}" -f ([guid]::NewGuid().ToString('N')))
    try {
        New-Item -ItemType Directory -Path $hardeningTemp -Force | Out-Null
        $silverContract = Resolve-EaSourceContract -RepoRoot $repoRoot -EaName 'EA_SilverBullet'
        $expectedSilverRelative = '03. EA Developer/EA_SilverBullet/EA_SilverBullet_v2.mq5'
        $expectedSilverAbsolute = [System.IO.Path]::GetFullPath((Join-Path $repoRoot '03. EA Developer\EA_SilverBullet\EA_SilverBullet_v2.mq5'))
        Assert-Contract ($silverContract.RepoRelativeSource -ceq $expectedSilverRelative) "shared source contract returns the exact SilverBullet repo-relative main"
        Assert-Contract ([string]::Equals($silverContract.AbsoluteSource, $expectedSilverAbsolute, [System.StringComparison]::OrdinalIgnoreCase)) "shared source contract returns the exact SilverBullet absolute main"
        Assert-Contract ($silverContract.TelemetryProfile -ceq 'none' -and $silverContract.IsPinned) "SilverBullet source contract is pinned with telemetry profile none"

        $sonicCaseVariantContract = Resolve-EaSourceContract -RepoRoot $repoRoot -EaName 'ea_sonicr'
        Assert-Contract ($sonicCaseVariantContract.TelemetryProfile -ceq 'sonic-strict') "Sonic telemetry profile cannot be bypassed by EA-name casing"

        $missingPinnedRoot = Join-Path $hardeningTemp 'missing-pinned-source'
        $missingPinnedEaRoot = Join-Path $missingPinnedRoot '03. EA Developer\EA_SilverBullet'
        New-Item -ItemType Directory -Path $missingPinnedEaRoot -Force | Out-Null
        '// index decoy' | Set-Content -LiteralPath (Join-Path $missingPinnedEaRoot 'EA_SilverBullet_v2_Index.mq5') -Encoding UTF8
        $missingPinnedError = $null
        try { [void](Resolve-EaSourceContract -RepoRoot $missingPinnedRoot -EaName 'EA_SilverBullet') } catch { $missingPinnedError = $_.Exception.Message }
        Assert-Contract ($missingPinnedError -match 'Pinned EA source is missing.*EA_SilverBullet_v2\.mq5') "missing pinned SilverBullet v2 fails closed without selecting the Index variant"

        $unsafeScalarError = $null
        try {
            Assert-BacktestScalarContract 'EA_SonicR' 'CONTRACT-HYPOTHESIS' "XAUUSD`r`n[Tester]" 'M5' '2024.01.01' '2025.12.31' '' 0 0
        } catch { $unsafeScalarError = $_.Exception.Message }
        Assert-Contract ($unsafeScalarError -match 'Symbol contains unsupported or unsafe INI characters') "INI-bound symbol rejects CRLF section injection"

        $unsafeOverrideError = $null
        try {
            [void](ConvertTo-NormalizedOverrideMap "InpVariantTag=X`r`n[Tester]`r`nExecutionMode=99")
        } catch { $unsafeOverrideError = $_.Exception.Message }
        Assert-Contract ($unsafeOverrideError -match 'Malformed tester override|unsafe control') "tester override rejects CRLF section injection"

        $unsafeOverrideNameError = $null
        try { [void](ConvertTo-NormalizedOverrideMap '[Tester]=99') } catch { $unsafeOverrideNameError = $_.Exception.Message }
        Assert-Contract ($unsafeOverrideNameError -match 'input name.*unsafe') "tester override rejects non-identifier input names"

        $archiveFixtureRoot = Join-Path $hardeningTemp 'archive-include-fixture'
        $script:AdvisorsRoot = $archiveFixtureRoot
        $script:AlphaRoot = Join-Path $archiveFixtureRoot '02. AlphaFactory'
        $script:MT5Mql5Root = Join-Path $archiveFixtureRoot 'terminal-mql5'
        $activeEaRoot = Join-Path $archiveFixtureRoot '03. EA Developer\EA_Test'
        $archiveRoot = Join-Path $archiveFixtureRoot '00. Old File'
        New-Item -ItemType Directory -Path $activeEaRoot, $archiveRoot, (Join-Path $script:MT5Mql5Root 'Include') -Force | Out-Null
        $archiveInclude = Join-Path $archiveRoot 'Legacy.mqh'
        '// archived dependency' | Set-Content -LiteralPath $archiveInclude -Encoding UTF8
        $archiveMain = Join-Path $activeEaRoot 'EA_Test.mq5'
        '#include "..\..\00. Old File\Legacy.mqh"' | Set-Content -LiteralPath $archiveMain -Encoding UTF8
        $archiveIncludeError = $null
        try { [void](Get-IncludeDependencyClosure $archiveMain) } catch { $archiveIncludeError = $_.Exception.Message }
        Assert-Contract ($archiveIncludeError -match 'Archived include dependency is forbidden') "include closure dynamically rejects a dependency under 00. Old File"

        $localShadow = Join-Path $activeEaRoot 'Shadow.mqh'
        $terminalIncludeRoot = Join-Path $script:MT5Mql5Root 'Include'
        $terminalShadow = Join-Path $terminalIncludeRoot 'Shadow.mqh'
        '// source-relative shadow' | Set-Content -LiteralPath $localShadow -Encoding UTF8
        '// terminal include' | Set-Content -LiteralPath $terminalShadow -Encoding UTF8

        $systemIncludeMain = Join-Path $activeEaRoot 'EA_SystemInclude.mq5'
        '#include <Shadow.mqh>' | Set-Content -LiteralPath $systemIncludeMain -Encoding UTF8
        $systemIncludeClosure = @(Get-IncludeDependencyClosure $systemIncludeMain)
        Assert-Contract (
            $systemIncludeClosure.Count -eq 1 -and
            [System.IO.Path]::GetFullPath($systemIncludeClosure[0]) -ieq [System.IO.Path]::GetFullPath($terminalShadow)
        ) "angle include resolves only from terminal MQL5 Include despite a source-relative shadow"

        $localIncludeMain = Join-Path $activeEaRoot 'EA_LocalInclude.mq5'
        '#include "Shadow.mqh"' | Set-Content -LiteralPath $localIncludeMain -Encoding UTF8
        $localIncludeClosure = @(Get-IncludeDependencyClosure $localIncludeMain)
        Assert-Contract (
            $localIncludeClosure.Count -eq 1 -and
            [System.IO.Path]::GetFullPath($localIncludeClosure[0]) -ieq [System.IO.Path]::GetFullPath($localShadow)
        ) "quoted include resolves only relative to the including source despite a terminal shadow"

        $terminalOnlyInclude = Join-Path $terminalIncludeRoot 'TerminalOnly.mqh'
        '// terminal only' | Set-Content -LiteralPath $terminalOnlyInclude -Encoding UTF8
        $quotedTerminalOnlyMain = Join-Path $activeEaRoot 'EA_QuotedTerminalOnly.mq5'
        '#include "TerminalOnly.mqh"' | Set-Content -LiteralPath $quotedTerminalOnlyMain -Encoding UTF8
        $quotedTerminalFallbackError = $null
        try { [void](Get-IncludeDependencyClosure $quotedTerminalOnlyMain) } catch { $quotedTerminalFallbackError = $_.Exception.Message }
        Assert-Contract ($quotedTerminalFallbackError -match 'Include dependency cannot be resolved') "quoted include never falls back to terminal MQL5 Include"

        $localOnlyInclude = Join-Path $activeEaRoot 'LocalOnly.mqh'
        '// source relative only' | Set-Content -LiteralPath $localOnlyInclude -Encoding UTF8
        $angleLocalOnlyMain = Join-Path $activeEaRoot 'EA_AngleLocalOnly.mq5'
        '#include <LocalOnly.mqh>' | Set-Content -LiteralPath $angleLocalOnlyMain -Encoding UTF8
        $angleLocalFallbackError = $null
        try { [void](Get-IncludeDependencyClosure $angleLocalOnlyMain) } catch { $angleLocalFallbackError = $_.Exception.Message }
        Assert-Contract ($angleLocalFallbackError -match 'Include dependency cannot be resolved') "angle include never falls back to the including source directory"

        $reportIdentityFixture = Join-Path $hardeningTemp 'identity-report.html'
        @'
<html><body>
<b>Broker-Demo (Build 6000)</b>
<tr align="right"><td>Broker Label:</td><td align="left"><b>Broker Ltd</b></td></tr>
<tr align="right"><td>Currency Label:</td><td align="left"><b>USD</b></td></tr>
<tr align="right"><td>Deposit Label:</td><td align="left"><b>10 000.00</b></td></tr>
<tr align="right"><td>Leverage Label:</td><td align="left"><b>1:100</b></td></tr>
<tr align="right"><td>History Quality:</td><td><b>99%</b></td></tr>
<tr align="right"><td>Bars:</td><td><b>1234</b></td></tr>
<tr align="right"><td>Ticks:</td><td><b>5678</b></td></tr>
</body></html>
'@ | Set-Content -LiteralPath $reportIdentityFixture -Encoding UTF8
        $reportIdentity = Get-ReportIdentity $reportIdentityFixture ([pscustomobject]@{
            symbol = 'XAUUSD'; period = 'M5'; from = '2024.01.01'; to = '2025.12.31'; model = 1
            deposit = 10000; leverage = 100; spread = 'current'
            contract_symbol_geometry = [pscustomobject]@{ digits = 2; point = 0.01; pip_size = 0.01 }
        })
        Assert-Contract (
            $reportIdentity.Basis.broker -ceq 'Broker Ltd' -and
            $reportIdentity.Basis.currency -ceq 'USD' -and
            (Test-Sha256Text $reportIdentity.BrokerFingerprint) -and
            (Test-Sha256Text $reportIdentity.ServerFingerprint) -and
            (Test-Sha256Text $reportIdentity.AccountFingerprint) -and
            (Test-Sha256Text $reportIdentity.DataFingerprint)
        ) "report-derived broker, server, account, and data fingerprints are complete"

        $telemetryInputs = @(
            'InpEnableTelemetry', 'InpEnableOpportunityLogger', 'InpEnableShadowNarrative',
            'InpEnableStateTelemetry', 'InpEnableGoldRegimeTelemetry',
            'InpEnableSourceClassicDragonEdgeDistanceTelemetry', 'InpEnableSourceH4TargetRunwayTelemetry',
            'InpEnableFxM15MtfPvaWeakeningTelemetry', 'InpEnableFxClassicNearMissTelemetry'
        )
        $telemetryFixture = Join-Path $hardeningTemp 'TelemetryFixture.mq5'
        ($telemetryInputs | ForEach-Object { "input bool $_ = false;" }) | Set-Content -LiteralPath $telemetryFixture -Encoding UTF8
        $expectedEnabled = @{
            'off' = @()
            'trade-only' = @('InpEnableTelemetry')
            'state-lite' = @('InpEnableTelemetry', 'InpEnableOpportunityLogger', 'InpEnableStateTelemetry')
            'state-full' = @($telemetryInputs)
            'snapshot-casebook' = @($telemetryInputs)
        }
        foreach ($tier in @('off', 'trade-only', 'state-lite', 'state-full', 'snapshot-casebook')) {
            $resolved = Resolve-TelemetryTierOverrides $tier $telemetryFixture 'InpVariantTag=CONTRACT;InpEnableTelemetry=false'
            $map = ConvertTo-NormalizedOverrideMap $resolved
            $tierCorrect = ([string]$map['InpVariantTag'] -ceq 'CONTRACT')
            foreach ($inputName in $telemetryInputs) {
                $expectedValue = if ($inputName -in $expectedEnabled[$tier]) { 'true' } else { 'false' }
                $tierCorrect = $tierCorrect -and ([string]$map[$inputName] -ceq $expectedValue)
            }
            Assert-Contract $tierCorrect "telemetry tier '$tier' deterministically overrides all telemetry flags"
        }

        $missingTelemetryFixture = Join-Path $hardeningTemp 'TelemetryMissingInput.mq5'
        ($telemetryInputs[0..($telemetryInputs.Count - 2)] | ForEach-Object { "input bool $_ = false;" }) |
            Set-Content -LiteralPath $missingTelemetryFixture -Encoding UTF8
        $missingTelemetryError = $null
        try { [void](Resolve-TelemetryTierOverrides 'state-full' $missingTelemetryFixture '') } catch { $missingTelemetryError = $_.Exception.Message }
        Assert-Contract ($missingTelemetryError -match 'EA input.*required for telemetry tier.*is absent') "telemetry mapping fails closed when an EA input declaration is missing"

        $nonSonicFixture = Join-Path $hardeningTemp 'NonSonicFixture.mq5'
        'input bool InpEnabled = true;' | Set-Content -LiteralPath $nonSonicFixture -Encoding UTF8
        $nonSonicOffError = $null
        $nonSonicOffResolved = $null
        try { $nonSonicOffResolved = Resolve-TelemetryTierOverrides 'off' $nonSonicFixture 'InpEnabled=false' 'none' } catch { $nonSonicOffError = $_.Exception.Message }
        Assert-Contract ([string]::IsNullOrWhiteSpace($nonSonicOffError)) "telemetry tier off accepts an EA with no Sonic telemetry inputs"
        Assert-Contract ($nonSonicOffResolved -ceq 'InpEnabled=false') "telemetry tier off leaves non-Sonic overrides unchanged"

        $nonSonicTradeError = $null
        try { [void](Resolve-TelemetryTierOverrides 'trade-only' $nonSonicFixture '' 'none') } catch { $nonSonicTradeError = $_.Exception.Message }
        Assert-Contract ($nonSonicTradeError -match "telemetry tier 'trade-only'.*not supported") "non-Sonic telemetry tiers above off fail closed"

        $sonicMissingAllOffError = $null
        try { [void](Resolve-TelemetryTierOverrides 'off' $nonSonicFixture '' 'sonic-strict') } catch { $sonicMissingAllOffError = $_.Exception.Message }
        Assert-Contract ($sonicMissingAllOffError -match 'EA input.*required for telemetry tier.*is absent') "Sonic strict telemetry still requires all declarations at tier off"

        $receiptMainA = Join-Path $hardeningTemp 'ReceiptMainA.mq5'
        $receiptMainB = Join-Path $hardeningTemp 'ReceiptMainB.mq5'
        '// a' | Set-Content -LiteralPath $receiptMainA -Encoding UTF8
        '// b' | Set-Content -LiteralPath $receiptMainB -Encoding UTF8
        $receiptCheckFixture = [pscustomobject]@{
            Receipt = [pscustomobject]@{
                evidence = @([pscustomobject]@{ label = 'source'; path = $receiptMainA })
            }
        }
        $receiptMainMismatchError = $null
        try { Assert-ReceiptSourceMatchesMain $receiptCheckFixture $receiptMainB } catch { $receiptMainMismatchError = $_.Exception.Message }
        Assert-Contract ($receiptMainMismatchError -match 'does not match resolved EA main') "receipt source mismatch is rejected before compile"

        $processIdentityError = $null
        $pidReuseRejected = $false
        try {
            $actualIdentity = Get-RunnerTerminalProcessIdentity $PID
            $wrongIdentity = [pscustomobject]@{
                Pid = $PID
                StartTimeUtc = '2000-01-01T00:00:00.0000000Z'
                ExecutablePath = $actualIdentity.ExecutablePath
            }
            $pidReuseRejected = -not (Test-RunnerOwnedTerminalIdentity $PID $wrongIdentity)
        } catch { $processIdentityError = $_.Exception.Message }
        Assert-Contract ([string]::IsNullOrWhiteSpace($processIdentityError)) "process identity probe can read PID start-time and executable"
        Assert-Contract $pidReuseRejected "process identity probe rejects a reused PID/start-time mismatch"

        $evidenceFile = Join-Path $hardeningTemp 'source.txt'
        'version-one' | Set-Content -LiteralPath $evidenceFile -Encoding UTF8
        $receiptPath = Join-Path $hardeningTemp 'receipt.json'
        @{
            schema_version = 'sonic_execution_receipt.v1'
            git_commit = ('A' * 40) -join ''
            git_status_sha256 = ('B' * 64) -join ''
            evidence = @(@{ label = 'source'; kind = 'file'; path = $evidenceFile; sha256 = Get-Sha256IfExists $evidenceFile })
        } | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $receiptPath -Encoding UTF8
        $receiptHash = Get-Sha256IfExists $receiptPath
        'version-two' | Set-Content -LiteralPath $evidenceFile -Encoding UTF8
        $receiptDriftError = $null
        try { [void](Assert-EvidenceUnchanged $receiptPath $receiptHash $null) } catch { $receiptDriftError = $_.Exception.Message }
        Assert-Contract ($receiptDriftError -match "Execution evidence 'source' changed") "execution receipt rejects source hash drift before validation"

        $variantsFixture = Join-Path $hardeningTemp 'variants'
        New-Item -ItemType Directory -Path $variantsFixture -Force | Out-Null
        'variant-one' | Set-Content -LiteralPath (Join-Path $variantsFixture 'variant.txt') -Encoding UTF8
        @{
            schema_version = 'sonic_execution_receipt.v1'
            git_commit = ('A' * 40) -join ''
            git_status_sha256 = ('B' * 64) -join ''
            evidence = @(@{ label = 'variants_dir'; kind = 'directory'; path = $variantsFixture; sha256 = Get-DirectoryTreeSha256 $variantsFixture })
        } | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $receiptPath -Encoding UTF8
        $receiptHash = Get-Sha256IfExists $receiptPath
        'variant-two' | Set-Content -LiteralPath (Join-Path $variantsFixture 'variant.txt') -Encoding UTF8
        $variantsDriftError = $null
        try { [void](Assert-EvidenceUnchanged $receiptPath $receiptHash $null) } catch { $variantsDriftError = $_.Exception.Message }
        Assert-Contract ($variantsDriftError -match "Execution evidence 'variants_dir' changed") "execution receipt rejects tried-variants directory drift before validation"

        $runFixture = Join-Path $hardeningTemp 'run'
        $logsFixture = Join-Path $runFixture 'logs'
        New-Item -ItemType Directory -Path $logsFixture -Force | Out-Null
        $sourceFixture = Join-Path $runFixture 'source.mq5'
        $configFixture = Join-Path $runFixture 'config.ini'
        $reportFixture = Join-Path $runFixture 'report.html'
        'source' | Set-Content -LiteralPath $sourceFixture -Encoding UTF8
        'config' | Set-Content -LiteralPath $configFixture -Encoding UTF8
        'report' | Set-Content -LiteralPath $reportFixture -Encoding UTF8
        $sourceHash = Get-Sha256IfExists $sourceFixture
        $fingerprintA = ('A' * 64) -join ''
        $fingerprintB = ('B' * 64) -join ''
        $fingerprintC = ('C' * 64) -join ''
        $fingerprintD = ('D' * 64) -join ''
        $receiptIdentity = ('E' * 64) -join ''
        $manifestPath = Join-Path $runFixture 'run_manifest.json'
        @{
            hypothesis_id = 'CONTRACT-HYPOTHESIS'; run_role = 'challenger'; ea_name = 'EA_SonicR'; symbol = 'XAUUSD'; period = 'M5'
            from = '2024.01.01'; to = '2025.12.31'; model = 1; execution_mode = 0; fixed_delay_ms = 0
            overrides = 'InpEnableTelemetry=false'; telemetry_tier = 'off'; deposit = 10000; leverage = 100; spread = 'current'
            source_sha256 = $sourceHash; config_sha256 = $fingerprintC; report_sha256 = Get-Sha256IfExists $reportFixture
            git_commit = ('F' * 40) -join ''; git_status_sha256 = $fingerprintA
            broker_fingerprint = $fingerprintA; server_fingerprint = $fingerprintB
            account_fingerprint = $fingerprintC; data_fingerprint = $fingerprintD
            contract_receipt_sha256 = $receiptIdentity; source_snapshot = $sourceFixture
            main_file = $sourceFixture
            config_snapshot = $configFixture; report_path = $reportFixture; required_sidecars = @(); sidecars = @()
            fingerprint_basis = @{ digits = 2; point = 0.01; pip_size = 0.01 }
        } | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
        $manifestBinding = [pscustomobject]@{
            EaName = 'EA_SonicR'; RunRole = 'challenger'; Symbol = 'XAUUSD'; Period = 'M5'; From = '2024.01.01'; To = '2025.12.31'
            Model = 1; ExecutionMode = 0; FixedDelayMs = 0; Overrides = 'InpEnableTelemetry=false'; TelemetryTier = 'off'
            Deposit = 10000; Leverage = 100; Spread = 'current'; GitCommit = ('F' * 40) -join ''
            GitStatusSha256 = $fingerprintA; BrokerFingerprint = $fingerprintA; ServerFingerprint = $fingerprintB
            AccountFingerprint = $fingerprintC; DataFingerprint = $fingerprintD
            SymbolDigits = 2; SymbolPoint = 0.01; PipSize = 0.01
        }
        $manifestPacket = [pscustomobject]@{ RequiredSidecars = @(); RequiredManifestHashes = @('source_sha256', 'config_sha256', 'report_sha256') }
        $manifestContract = [pscustomobject]@{
            HypothesisId = 'CONTRACT-HYPOTHESIS'
            CurrentSourceSha256 = $sourceHash
            CanonicalSourceAbsolute = $sourceFixture
        }
        $manifestHashError = $null
        try { [void](Assert-RunManifestMatchesPacket $manifestPath $manifestPacket $manifestBinding $manifestContract $receiptIdentity) } catch { $manifestHashError = $_.Exception.Message }
        Assert-Contract ($manifestHashError -match "Post-run manifest hash 'config_sha256' does not match artifact") "post-run manifest rejects config hash drift before validation"

        $manifestMainMismatch = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
        $manifestMainMismatch.main_file = $receiptMainB
        $manifestMainMismatch | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
        $manifestMainMismatchError = $null
        try { [void](Assert-RunManifestMatchesPacket $manifestPath $manifestPacket $manifestBinding $manifestContract $receiptIdentity) } catch { $manifestMainMismatchError = $_.Exception.Message }
        Assert-Contract ($manifestMainMismatchError -match 'main_file.*does not match resolved EA main') "post-run manifest rejects a source entrypoint mismatch"
        $manifestMainMismatch.main_file = $sourceFixture
        $manifestMainMismatch | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

        $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
        $snapshotRoot = Join-Path $runFixture 'snapshot'
        $includeRoot = Join-Path $snapshotRoot 'includes'
        New-Item -ItemType Directory -Path $includeRoot -Force | Out-Null
        $includeFixture = Join-Path $includeRoot 'SNR_Test.mqh'
        $ex5SnapshotFixture = Join-Path $snapshotRoot 'EA_SonicR.ex5'
        $testerEx5Fixture = Join-Path $runFixture 'tester-EA_SonicR.ex5'
        'include-one' | Set-Content -LiteralPath $includeFixture -Encoding UTF8
        'binary-one' | Set-Content -LiteralPath $ex5SnapshotFixture -Encoding UTF8
        Copy-Item -LiteralPath $ex5SnapshotFixture -Destination $testerEx5Fixture -Force
        $manifest.config_sha256 = Get-Sha256IfExists $configFixture
        $manifest | Add-Member -MemberType NoteProperty -Name snapshot_root -Value $snapshotRoot -Force
        $manifest | Add-Member -MemberType NoteProperty -Name ex5_snapshot -Value $ex5SnapshotFixture -Force
        $manifest | Add-Member -MemberType NoteProperty -Name ex5_sha256 -Value (Get-Sha256IfExists $ex5SnapshotFixture) -Force
        $manifest | Add-Member -MemberType NoteProperty -Name tester_ex5_path -Value $testerEx5Fixture -Force
        $manifest | Add-Member -MemberType NoteProperty -Name tester_ex5_sha256 -Value $manifest.ex5_sha256 -Force
        $manifest | Add-Member -MemberType NoteProperty -Name include_snapshots -Value @([pscustomobject]@{
            original_path = $includeFixture
            snapshot_path = $includeFixture
            sha256 = Get-Sha256IfExists $includeFixture
        }) -Force
        $manifest | Add-Member -MemberType NoteProperty -Name includes_sha256 -Value (Get-ManifestIncludeSetSha256 $manifest) -Force
        $manifestBinding | Add-Member -MemberType NoteProperty -Name IncludeClosureSha256 -Value (Get-PathHashSetSha256 @([pscustomobject]@{
            Path = $includeFixture
            Sha256 = Get-Sha256IfExists $includeFixture
        })) -Force
        $manifest | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
        $fullManifestPacket = [pscustomobject]@{
            RequiredSidecars = @()
            RequiredManifestHashes = @('source_sha256', 'config_sha256', 'report_sha256', 'ex5_sha256', 'includes_sha256')
        }
        $manifest.fingerprint_basis.point = 0.001
        $manifest | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
        $geometryMismatchError = $null
        try { [void](Assert-RunManifestMatchesPacket $manifestPath $fullManifestPacket $manifestBinding $manifestContract $receiptIdentity) } catch { $geometryMismatchError = $_.Exception.Message }
        Assert-Contract ($geometryMismatchError -match 'fingerprint_basis\.point.*does not match') "post-run manifest rejects report geometry mismatch"
        $manifest.fingerprint_basis.point = 0.01
        $manifest.fingerprint_basis.PSObject.Properties.Remove('pip_size')
        $manifest | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
        $geometryMissingError = $null
        try { [void](Assert-RunManifestMatchesPacket $manifestPath $fullManifestPacket $manifestBinding $manifestContract $receiptIdentity) } catch { $geometryMissingError = $_.Exception.Message }
        Assert-Contract ($geometryMissingError -match 'fingerprint_basis\.pip_size.*required') "post-run manifest rejects missing report geometry"
        $manifest.fingerprint_basis | Add-Member -MemberType NoteProperty -Name pip_size -Value 0.01 -Force
        $manifest | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
        'binary-two' | Set-Content -LiteralPath $testerEx5Fixture -Encoding UTF8
        $testerEx5DriftError = $null
        try { [void](Assert-RunManifestMatchesPacket $manifestPath $fullManifestPacket $manifestBinding $manifestContract $receiptIdentity) } catch { $testerEx5DriftError = $_.Exception.Message }
        Assert-Contract ($testerEx5DriftError -match 'staged tester EX5 identity') "post-run manifest rejects staged tester EX5 drift before validation"

        Copy-Item -LiteralPath $ex5SnapshotFixture -Destination $testerEx5Fixture -Force
        'include-two' | Set-Content -LiteralPath $includeFixture -Encoding UTF8
        $includeDriftError = $null
        try { [void](Assert-RunManifestMatchesPacket $manifestPath $fullManifestPacket $manifestBinding $manifestContract $receiptIdentity) } catch { $includeDriftError = $_.Exception.Message }
        Assert-Contract ($includeDriftError -match 'Include snapshot hash mismatch') "post-run manifest rejects include-closure drift before validation"
    } finally {
        if (Test-Path -LiteralPath $hardeningTemp) { Remove-Item -LiteralPath $hardeningTemp -Recurse -Force }
    }

    $missingHypothesis = Invoke-ScriptProcess $loopPath @()
    Assert-Contract ($missingHypothesis.ExitCode -ne 0) "missing hypothesis_id exits nonzero"
    Assert-Contract ($missingHypothesis.Output -match 'HypothesisId is required') "missing hypothesis_id reports the contract violation"
    Assert-Contract ($missingHypothesis.Output -notmatch 'Research loop complete') "missing hypothesis_id never prints success"

    $unknownHypothesis = Invoke-ScriptProcess $loopPath @('-HypothesisId', 'RUNNER-CONTRACT-UNKNOWN')
    Assert-Contract ($unknownHypothesis.ExitCode -ne 0) "unknown hypothesis_id exits nonzero"
    Assert-Contract ($unknownHypothesis.Output -match 'not found in registry') "unknown hypothesis_id reports missing registry evidence"
    Assert-Contract ($unknownHypothesis.Output -notmatch 'Research loop complete') "unknown hypothesis_id never prints success"

    $latestRows = @{}
    foreach ($line in (Get-Content -LiteralPath $registryPath)) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $row = $line | ConvertFrom-Json
        $hypothesisProperty = $row.PSObject.Properties['hypothesis_id']
        if ($null -ne $hypothesisProperty) {
            $latestRows[[string]$hypothesisProperty.Value] = $row
        }
    }
    $terminalFixture = $latestRows.Values | Where-Object { [string]$_.state -in @('killed', 'parked') } | Select-Object -First 1
    Assert-Contract ($null -ne $terminalFixture) "registry exposes a terminal-state negative fixture"
    if ($null -ne $terminalFixture) {
        $terminalDryRun = Invoke-ScriptProcess $loopPath @('-HypothesisId', [string]$terminalFixture.hypothesis_id)
        Assert-Contract ($terminalDryRun.ExitCode -eq 0) "terminal-state dry-run remains inspectable"
        Assert-Contract ($terminalDryRun.Output -match "terminal state '?(killed|parked)'?") "terminal-state dry-run reports the execution blocker"
        Assert-Contract ($terminalDryRun.Output -match 'TaskPacket is required for -Execute') "dry-run without a task packet reports execution blocked"
    }

    $canonicalSource = '03. EA Developer/EA_SonicR/EA_SonicR.mq5'
    $offlineFixture = $latestRows.Values | Where-Object {
        $modelProperty = $_.PSObject.Properties['model']
        $sourceProperty = $_.PSObject.Properties['source_path']
        ($null -eq $modelProperty) -or
        ($modelProperty.Value -isnot [int] -and $modelProperty.Value -isnot [long]) -or
        ($null -eq $sourceProperty) -or
        ([string]$sourceProperty.Value -cne $canonicalSource)
    } | Select-Object -First 1
    Assert-Contract ($null -ne $offlineFixture) "registry exposes an offline/non-EA negative fixture"
    if ($null -ne $offlineFixture) {
        $offlineDryRun = Invoke-ScriptProcess $loopPath @('-HypothesisId', [string]$offlineFixture.hypothesis_id)
        Assert-Contract ($offlineDryRun.ExitCode -eq 0) "offline-row dry-run remains inspectable"
        Assert-Contract ($offlineDryRun.Output -match 'integer MT5 model|source_path is not canonical') "offline-row dry-run reports non-EA execution blockers"
        Assert-Contract ($offlineDryRun.Output -match 'source SHA256') "dry-run reports registry source-hash drift"
        Assert-Contract ($offlineDryRun.Output -notmatch 'Verified cost builder is missing') "dry-run recognizes the installed report-bound cost builder"
    }

    $packetTemp = Join-Path $env:TEMP ("runner_task_packet_contract_{0}" -f ([guid]::NewGuid().ToString('N')))
    try {
        New-Item -ItemType Directory -Path $packetTemp -Force | Out-Null
        $mismatchPacketPath = Join-Path $packetTemp 'mismatch.json'
        @{ schema_version = 'sonic_research_task_packet.v1'; hypothesis_id = 'WRONG-HYPOTHESIS' } |
            ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $mismatchPacketPath -Encoding UTF8
        $packetFixtureId = if ($null -ne $offlineFixture) { [string]$offlineFixture.hypothesis_id } else { [string]$terminalFixture.hypothesis_id }
        $mismatchDryRun = Invoke-ScriptProcess $loopPath @('-HypothesisId', $packetFixtureId, '-TaskPacket', $mismatchPacketPath)
        Assert-Contract ($mismatchDryRun.ExitCode -eq 0) "mismatched task-packet dry-run remains inspectable"
        Assert-Contract ($mismatchDryRun.Output -match "field 'hypothesis_id'.*does not match") "task-packet CLI mismatch is rejected"
        Assert-Contract ($mismatchDryRun.Output -match "field 'execution_mode'.*required") "task packet without execution mode is rejected"
        Assert-Contract ($mismatchDryRun.Output -match "field 'fixed_delay_ms'.*required") "task packet without fixed execution delay is rejected"
        Assert-Contract ($mismatchDryRun.Output -match "field 'cost_source_manifest_path'.*required") "task packet without cost-source evidence is rejected"
        Assert-Contract ($mismatchDryRun.Output -match "field 'include_closure'.*required") "task packet without include-closure evidence is rejected"
        Assert-Contract ($mismatchDryRun.Output -match "field 'required_sidecars'.*required") "task packet without required sidecars is rejected"
        Assert-Contract ($mismatchDryRun.Output -match "field 'required_manifest_hashes'.*required") "task packet without post-run hash requirements is rejected"
        Assert-Contract ($mismatchDryRun.Output -match "field 'broker_fingerprint'.*SHA256") "task packet without broker identity is rejected"
        Assert-Contract ($mismatchDryRun.Output -match "field 'symbol_geometry'.*required") "task packet without symbol geometry is rejected"
        Assert-Contract ($mismatchDryRun.Output -match "field 'matched_control_config_sha256'.*SHA256") "task packet without matched-control config hash is rejected"

        $controlPacketPath = Join-Path $packetTemp 'control-bootstrap.json'
        @{ schema_version = 'sonic_research_task_packet.v1'; hypothesis_id = $packetFixtureId; run_role = 'control' } |
            ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $controlPacketPath -Encoding UTF8
        $controlDryRun = Invoke-ScriptProcess $loopPath @('-HypothesisId', $packetFixtureId, '-RunRole', 'control', '-TaskPacket', $controlPacketPath)
        Assert-Contract ($controlDryRun.ExitCode -eq 0) "control-bootstrap packet remains inspectable without MT5"
        Assert-Contract ($controlDryRun.Output -notmatch "field 'matched_control_run_id'.*required") "control-bootstrap role does not require a prior strict control"

        $spreadEvidencePath = Join-Path $packetTemp 'spread-evidence.csv'
        $commissionEvidencePath = Join-Path $packetTemp 'commission-evidence.csv'
        $slippageEvidencePath = Join-Path $packetTemp 'slippage-evidence.csv'
        $brokerContractPath = Join-Path $packetTemp 'broker-contract.txt'
        "timestamp,symbol,spread`n2024.01.01T00:00:00Z,XAUUSD,12" | Set-Content -LiteralPath $spreadEvidencePath -Encoding UTF8
        "ticket,symbol,commission`n1,XAUUSD,7.0" | Set-Content -LiteralPath $commissionEvidencePath -Encoding UTF8
        "ticket,symbol,direction,slippage`n1,XAUUSD,long,1.0" | Set-Content -LiteralPath $slippageEvidencePath -Encoding UTF8
        "Fixture broker contract for XAUUSD round-turn commission." | Set-Content -LiteralPath $brokerContractPath -Encoding UTF8

        $brokerFingerprint = ('A' * 64)
        $serverFingerprint = ('B' * 64)
        $accountFingerprint = ('C' * 64)
        $dataFingerprint = ('D' * 64)
        $newCostManifest = {
            [ordered]@{
                schema_version = 'alphafactory_cost_source_manifest.v1'
                provenance_status = 'VERIFIED'
                audit_status = 'PASS'
                verdict = 'PASS'
                broker = 'Fixture Broker'
                account_currency = 'USD'
                broker_fingerprint = $brokerFingerprint
                server_fingerprint = $serverFingerprint
                account_fingerprint = $accountFingerprint
                data_fingerprint = $dataFingerprint
                symbol = 'XAUUSD'
                from = '2024.01.01'
                to = '2025.12.31'
                symbol_geometry = [ordered]@{
                    digits = 2
                    point = 0.01
                    pip_size = 0.01
                }
                historical_spread_provenance = [ordered]@{
                    verification_status = 'VERIFIED'
                    source = $spreadEvidencePath
                    source_sha256 = Get-Sha256IfExists $spreadEvidencePath
                    symbol = 'XAUUSD'
                    coverage = [ordered]@{
                        from = '2024.01.01'
                        to = '2025.12.31'
                        sample_count = 1000
                        total_count = 1000
                        coverage_ratio = 1.0
                    }
                }
                commission_provenance = [ordered]@{
                    verification_status = 'VERIFIED'
                    source = $commissionEvidencePath
                    source_sha256 = Get-Sha256IfExists $commissionEvidencePath
                    symbol = 'XAUUSD'
                    value = 7.0
                    sample_count = 30
                    same_symbol_lifecycles = $true
                    method = 'fully closed same-symbol lifecycle round-turn commission per lot'
                }
                slippage_provenance = [ordered]@{
                    verification_status = 'VERIFIED'
                    source = $slippageEvidencePath
                    source_sha256 = Get-Sha256IfExists $slippageEvidencePath
                    symbol = 'XAUUSD'
                    sample_count = 100
                    buy_count = 50
                    sell_count = 50
                    independent_reference = $true
                    buy_reference_side = 'ask'
                    sell_reference_side = 'bid'
                    method = 'side-referenced independent adverse fill delta'
                    p90_buy = 0.7
                    p90_sell = 0.8
                    p90_roundturn = 1.5
                    slippage_unit = 'pips'
                }
                direction_aware_methodology = [ordered]@{
                    verification_status = 'VERIFIED'
                    direction_aware = $true
                    long_cost_treatment = 'entry ask and exit bid'
                    short_cost_treatment = 'entry bid and exit ask'
                }
            }
        }
        $invokeCostDryRun = {
            param([string]$Name, $Manifest)
            $manifestPath = Join-Path $packetTemp ("cost-{0}.json" -f $Name)
            $packetPath = Join-Path $packetTemp ("packet-{0}.json" -f $Name)
            $Manifest | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
            [ordered]@{
                schema_version = 'sonic_research_task_packet.v1'
                hypothesis_id = $packetFixtureId
                run_role = 'control'
                cost_source_manifest_path = $manifestPath
                cost_source_manifest_sha256 = Get-Sha256IfExists $manifestPath
                broker_fingerprint = $brokerFingerprint
                server_fingerprint = $serverFingerprint
                account_fingerprint = $accountFingerprint
                data_fingerprint = $dataFingerprint
                symbol_geometry = [ordered]@{
                    digits = 2
                    point = 0.01
                    pip_size = 0.01
                }
            } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $packetPath -Encoding UTF8
            Invoke-ScriptProcess $loopPath @(
                '-HypothesisId', $packetFixtureId,
                '-RunRole', 'control',
                '-CostSourceManifest', $manifestPath,
                '-TaskPacket', $packetPath
            )
        }

        $validCostDryRun = & $invokeCostDryRun 'valid' (& $newCostManifest)
        Assert-Contract ($validCostDryRun.ExitCode -eq 0) "artifact-backed cost-source fixture remains dry-run inspectable"
        Assert-Contract ($validCostDryRun.Output -notmatch 'historical_spread_provenance.*(missing|mismatch|coverage_ratio)') "valid spread evidence passes strict source preflight"
        Assert-Contract ($validCostDryRun.Output -notmatch 'commission_provenance.*(mismatch|30 same-symbol)') "valid commission evidence passes strict source preflight"
        Assert-Contract ($validCostDryRun.Output -notmatch 'slippage_provenance.*(mismatch|100 independent-reference)') "valid slippage evidence passes strict source preflight"

        $missingGeometryManifest = & $newCostManifest
        [void]$missingGeometryManifest.symbol_geometry.Remove('digits')
        $missingGeometryDryRun = & $invokeCostDryRun 'missing-geometry' $missingGeometryManifest
        Assert-Contract ($missingGeometryDryRun.Output -match 'symbol_geometry\.digits.*required') "cost source rejects missing symbol digits"

        $mismatchedGeometryManifest = & $newCostManifest
        $mismatchedGeometryManifest.symbol_geometry.point = 0.001
        $mismatchedGeometryDryRun = & $invokeCostDryRun 'mismatched-geometry' $mismatchedGeometryManifest
        Assert-Contract ($mismatchedGeometryDryRun.Output -match 'symbol_geometry\.point.*does not match task packet') "cost source rejects symbol point mismatch"

        $missingSlippageUnitManifest = & $newCostManifest
        [void]$missingSlippageUnitManifest.slippage_provenance.Remove('slippage_unit')
        $missingSlippageUnitDryRun = & $invokeCostDryRun 'missing-slippage-unit' $missingSlippageUnitManifest
        Assert-Contract ($missingSlippageUnitDryRun.Output -match 'slippage_provenance\.slippage_unit must equal pips') "slippage provenance rejects a missing unit"

        $wrongSlippageUnitManifest = & $newCostManifest
        $wrongSlippageUnitManifest.slippage_provenance.slippage_unit = 'points'
        $wrongSlippageUnitDryRun = & $invokeCostDryRun 'wrong-slippage-unit' $wrongSlippageUnitManifest
        Assert-Contract ($wrongSlippageUnitDryRun.Output -match 'slippage_provenance\.slippage_unit must equal pips') "slippage provenance rejects point values without deterministic conversion"

        $missingCostManifest = & $newCostManifest
        $missingCostManifest.historical_spread_provenance.source = Join-Path $packetTemp 'does-not-exist.csv'
        $missingCostManifest.historical_spread_provenance.source_sha256 = ('E' * 64)
        $missingCostDryRun = & $invokeCostDryRun 'missing' $missingCostManifest
        Assert-Contract ($missingCostDryRun.Output -match 'historical_spread_provenance\.source is missing') "cost-source preflight rejects a nonexistent internal evidence file"

        $arbitraryHashManifest = & $newCostManifest
        $arbitraryHashManifest.historical_spread_provenance.source_sha256 = ('E' * 64)
        $arbitraryHashDryRun = & $invokeCostDryRun 'arbitrary-hash' $arbitraryHashManifest
        Assert-Contract ($arbitraryHashDryRun.Output -match 'historical_spread_provenance\.source_sha256 mismatch') "cost-source preflight rejects a self-attested arbitrary evidence hash"

        $brokerContractManifest = & $newCostManifest
        $brokerContractManifest.commission_provenance.sample_count = 0
        $brokerContractManifest.commission_provenance.same_symbol_lifecycles = $false
        $brokerContractManifest.commission_provenance.broker_contract = [ordered]@{
            source = $brokerContractPath
            source_sha256 = ('E' * 64)
            broker_fingerprint = $brokerFingerprint
            server_fingerprint = $serverFingerprint
            account_fingerprint = $accountFingerprint
            symbol = 'XAUUSD'
            account_currency = 'USD'
            per_lot_basis = $true
            round_turn_account_per_lot = 7.0
            from = '2024.01.01'
            to = '2025.12.31'
            conversion_method = 'per_trade_contemporaneous'
            description = 'explicit round-turn commission contract'
        }
        $brokerContractDryRun = & $invokeCostDryRun 'broker-contract-hash' $brokerContractManifest
        Assert-Contract ($brokerContractDryRun.Output -match 'commission_provenance\.broker_contract\.source_sha256 mismatch') "commission contract alternative rejects an arbitrary broker-contract hash"

        $validBrokerContractManifest = & $newCostManifest
        [void]$validBrokerContractManifest.commission_provenance.Remove('source')
        [void]$validBrokerContractManifest.commission_provenance.Remove('source_sha256')
        [void]$validBrokerContractManifest.commission_provenance.Remove('method')
        $validBrokerContractManifest.commission_provenance.sample_count = 0
        $validBrokerContractManifest.commission_provenance.same_symbol_lifecycles = $false
        $validBrokerContractManifest.commission_provenance.broker_contract = [ordered]@{
            source = $brokerContractPath
            source_sha256 = Get-Sha256IfExists $brokerContractPath
            broker_fingerprint = $brokerFingerprint
            server_fingerprint = $serverFingerprint
            account_fingerprint = $accountFingerprint
            symbol = 'XAUUSD'
            account_currency = 'USD'
            per_lot_basis = $true
            round_turn_account_per_lot = 7.0
            from = '2024.01.01'
            to = '2025.12.31'
            conversion_method = 'per_trade_contemporaneous'
            description = 'explicit round-turn commission contract'
        }
        $validBrokerContractDryRun = & $invokeCostDryRun 'valid-broker-contract' $validBrokerContractManifest
        Assert-Contract ($validBrokerContractDryRun.Output -notmatch 'commission_provenance requires at least 30 same-symbol lifecycles|commission_provenance\.broker_contract.*(missing|mismatch|required)') "hashed explicit broker contract satisfies the commission alternative"

        $invalidBrokerIdentityManifest = & $newCostManifest
        [void]$invalidBrokerIdentityManifest.commission_provenance.Remove('source')
        [void]$invalidBrokerIdentityManifest.commission_provenance.Remove('source_sha256')
        $invalidBrokerIdentityManifest.commission_provenance.sample_count = 0
        $invalidBrokerIdentityManifest.commission_provenance.same_symbol_lifecycles = $false
        $invalidBrokerIdentityManifest.commission_provenance.broker_contract = [ordered]@{
            source = $brokerContractPath
            source_sha256 = Get-Sha256IfExists $brokerContractPath
            broker_fingerprint = $brokerFingerprint
            server_fingerprint = ('E' * 64)
            account_fingerprint = ('F' * 64)
            symbol = 'EURUSD'
            account_currency = 'EUR'
            per_lot_basis = $false
            round_turn_account_per_lot = 7.0
            from = '2023.01.01'
            to = '2026.12.31'
            conversion_method = 'fixed_snapshot'
            description = 'wrongly bound round-turn commission contract'
        }
        $invalidBrokerIdentityDryRun = & $invokeCostDryRun 'invalid-broker-identity' $invalidBrokerIdentityManifest
        foreach ($field in @('server_fingerprint', 'account_fingerprint', 'symbol', 'account_currency', 'per_lot_basis', 'from', 'to', 'conversion_method')) {
            Assert-Contract ($invalidBrokerIdentityDryRun.Output -match ("broker_contract\." + [regex]::Escape($field))) "commission contract rejects invalid $field binding"
        }

        $zeroRoundTurnManifest = & $newCostManifest
        [void]$zeroRoundTurnManifest.commission_provenance.Remove('source')
        [void]$zeroRoundTurnManifest.commission_provenance.Remove('source_sha256')
        [void]$zeroRoundTurnManifest.commission_provenance.Remove('method')
        $zeroRoundTurnManifest.commission_provenance.sample_count = 0
        $zeroRoundTurnManifest.commission_provenance.same_symbol_lifecycles = $false
        $zeroRoundTurnManifest.commission_provenance.broker_contract = $validBrokerContractManifest.commission_provenance.broker_contract.PSObject.Copy()
        $zeroRoundTurnManifest.commission_provenance.broker_contract.round_turn_account_per_lot = 0.0
        $zeroRoundTurnDryRun = & $invokeCostDryRun 'zero-round-turn' $zeroRoundTurnManifest
        Assert-Contract ($zeroRoundTurnDryRun.Output -match 'broker_contract\.round_turn_account_per_lot must be a finite number greater than zero') "commission contract rejects zero round-turn account commission"

        $mismatchedRoundTurnManifest = & $newCostManifest
        [void]$mismatchedRoundTurnManifest.commission_provenance.Remove('source')
        [void]$mismatchedRoundTurnManifest.commission_provenance.Remove('source_sha256')
        [void]$mismatchedRoundTurnManifest.commission_provenance.Remove('method')
        $mismatchedRoundTurnManifest.commission_provenance.sample_count = 0
        $mismatchedRoundTurnManifest.commission_provenance.same_symbol_lifecycles = $false
        $mismatchedRoundTurnManifest.commission_provenance.broker_contract = $validBrokerContractManifest.commission_provenance.broker_contract.PSObject.Copy()
        $mismatchedRoundTurnManifest.commission_provenance.broker_contract.round_turn_account_per_lot = 8.0
        $mismatchedRoundTurnDryRun = & $invokeCostDryRun 'mismatched-round-turn' $mismatchedRoundTurnManifest
        Assert-Contract ($mismatchedRoundTurnDryRun.Output -match 'broker_contract\.round_turn_account_per_lot must equal commission_provenance\.value') "commission contract rejects round-turn value inconsistent with commission value"

        $invalidSideSlippageManifest = & $newCostManifest
        $invalidSideSlippageManifest.slippage_provenance.sample_count = 100
        $invalidSideSlippageManifest.slippage_provenance.buy_count = 29
        $invalidSideSlippageManifest.slippage_provenance.sell_count = 29
        $invalidSideSlippageManifest.slippage_provenance.buy_reference_side = 'bid'
        $invalidSideSlippageManifest.slippage_provenance.sell_reference_side = 'ask'
        $invalidSideSlippageManifest.slippage_provenance.p90_buy = -0.1
        $invalidSideSlippageManifest.slippage_provenance.p90_sell = $null
        $invalidSideSlippageManifest.slippage_provenance.p90_roundturn = 9.9
        $invalidSideSlippageDryRun = & $invokeCostDryRun 'invalid-side-slippage' $invalidSideSlippageManifest
        foreach ($field in @('buy_count', 'sell_count', 'buy_reference_side', 'sell_reference_side', 'p90_buy', 'p90_sell')) {
            Assert-Contract ($invalidSideSlippageDryRun.Output -match ("slippage_provenance\." + [regex]::Escape($field))) "slippage provenance rejects invalid $field"
        }
        Assert-Contract ($invalidSideSlippageDryRun.Output -match 'sample_count must equal buy_count plus sell_count') "slippage provenance rejects inconsistent side-count totals"

        $mismatchedRoundturnP90Manifest = & $newCostManifest
        $mismatchedRoundturnP90Manifest.slippage_provenance.p90_roundturn = 9.9
        $mismatchedRoundturnP90DryRun = & $invokeCostDryRun 'mismatched-roundturn-p90' $mismatchedRoundturnP90Manifest
        Assert-Contract ($mismatchedRoundturnP90DryRun.Output -match 'slippage_provenance\.p90_roundturn must equal p90_buy plus p90_sell') "slippage provenance rejects a round-turn P90 inconsistent with its side P90 values"

        $zeroP90Manifest = & $newCostManifest
        [void]$zeroP90Manifest.slippage_provenance.Remove('p90')
        $zeroP90Manifest.slippage_provenance.p90_buy = 0.0
        $zeroP90Manifest.slippage_provenance.p90_sell = 0.0
        $zeroP90Manifest.slippage_provenance.p90_roundturn = 0.0
        $zeroP90DryRun = & $invokeCostDryRun 'zero-side-p90' $zeroP90Manifest
        Assert-Contract ($zeroP90DryRun.Output -notmatch 'slippage_provenance\.(p90_buy|p90_sell|p90_roundturn)') "verified zero side-specific P90 remains valid with complete samples"

        $insufficientCostManifest = & $newCostManifest
        $insufficientCostManifest.historical_spread_provenance.coverage.sample_count = 980
        $insufficientCostManifest.historical_spread_provenance.coverage.coverage_ratio = 0.98
        $insufficientCostManifest.commission_provenance.sample_count = 29
        $insufficientCostManifest.slippage_provenance.sample_count = 99
        $insufficientCostManifest.slippage_provenance.independent_reference = $false
        $insufficientCostManifest.direction_aware_methodology.short_cost_treatment = $insufficientCostManifest.direction_aware_methodology.long_cost_treatment
        $insufficientCostDryRun = & $invokeCostDryRun 'insufficient' $insufficientCostManifest
        Assert-Contract ($insufficientCostDryRun.Output -match 'coverage_ratio must be at least 0\.99') "spread provenance rejects less than 99 percent coverage"
        Assert-Contract ($insufficientCostDryRun.Output -match 'commission_provenance requires at least 30 same-symbol lifecycles') "commission provenance rejects fewer than 30 same-symbol lifecycles"
        Assert-Contract ($insufficientCostDryRun.Output -match 'slippage_provenance requires at least 100 independent-reference samples') "slippage provenance rejects fewer than 100 independent-reference samples"
        Assert-Contract ($insufficientCostDryRun.Output -match 'long and short cost treatments must be direction-specific') "cost-source preflight rejects non-directional long and short treatments"

        $mismatchedCostManifest = & $newCostManifest
        $mismatchedCostManifest.broker_fingerprint = ('F' * 64)
        $mismatchedCostManifest.server_fingerprint = ('E' * 64)
        $mismatchedCostManifest.account_fingerprint = ('0' * 64)
        $mismatchedCostManifest.data_fingerprint = ('1' * 64)
        $mismatchedCostManifest.symbol = 'EURUSD'
        $mismatchedCostManifest.from = '2024.02.01'
        $mismatchedCostManifest.to = '2025.11.30'
        $mismatchedCostManifest.historical_spread_provenance.symbol = 'EURUSD'
        $mismatchedCostManifest.historical_spread_provenance.coverage.from = '2024.02.01'
        $mismatchedCostManifest.historical_spread_provenance.coverage.to = '2025.11.30'
        $mismatchedCostManifest.commission_provenance.symbol = 'EURUSD'
        $mismatchedCostManifest.slippage_provenance.symbol = 'EURUSD'
        $mismatchedCostDryRun = & $invokeCostDryRun 'mismatched' $mismatchedCostManifest
        foreach ($fingerprintField in @('broker_fingerprint', 'server_fingerprint', 'account_fingerprint', 'data_fingerprint')) {
            Assert-Contract ($mismatchedCostDryRun.Output -match "$fingerprintField.*does not match task packet") "cost-source root rejects a $fingerprintField mismatch"
        }
        Assert-Contract ($mismatchedCostDryRun.Output -match "symbol 'EURUSD'.*does not match task packet symbol 'XAUUSD'") "cost-source evidence rejects a task-packet symbol mismatch"
        Assert-Contract ($mismatchedCostDryRun.Output -match "window '2024\.02\.01' to '2025\.11\.30'.*task packet window '2024\.01\.01' to '2025\.12\.31'") "cost-source evidence rejects a task-packet date-window mismatch"
    } finally {
        if (Test-Path -LiteralPath $packetTemp) {
            Remove-Item -LiteralPath $packetTemp -Recurse -Force
        }
    }

    if ($null -ne $offlineFixture) {
        $skipExecute = Invoke-ScriptProcess $loopPath @('-HypothesisId', [string]$offlineFixture.hypothesis_id, '-Execute', '-SkipCompile')
        Assert-Contract ($skipExecute.ExitCode -ne 0) "execute with a skip flag exits nonzero before MT5"
        Assert-Contract ($skipExecute.Output -match 'SkipCompile') "execute reports the forbidden skip flag"
        Assert-Contract ($skipExecute.Output -notmatch 'Starting MT5') "skip-flag rejection never starts MT5"
    }

    $registered = $null
    foreach ($line in (Get-Content -LiteralPath $registryPath)) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $row = $line | ConvertFrom-Json
        $hypothesisProperty = $row.PSObject.Properties['hypothesis_id']
        $preregProperty = $row.PSObject.Properties['prereg_path']
        if (($null -eq $hypothesisProperty) -or [string]::IsNullOrWhiteSpace([string]$hypothesisProperty.Value)) { continue }
        if (($null -eq $preregProperty) -or [string]::IsNullOrWhiteSpace([string]$preregProperty.Value)) { continue }
        if ([string]$preregProperty.Value -like 'not-created:*') { continue }
        $candidatePrereg = Join-Path $repoRoot ([string]$preregProperty.Value)
        if (Test-Path -LiteralPath $candidatePrereg -PathType Leaf) {
            $registered = $row
            break
        }
    }
    if ($null -eq $registered) {
        Write-Host "[SKIP] registered-hypothesis dry-run: current checkout has no registry row whose prereg_path exists" -ForegroundColor Yellow
    } else {
        Assert-Contract $true "test fixture finds a registered hypothesis with an existing prereg"
        $dryRun = Invoke-ScriptProcess $loopPath @('-HypothesisId', [string]$registered.hypothesis_id)
        Assert-Contract ($dryRun.ExitCode -eq 0) "registered hypothesis dry-run exits zero"
        Assert-Contract ($dryRun.Output -match 'CANDIDATE_REGISTRY_OK') "registered hypothesis dry-run executes the semantic registry validator"
        Assert-Contract ($dryRun.Output -match 'DRY RUN') "registered hypothesis stays dry-run without -Execute"
        Assert-Contract ($dryRun.Output -match [regex]::Escape([string]$registered.hypothesis_id)) "dry-run plan records hypothesis_id"
        Assert-Contract ($dryRun.Output -notmatch 'Research loop complete') "dry-run never prints execution success"

        $pythonShimRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("sonic-registry-python-shim-{0}" -f [guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Path $pythonShimRoot -Force | Out-Null
        $pythonShimPath = Join-Path $pythonShimRoot 'python.cmd'
        "@echo off`r`necho FORCED_REGISTRY_VALIDATOR_FAIL`r`nexit /b 23`r`n" | Set-Content -LiteralPath $pythonShimPath -Encoding ASCII
        $previousPath = $env:PATH
        try {
            $env:PATH = "$pythonShimRoot;$previousPath"
            $registryValidatorFailure = Invoke-ScriptProcess $loopPath @('-HypothesisId', [string]$registered.hypothesis_id)
        } finally {
            $env:PATH = $previousPath
            Remove-Item -LiteralPath $pythonShimRoot -Recurse -Force -ErrorAction SilentlyContinue
        }
        Assert-Contract ($registryValidatorFailure.ExitCode -ne 0) "semantic registry validator nonzero aborts dry-run"
        Assert-Contract ($registryValidatorFailure.Output -match 'FORCED_REGISTRY_VALIDATOR_FAIL') "registry validator failure preserves subprocess evidence"
        Assert-Contract ($registryValidatorFailure.Output -notmatch 'DRY RUN') "registry validator failure stops before research contract planning"
    }

    $missingEaCompile = Invoke-ScriptProcess $alphaPath @('compile', 'RUNNER_CONTRACT_MISSING_EA')
    Assert-Contract ($missingEaCompile.ExitCode -ne 0) "compile failure exits nonzero"
    Assert-Contract ($missingEaCompile.Output -notmatch 'SUCCESS:') "compile failure never prints success"

    $missingEaBacktest = Invoke-ScriptProcess $alphaPath @(
        'backtest',
        'RUNNER_CONTRACT_MISSING_EA',
        '-HypothesisId',
        'RUNNER-CONTRACT-FAILURE'
    )
    Assert-Contract ($missingEaBacktest.ExitCode -ne 0) "backtest failure exits nonzero"
    Assert-Contract ($missingEaBacktest.Output -match 'EA not found') "backtest failure preserves the concrete cause"
    Assert-Contract ($missingEaBacktest.Output -notmatch 'ALPHA_RUN_DIR=') "backtest failure never emits a success run marker"

    $missingValidationReport = Join-Path $env:TEMP ("runner_missing_report_{0}.html" -f ([guid]::NewGuid().ToString('N')))
    $validationFailure = Invoke-ScriptProcess $alphaPath @(
        'validate-full',
        '-Report', $missingValidationReport,
        '-ValidationStage', 'confirmed',
        '-HoldingContract', 'non_scalp',
        '-CostArtifact', (Join-Path $env:TEMP 'missing_cost_artifact.json'),
        '-WfaArtifact', (Join-Path $env:TEMP 'missing_wfa_artifact.json'),
        '-VariantsDir', (Join-Path $env:TEMP 'missing_variants_dir')
    )
    Assert-Contract ($validationFailure.ExitCode -ne 0) "alpha validate-full propagates missing-evidence failure"
    Assert-Contract ($validationFailure.Output -match 'Cannot find path|does not exist|not found') "alpha validate-full reports the concrete missing-report cause"
}

Write-Host "Contract checks: $passes passed, $($failures.Count) failed."
if ($failures.Count -gt 0) {
    exit 1
}

exit 0
