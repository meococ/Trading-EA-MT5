# Shared secret/artifact hygiene for Grok PreToolUse and git pre-commit.
# Scan added lines only for content; always scan names and size.

Set-StrictMode -Version 1
$ErrorActionPreference = 'Stop'

$script:MaxCommitBytes = 5MB

$script:ForbiddenNamePatterns = @(
    '(^|[/\\])alpha\.local\.ps1$'
    '(^|[/\\])\.mcp\.json$'
    '(^|[/\\])[^/\\]*credentials[^/\\]*$'
    '\.(pem|key|secret)$'
    'raw_history_deals'
    '\.parquet$'
    'recovery-codes'
    '(^|[/\\])id_rsa'
)

# Value patterns carry two guards (2026-09-11): a keyword guard so PowerShell
# variables and CLI flags (`$token = ...`, `-Secret $x`) are not secrets, and a
# placeholder guard so documentation like `password=...` or `password=<pw>`
# does not flag. Only a real-looking literal value matches.
$script:SecretValuePatterns = @(
    '(?i)(?<![$\w.-])password["'']?\s*[:=]\s*(?!\.{3}|<|\$|\s*$|\(|@)\S+'
    '(?i)(?<![$\w.-])passwd["'']?\s*[:=]\s*(?!\.{3}|<|\$|\s*$|\(|@)\S+'
    '(?i)(?<![$\w.-])token["'']?\s*[:=]\s*(?!\.{3}|<|\$|\s*$|\(|@)\S+'
    '(?i)(?<![$\w.-])secret["'']?\s*[:=]\s*(?!\.{3}|<|\$|\s*$|\(|@)\S+'
    '(?i)(?<![$\w.-])api[_-]?key["'']?\s*[:=]\s*(?!\.{3}|<|\$|\s*$|\(|@)\S+'
)
$script:SecretLinePatterns = @(
    'BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY'
    '(?i)authorization\s*[:=]\s*bearer\s+\S+'
    '(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}'
    '"login"\s*:\s*"?\d{6,}'
) + $script:SecretValuePatterns

# Machine-local absolute paths on the owner drives (2026-09-11). These are
# skipped for files whose job is to carry them — see OwnerPathAllowedFiles.
$script:OwnerPathPatterns = @(
    '(?i)C:[\\/]+Users[\\/]'
    '(?i)C:[\\/]+Users[\\/]+toila'
    '(?i)D:[\\/]+Meta 5'
    '(?i)D:[\\/]+Trading EA MT5'
)

# Files that legitimately embed the owner machine paths (hook code, the
# AlphaFactory machine-config scripts, the memory/source-of-truth docs). The
# owner-path patterns are skipped for these; the credential patterns still
# apply.
$script:OwnerPathAllowedFiles = @(
    '(^|/)\.grok/hooks/'
    '(^|/)\.githooks/'
    '(^|/)02\. AlphaFactory/'
    '(^|/)04\. Memory/hot[^/]*\.md$'
    '(^|/)04\. Memory/source_of_truth\.(md|json)$'
    '(^|/)CONTRIBUTING\.md$'
    '(^|/)AGENTS\.md$'
)

function Test-ForbiddenRelativePath {
    param([string]$RelativePath)
    if ([string]::IsNullOrWhiteSpace($RelativePath)) { return $false }
    $norm = $RelativePath.Replace('\', '/')
    foreach ($pat in $script:ForbiddenNamePatterns) {
        if ([regex]::IsMatch($norm, $pat, 'IgnoreCase, CultureInvariant')) { return $true }
    }
    return $false
}

function Test-SecretContent {
    param([string]$Text, [string]$RelativePath = '')
    if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
    foreach ($pat in $script:SecretLinePatterns) {
        if ([regex]::IsMatch($Text, $pat, 'CultureInvariant')) { return $true }
    }
    $normRel = $RelativePath.Replace('\', '/')
    $skipOwnerPaths = $false
    foreach ($allow in $script:OwnerPathAllowedFiles) {
        if ([regex]::IsMatch($normRel, $allow, 'CultureInvariant')) { $skipOwnerPaths = $true; break }
    }
    if (-not $skipOwnerPaths) {
        foreach ($pat in $script:OwnerPathPatterns) {
            if ([regex]::IsMatch($Text, $pat, 'CultureInvariant')) { return $true }
        }
    }
    return $false
}

function Get-AddedDiffLines {
    param([string]$DiffText)
    $added = New-Object System.Collections.Generic.List[string]
    if ([string]::IsNullOrWhiteSpace($DiffText)) { return $added }
    foreach ($line in ($DiffText -split "`n")) {
        if ($line.StartsWith('+') -and -not $line.StartsWith('+++')) {
            [void]$added.Add($line.Substring(1))
        }
    }
    return $added
}

function Get-GitStagedViolations {
    param([string]$RepoRoot)
    $violations = New-Object System.Collections.Generic.List[string]
    Push-Location -LiteralPath $RepoRoot
    try {
        $files = @(git diff --cached --name-only --diff-filter=ACMR)
        foreach ($rel in $files) {
            if ([string]::IsNullOrWhiteSpace($rel)) { continue }
            if (Test-ForbiddenRelativePath $rel) {
                [void]$violations.Add("forbidden path staged: $rel")
                continue
            }
            $abs = Join-Path $RepoRoot $rel
            if (Test-Path -LiteralPath $abs -PathType Leaf) {
                $len = (Get-Item -LiteralPath $abs).Length
                if ($len -gt $script:MaxCommitBytes) {
                    [void]$violations.Add(("file exceeds 5 MB ($len bytes): {0}" -f $rel))
                }
            }
            $diff = git diff --cached -U0 -- $rel 2>$null | Out-String
            $added = (Get-AddedDiffLines $diff) -join "`n"
            if (Test-SecretContent $added $rel) {
                [void]$violations.Add("secret/account/machine-path content in added lines: $rel")
            }
        }
    }
    finally {
        Pop-Location
    }
    return $violations
}

function Get-GitUntrackedForbidden {
    # 2026-09-11: untracked entries whose names are forbidden. Warn-only — they
    # cannot enter this commit, but they are one blanket `git add` away from
    # doing so, and gitignored paths never show up here anyway.
    param([string]$RepoRoot)
    $hits = New-Object System.Collections.Generic.List[string]
    Push-Location -LiteralPath $RepoRoot
    try {
        $lines = @(git status --porcelain --untracked-files=all 2>$null)
        foreach ($l in $lines) {
            if ($l -match '^\?\?\s+"?(?<p>.+?)"?$') {
                $rel = $Matches['p'].TrimEnd('/')
                if (Test-ForbiddenRelativePath $rel) { [void]$hits.Add($rel) }
            }
        }
    }
    finally {
        Pop-Location
    }
    return $hits
}
