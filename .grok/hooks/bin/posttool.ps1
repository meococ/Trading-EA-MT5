# P2 PostToolUse: MCP audit log + compile-evidence reminder. Never log secrets.
. (Join-Path $PSScriptRoot 'lib.ps1')

function Get-AuditLogPath {
    if ($env:HOOK_AUDIT_PATH) { return $env:HOOK_AUDIT_PATH }
    $repo = Get-TradingRepoRoot
    $dir = Join-Path $repo '.grok\hooks\logs'
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    return (Join-Path $dir 'mcp-audit.jsonl')
}

function Write-McpAudit {
    param($Event, [string]$ToolName)
    if (-not (Test-TextMatch $ToolName '^mt5__')) { return }
    $line = [pscustomobject]@{
        ts         = [DateTime]::UtcNow.ToString('o')
        sessionId  = [string](Get-HookProp $Event @('sessionId', 'session_id'))
        toolName   = $ToolName
        event      = [string](Get-HookProp $Event @('hookEventName', 'hook_event_name'))
    }
    $json = ConvertTo-HookJson $line
    Add-Content -LiteralPath (Get-AuditLogPath) -Value $json -Encoding UTF8
}

function Get-ToolResultText {
    param($Event)
    $result = Get-HookProp $Event @('toolResult', 'tool_result', 'tool_response')
    if ($null -eq $result) { return '' }
    if ($result -is [string]) { return $result }
    try { return (ConvertTo-HookJson $result) } catch { return [string]$result }
}

function Invoke-CompileEvidence {
    param($Event, [string]$Command)
    if (-not (Test-TextMatch $Command 'alpha\.ps1') -or -not (Test-TextMatch $Command '\bcompile\b')) {
        return
    }
    $text = Get-ToolResultText $Event
    $hasCleanLog = Test-TextMatch $text '0 errors,\s*0 warnings'
    $hasEx5 = Test-TextMatch $text '\.ex5'
    if ($hasCleanLog -and $hasEx5) { return }
    $msg = "alpha.ps1 compile returned without both a fresh '0 errors, 0 warnings' log line and EX5 evidence in the tool output. Do not claim the EA compiled. Compile evidence is the log + a new EX5, not the process exit code."
    Write-HookAdditionalContext -EventName 'PostToolUse' -Context $msg
}

try {
    $event = Read-HookEvent
    if ($null -eq $event) { exit 0 }
    $toolName = Get-EffectiveMcpToolName $event
    $command = Get-HookCommandText $event
    Write-McpAudit $event $toolName
    Invoke-CompileEvidence $event $command
    exit 0
}
catch {
    [Console]::Error.WriteLine("posttool hook error: $($_.Exception.Message)")
    exit 0
}
