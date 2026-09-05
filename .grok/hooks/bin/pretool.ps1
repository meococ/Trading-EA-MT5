# P0-P2 PreToolUse gate. First explicit deny/ask wins. Fail-open on crash.
. (Join-Path $PSScriptRoot 'lib.ps1')
. (Join-Path $PSScriptRoot 'hygiene.ps1')

$script:SubagentAppendix = @'
[workspace-hook] Two MT5 planes. Research: alpha.ps1 + portable isolate under 02. AlphaFactory/runtime. Observation: MCP / session_trader probe on the Owner GUI, read-only. Never mt5.initialize(path=) targeting D:\Meta 5\terminal64.exe in ad-hoc scripts; never spawn terminal64.exe / metaeditor64.exe / metatester64.exe outside alpha.ps1; never call mt5__trade_*. Compile and backtest only via alpha.ps1. Do not create git worktrees unless the Owner approved this turn (token OWNER_APPROVED_WORKTREE). Do not commit or push unless the Owner asked in the current message. Do not kill MT5 processes you did not start.
'@

function Test-AlphaPs1Command {
    param([string]$Command)
    return (Test-TextMatch $Command 'alpha\.ps1')
}

function Test-SessionTraderProbeCommand {
    param([string]$Command)
    return (Test-TextMatch $Command 'session_trader') -and (Test-TextMatch $Command '\bprobe\b')
}

function Test-FactoryIsolateCommand {
    param([string]$Command)
    return (Test-TextMatch $Command '02\. AlphaFactory[\\/]+runtime') -or
           (Test-TextMatch $Command 'mt5-portable') -or
           (Test-TextMatch $Command 'mt5_initialize_kwargs') -or
           (Test-TextMatch $Command 'factory_paths')
}

function Test-RunnerOwnedStopCommand {
    param([string]$Command)
    return (Test-TextMatch $Command 'Stop-RunnerOwnedTerminal') -or
           (Test-TextMatch $Command 'Stop-OrphanPortableTesters')
}

function Test-LaunchesMt5Binary {
    param([string]$Command)
    if ([string]::IsNullOrWhiteSpace($Command)) { return $false }
    if (Test-AlphaPs1Command $Command) { return $false }
    if (Test-SessionTraderProbeCommand $Command) { return $false }
    if (Test-FactoryIsolateCommand $Command) { return $false }
    if (-not (Test-TextMatch $Command '(terminal64|metaeditor64|metatester64)\.exe')) { return $false }
    # --terminal <path> names the Owner GUI for observation; that is not a launch.
    if ((Test-TextMatch $Command '--terminal') -and -not (Test-TextMatch $Command 'Start-Process')) {
        return $false
    }
    return $true
}

function Get-SpawnIsolation {
    param($InputObj)
    $value = Get-HookProp $InputObj @('isolation')
    if ($null -eq $value) { return '' }
    return [string]$value
}

function Get-SpawnPrompt {
    param($InputObj)
    $value = Get-HookProp $InputObj @('prompt')
    if ($null -eq $value) { return '' }
    return [string]$value
}

function Test-OwnerApprovedWorktree {
    param([string]$Prompt)
    return $Prompt -match 'OWNER_APPROVED_WORKTREE'
}

function Invoke-McpTradeGate {
    param([string]$ToolName)
    if (Test-TextMatch $ToolName '^mt5__trade_') {
        Write-HookDeny 'Blocked mt5__trade_* . MCP orders bypass session_trader / Risk Gateway. Route execution through the Risk Gateway. AutoTrading OFF does not cover this path (mcp_trade_allowed is independent).'
    }
}

function Invoke-TesterGate {
    param([string]$ToolName)
    if (Test-TextMatch $ToolName 'mt5__tester_run_backtest') {
        Write-HookAsk 'MCP tester_run_backtest runs on the Owner GUI with that broker history. Observation only — not a decision number. Economic evidence must come from alpha.ps1 backtest against the portable isolate. Confirm if this is exploration-only.'
    }
}

function Invoke-WorktreeGate {
    param($Event, [string]$ToolName, [string]$Command, $InputObj)
    $spawn = Test-TextMatch $ToolName 'spawn_subagent|^Task$'
    if ($spawn) {
        $isolation = Get-SpawnIsolation $InputObj
        $prompt = Get-SpawnPrompt $InputObj
        if ($isolation -eq 'worktree' -and -not (Test-OwnerApprovedWorktree $prompt)) {
            Write-HookDeny 'Blocked spawn_subagent isolation=worktree. Do not create a worktree unless the Owner asked this turn. If he did, put OWNER_APPROVED_WORKTREE in the subagent prompt and retry.'
        }
    }
    if (Test-TextMatch $Command 'git\s+worktree\s+add') {
        if (-not (Test-TextMatch $Command 'OWNER_APPROVED_WORKTREE')) {
            Write-HookDeny 'Blocked git worktree add. Owner rule: do not create a worktree unless he asked in this message. Wait for a yes.'
        }
    }
}

function Invoke-ShellProcessGate {
    param([string]$Command)
    if ([string]::IsNullOrWhiteSpace($Command)) { return }

    if (Test-LaunchesMt5Binary $Command) {
        Write-HookDeny 'Blocked launching terminal64.exe / metaeditor64.exe / metatester64.exe outside alpha.ps1. 2026-08-31: path= / a bare terminal starts an empty process. Allowed: alpha.ps1 compile (MetaEditor -Wait) and alpha.ps1 backtest (isolate /config: + Register-RunnerOwnedTerminal). Attach to a terminal that is already running; do not start one.'
    }

    $killsMt5 = (Test-TextMatch $Command '(taskkill|Stop-Process).*(terminal64|metaeditor64|metatester64)') -or
                (Test-TextMatch $Command '(terminal64|metaeditor64|metatester64).*(taskkill|Stop-Process)')
    if ($killsMt5 -and -not (Test-RunnerOwnedStopCommand $Command) -and -not (Test-AlphaPs1Command $Command)) {
        Write-HookDeny 'Blocked killing an MT5 process. alpha.ps1 only stops terminals it started (Stop-RunnerOwnedTerminal). Ask the Owner before touching the GUI terminal.'
    }

    $bareInit = Test-TextMatch $Command 'mt5\.initialize\(\s*\)'
    if ($bareInit -and -not (Test-SessionTraderProbeCommand $Command) -and -not (Test-FactoryIsolateCommand $Command)) {
        Write-HookDeny 'Blocked bare mt5.initialize(). Research attach must use mt5_initialize_kwargs() from 02. AlphaFactory/tools/factory_paths.py. Observation uses session_trader probe --terminal <Owner GUI>.'
    }

    $ownerPathInit = Test-TextMatch $Command 'mt5\.initialize\([^)]*path\s*='
    if ($ownerPathInit -and (Test-TextMatch $Command 'D:\\Meta 5\\terminal64\.exe') -and -not (Test-SessionTraderProbeCommand $Command) -and -not (Test-AlphaPs1Command $Command)) {
        Write-HookDeny 'Blocked mt5.initialize(path=) targeting the Owner GUI. path= launches that terminal if it is not running (2026-08-31 empty isolate). Observation: python -m session_trader probe --terminal "D:\Meta 5\terminal64.exe". Research: mt5_initialize_kwargs() onto the portable isolate.'
    }
}

function Invoke-GitGate {
    param([string]$Command)
    if ([string]::IsNullOrWhiteSpace($Command)) { return }

    if (Test-TextMatch $Command 'git(?:\s+-C\s+\S+)?\s+add\s+(?:-A|--all|\.(?:\s|$)|(?:--\s+)?\*)') {
        Write-HookDeny 'Blocked git add -A / git add . / git add *. Stage named paths only. This repo has secrets, parquet, and machine-local files that a blanket add will pick up.'
    }

    if (Test-TextMatch $Command 'git_sync\.ps1.*\b(push|backup)\b') {
        Write-HookAsk 'git_sync.ps1 push/backup stages with git add -A. Owner must confirm commit/push in this message. Prefer named git add of the files he asked for.'
    }

    if (Test-TextMatch $Command 'git(?:\s+-C\s+\S+)?\s+push') {
        Write-HookAsk 'git push requires the Owner to ask in the current message. Confirm before sending.'
    }

    if (Test-TextMatch $Command 'git(?:\s+-C\s+\S+)?\s+commit') {
        Write-HookAsk 'git commit requires the Owner to ask in the current message. Confirm before creating a commit.'
    }
}

function Invoke-SecretWriteGate {
    param([string]$FilePath)
    if ([string]::IsNullOrWhiteSpace($FilePath)) { return }
    $norm = $FilePath.Replace('\', '/')
    if (Test-ForbiddenRelativePath $norm) {
        Write-HookDeny "Blocked write to protected path: $FilePath. Secrets, MCP config, parquet, and alpha.local.ps1 stay untracked."
    }
}

function Invoke-SubagentRewrite {
    param($Event, [string]$ToolName, $InputObj)
    if (-not (Test-TextMatch $ToolName 'spawn_subagent|^Task$')) { return }
    if ($null -eq $InputObj) { return }
    $prompt = Get-SpawnPrompt $InputObj
    if ($prompt -match '\[workspace-hook\]') { return }
    $prop = $InputObj.PSObject.Properties['prompt']
    if ($null -eq $prop) { return }
    $InputObj.prompt = $prompt.TrimEnd() + "`n`n" + $script:SubagentAppendix.Trim()
    Write-HookUpdatedInput $InputObj
}

try {
    $event = Read-HookEvent
    if ($null -eq $event) { exit 0 }

    $toolName = Get-HookToolName $event
    $mcpName = Get-EffectiveMcpToolName $event
    $inputObj = Get-HookToolInput $event
    $command = Get-HookCommandText $event
    $filePath = Get-HookFilePath $event

    Invoke-McpTradeGate $mcpName
    Invoke-TesterGate $mcpName
    Invoke-WorktreeGate $event $toolName $command $inputObj
    Invoke-ShellProcessGate $command
    Invoke-GitGate $command
    Invoke-SecretWriteGate $filePath
    Invoke-SubagentRewrite $event $toolName $inputObj
    exit 0
}
catch {
    [Console]::Error.WriteLine("pretool hook error: $($_.Exception.Message)")
    exit 0
}
