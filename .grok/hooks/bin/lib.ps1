# Shared helpers for Grok project hooks. Windows PowerShell 5.1 compatible.
# Do not emit secrets, tokens, or passwords to stdout/stderr/status files.

Set-StrictMode -Version 1
$ErrorActionPreference = 'Stop'

function Get-TradingRepoRoot {
    $candidates = New-Object System.Collections.Generic.List[string]
    if ($env:GROK_WORKSPACE_ROOT) { [void]$candidates.Add($env:GROK_WORKSPACE_ROOT) }
    if ($env:CLAUDE_PROJECT_DIR) { [void]$candidates.Add($env:CLAUDE_PROJECT_DIR) }
    if ($PSScriptRoot) {
        $fromHook = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
        [void]$candidates.Add($fromHook)
    }
    foreach ($c in $candidates) {
        if ([string]::IsNullOrWhiteSpace($c)) { continue }
        if (Test-Path -LiteralPath (Join-Path $c '01. GOAL\GOAL.md')) {
            return [System.IO.Path]::GetFullPath($c)
        }
        $nested = Join-Path $c 'Trading-EA-MT5'
        if (Test-Path -LiteralPath (Join-Path $nested '01. GOAL\GOAL.md')) {
            return [System.IO.Path]::GetFullPath($nested)
        }
    }
    throw 'Trading-EA-MT5 repo root not found from hook context'
}

function Read-HookEvent {
    $utf8 = New-Object System.Text.UTF8Encoding $false
    $stdin = [Console]::OpenStandardInput()
    $reader = New-Object System.IO.StreamReader($stdin, $utf8, $false, 4096, $true)
    $raw = $reader.ReadToEnd()
    if ([string]::IsNullOrWhiteSpace($raw)) { return $null }
    return $raw | ConvertFrom-Json
}

function Get-HookProp {
    param($Object, [string[]]$Names)
    if ($null -eq $Object) { return $null }
    foreach ($name in $Names) {
        $prop = $Object.PSObject.Properties[$name]
        if ($null -ne $prop -and $null -ne $prop.Value) { return $prop.Value }
    }
    return $null
}

function Get-HookToolName {
    param($Event)
    $name = [string](Get-HookProp $Event @('toolName', 'tool_name'))
    if ([string]::IsNullOrWhiteSpace($name)) { return '' }
    return $name
}

function Get-HookToolInput {
    param($Event)
    return (Get-HookProp $Event @('toolInput', 'tool_input'))
}

function Get-HookCommandText {
    param($Event)
    $inputObj = Get-HookToolInput $Event
    $cmd = Get-HookProp $inputObj @('command', 'Command')
    if ($null -eq $cmd) { return '' }
    return [string]$cmd
}

function Get-HookFilePath {
    param($Event)
    $inputObj = Get-HookToolInput $Event
    $path = Get-HookProp $inputObj @('file_path', 'filePath', 'path', 'target_file')
    if ($null -eq $path) { return '' }
    return [string]$path
}

function Get-EffectiveMcpToolName {
    param($Event)
    $toolName = Get-HookToolName $Event
    if ($toolName -eq 'use_tool') {
        $inner = Get-HookProp (Get-HookToolInput $Event) @('tool_name', 'toolName')
        if ($inner) { return [string]$inner }
    }
    return $toolName
}

function ConvertTo-HookJson {
    param($Object)
    return ($Object | ConvertTo-Json -Compress -Depth 30)
}

function Write-HookStdout {
    param([string]$Json)
    $utf8 = New-Object System.Text.UTF8Encoding $false
    [Console]::OutputEncoding = $utf8
    [Console]::Out.WriteLine($Json)
}

function Write-HookDeny {
    param([string]$Reason)
    $payload = [pscustomobject]@{
        decision = 'deny'
        reason   = $Reason
    }
    Write-HookStdout (ConvertTo-HookJson $payload)
    exit 2
}

function Write-HookAsk {
    param([string]$Reason)
    $payload = [pscustomobject]@{
        decision = 'ask'
        reason   = $Reason
    }
    Write-HookStdout (ConvertTo-HookJson $payload)
    exit 0
}

function Write-HookUpdatedInput {
    param($UpdatedInput, [string]$Context = '')
    $specific = [ordered]@{
        hookEventName = 'PreToolUse'
        updatedInput  = $UpdatedInput
    }
    if (-not [string]::IsNullOrWhiteSpace($Context)) {
        $specific['additionalContext'] = $Context
    }
    $payload = [pscustomobject]@{
        hookSpecificOutput = [pscustomobject]$specific
    }
    Write-HookStdout (ConvertTo-HookJson $payload)
    exit 0
}

function Write-HookAdditionalContext {
    param([string]$EventName, [string]$Context)
    $payload = [pscustomobject]@{
        hookSpecificOutput = [pscustomobject]@{
            hookEventName     = $EventName
            additionalContext = $Context
        }
    }
    Write-HookStdout (ConvertTo-HookJson $payload)
    exit 0
}

function Test-TextMatch {
    param([string]$Text, [string]$Pattern)
    if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
    return [bool][regex]::IsMatch($Text, $Pattern, 'IgnoreCase, CultureInvariant')
}
