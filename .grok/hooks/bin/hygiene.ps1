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

$script:SecretLinePatterns = @(
    'password\s*[:=]\s*\S+'
    'BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY'
    '(?i)authorization\s*[:=]\s*bearer\s+\S+'
    '(?i)api[_-]?key\s*[:=]\s*\S+'
    '"login"\s*:\s*"?\d{6,}'
    '(?i)C:\\Users\\'
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
