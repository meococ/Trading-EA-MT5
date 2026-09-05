# SessionStart: write observation snapshot. Stdout is ignored by Grok; status file is the contract.
. (Join-Path $PSScriptRoot 'lib.ps1')

function Get-StatusPath {
    if ($env:HOOK_STATUS_PATH) { return $env:HOOK_STATUS_PATH }
    $repo = Get-TradingRepoRoot
    $dir = Join-Path $repo '04. Memory'
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    return (Join-Path $dir 'mcp_session_status.json')
}

try {
    $statusPath = Get-StatusPath
    $py = Join-Path $PSScriptRoot 'session_snapshot.py'
    $python = Get-Command python -ErrorAction SilentlyContinue
    $payload = $null

    if ($env:HOOK_SKIP_LIVE -eq '1') {
        $payload = [pscustomobject]@{
            ok             = $false
            captured_at_utc = [DateTime]::UtcNow.ToString('o')
            plane          = 'observation'
            authority      = $false
            error          = 'HOOK_SKIP_LIVE=1'
        }
    }
    elseif ($python -and (Test-Path -LiteralPath $py)) {
        $raw = & $python.Source $py 2>&1 | Out-String
        try {
            $payload = $raw | ConvertFrom-Json
        }
        catch {
            $payload = [pscustomobject]@{
                ok              = $false
                captured_at_utc = [DateTime]::UtcNow.ToString('o')
                plane           = 'observation'
                authority       = $false
                error           = 'session_snapshot.py returned non-JSON'
            }
        }
    }
    else {
        $payload = [pscustomobject]@{
            ok              = $false
            captured_at_utc = [DateTime]::UtcNow.ToString('o')
            plane           = 'observation'
            authority       = $false
            error           = 'python or session_snapshot.py missing'
        }
    }

    $json = ConvertTo-HookJson $payload
    Set-Content -LiteralPath $statusPath -Value $json -Encoding UTF8

    $warning = Get-HookProp $payload @('warning')
    if ($warning) {
        [Console]::Error.WriteLine([string]$warning)
    }
    $errorText = Get-HookProp $payload @('error')
    if ($errorText) {
        [Console]::Error.WriteLine([string]$errorText)
    }
    exit 0
}
catch {
    [Console]::Error.WriteLine("session-start hook error: $($_.Exception.Message)")
    exit 0
}
