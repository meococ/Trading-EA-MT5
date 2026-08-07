function Resolve-EaSourceContract {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,
        [Parameter(Mandatory = $true)]
        [string]$EaName
    )

    if ($EaName -notmatch '^[A-Za-z0-9][A-Za-z0-9 _.-]{0,127}$') {
        throw "EA name '$EaName' contains unsupported path characters."
    }

    # Active-lane pins. Owner Path-C overrides 2026-07-15.
    # Compile/backtest from archive remains invalid evidence (AGENTS.md).
    $pinnedSources = @{
        'EA_HybridICT_Sonic' = '03. EA Developer/EA_HybridICT_Sonic/EA_HybridICT_Sonic.mq5'
        'EA_FVGConfluence'   = '03. EA Developer/EA_FVGConfluence/EA_FVGConfluence.mq5'
    }

    $repoFull = [System.IO.Path]::GetFullPath($RepoRoot).TrimEnd([char[]]'\/')
    $eaDevRoot = [System.IO.Path]::GetFullPath((Join-Path $repoFull '03. EA Developer'))
    $eaRoot = [System.IO.Path]::GetFullPath((Join-Path $repoFull "03. EA Developer\$EaName"))
    $eaRootPrefix = $eaRoot.TrimEnd([char[]]'\/') + [System.IO.Path]::DirectorySeparatorChar
    $isPinned = $pinnedSources.ContainsKey($EaName)
    $relativeSource = if ($isPinned) {
        [string]$pinnedSources[$EaName]
    } else {
        "03. EA Developer/$EaName/$EaName.mq5"
    }
    $absoluteSource = [System.IO.Path]::GetFullPath((Join-Path $repoFull ($relativeSource.Replace('/', '\'))))

    if (-not (Test-Path -LiteralPath $eaDevRoot -PathType Container)) {
        throw "Active EA Developer root missing: $eaDevRoot"
    }

    $activePackages = @(Get-ChildItem -LiteralPath $eaDevRoot -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like 'EA_*' } |
        Select-Object -ExpandProperty Name)

    if (-not $absoluteSource.StartsWith($eaRootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "EA source contract escapes the active EA root: $relativeSource"
    }
    if ([System.IO.Path]::GetExtension($absoluteSource) -ine '.mq5') {
        throw "EA source contract must resolve to an .mq5 file: $relativeSource"
    }
    if (-not (Test-Path -LiteralPath $absoluteSource -PathType Leaf)) {
        $shelfNote = if ($activePackages.Count -eq 0) {
            'Active EA Developer shelf is empty (Owner archived packages to 00. Old File/EA_Archive/ on 2026-07-15). Restore an EA under 03. EA Developer/ and update hot.md before compile/backtest.'
        } else {
            "Active packages present: $($activePackages -join ', ')."
        }
        if ($isPinned) {
            throw "Pinned EA source is missing for ${EaName}: $absoluteSource. $shelfNote"
        }
        throw "EA not found: canonical source is missing for ${EaName}: $absoluteSource. $shelfNote Archive paths are not valid compile/evidence sources."
    }

    $contractRelative = "03. EA Developer/$EaName/ALPHAFACTORY_EA_CONTRACT.json"
    $contractAbsolute = [System.IO.Path]::GetFullPath((Join-Path $repoFull ($contractRelative.Replace('/', '\'))))
    $telemetryProfile = 'none'
    $marketPhaseAdapter = 'none'
    $comparisonAdapter = 'generic-control-improvement-v1'
    $variantTagInput = $null
    $contractSha256 = $null
    $indicatorDependencies = @()

    if (Test-Path -LiteralPath $contractAbsolute -PathType Leaf) {
        try {
            $packageContract = Get-Content -LiteralPath $contractAbsolute -Raw | ConvertFrom-Json
        } catch {
            throw "EA capability contract is malformed JSON: $contractAbsolute ($($_.Exception.Message))"
        }
        if ([string]$packageContract.schema_version -cne 'alphafactory_ea_contract.v1') {
            throw "EA capability contract schema must be 'alphafactory_ea_contract.v1': $contractAbsolute"
        }
        $telemetryProfile = [string]$packageContract.telemetry_profile
        $marketPhaseAdapter = [string]$packageContract.market_phase_adapter
        $comparisonAdapter = [string]$packageContract.comparison_adapter
        $variantTagInput = if ($null -eq $packageContract.variant_tag_input) { $null } else { [string]$packageContract.variant_tag_input }

        if ($telemetryProfile -notin @('none', 'lifecycle-v3', 'sonic-strict')) {
            throw "Unsupported telemetry_profile '$telemetryProfile' in $contractAbsolute"
        }
        if ($marketPhaseAdapter -notin @('none', 'sonic')) {
            throw "Unsupported market_phase_adapter '$marketPhaseAdapter' in $contractAbsolute"
        }
        if ($comparisonAdapter -notin @('generic-control-improvement-v1', 'sonic-v1')) {
            throw "Unsupported comparison_adapter '$comparisonAdapter' in $contractAbsolute"
        }
        if (-not [string]::IsNullOrWhiteSpace($variantTagInput) -and $variantTagInput -notmatch '^[A-Za-z_][A-Za-z0-9_]{0,63}$') {
            throw "variant_tag_input is not a safe MQL5 input name in $contractAbsolute"
        }
        if ($telemetryProfile -ceq 'none' -and $marketPhaseAdapter -cne 'none') {
            throw "market_phase_adapter must be 'none' when telemetry_profile is 'none': $contractAbsolute"
        }
        if ($marketPhaseAdapter -ceq 'sonic' -and $telemetryProfile -cne 'sonic-strict') {
            throw "market_phase_adapter 'sonic' requires telemetry_profile 'sonic-strict': $contractAbsolute"
        }
        if ($comparisonAdapter -ceq 'sonic-v1' -and $telemetryProfile -cne 'sonic-strict') {
            throw "comparison_adapter 'sonic-v1' requires telemetry_profile 'sonic-strict': $contractAbsolute"
        }
        $dependencyNames = @{}
        $dependencyProperty = $packageContract.PSObject.Properties['indicator_dependencies']
        $declaredDependencies = if ($null -eq $dependencyProperty -or $null -eq $dependencyProperty.Value) {
            @()
        } else {
            @($dependencyProperty.Value)
        }
        foreach ($dependency in $declaredDependencies) {
            $name = [string]$dependency.name
            $sourceRelative = ([string]$dependency.source).Replace('\', '/')
            $terminalRelative = ([string]$dependency.terminal_ex5).Replace('/', '\')
            if ($name -notmatch '^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$' -or $dependencyNames.ContainsKey($name)) {
                throw "Indicator dependency has an unsafe or duplicate name '$name' in $contractAbsolute"
            }
            if ([string]::IsNullOrWhiteSpace($sourceRelative) -or [System.IO.Path]::IsPathRooted($sourceRelative) -or
                $sourceRelative -match '(^|/)\.\.(/|$)' -or [System.IO.Path]::GetExtension($sourceRelative) -ine '.mq5') {
                throw "Indicator dependency '$name' has an unsafe source path in $contractAbsolute"
            }
            $sourceAbsolute = [System.IO.Path]::GetFullPath((Join-Path $repoFull $sourceRelative.Replace('/', '\')))
            $repoPrefix = $repoFull + [System.IO.Path]::DirectorySeparatorChar
            if (-not $sourceAbsolute.StartsWith($repoPrefix, [System.StringComparison]::OrdinalIgnoreCase) -or
                -not (Test-Path -LiteralPath $sourceAbsolute -PathType Leaf)) {
                throw "Indicator dependency '$name' source is missing or escapes the repository: $sourceAbsolute"
            }
            if ([string]::IsNullOrWhiteSpace($terminalRelative) -or [System.IO.Path]::IsPathRooted($terminalRelative) -or
                $terminalRelative -match '(^|\\)\.\.(\\|$)' -or [System.IO.Path]::GetExtension($terminalRelative) -ine '.ex5') {
                throw "Indicator dependency '$name' has an unsafe terminal_ex5 path in $contractAbsolute"
            }
            $dependencyNames[$name] = $true
            $indicatorDependencies += [pscustomobject]@{
                Name = $name
                SourceRelativePath = $sourceRelative
                SourceAbsolutePath = $sourceAbsolute
                TerminalEx5RelativePath = $terminalRelative
            }
        }
        $contractSha256 = (Get-FileHash -LiteralPath $contractAbsolute -Algorithm SHA256).Hash
    }

    return [pscustomobject]@{
        EaName = $EaName
        RepoRelativeSource = $relativeSource.Replace('\', '/')
        AbsoluteSource = $absoluteSource
        TelemetryProfile = $telemetryProfile
        MarketPhaseAdapter = $marketPhaseAdapter
        ComparisonAdapter = $comparisonAdapter
        VariantTagInput = $variantTagInput
        ContractRelativePath = if ($null -eq $contractSha256) { $null } else { $contractRelative }
        ContractAbsolutePath = if ($null -eq $contractSha256) { $null } else { $contractAbsolute }
        ContractSha256 = $contractSha256
        IndicatorDependencies = @($indicatorDependencies)
        IsPinned = $isPinned
    }
}
