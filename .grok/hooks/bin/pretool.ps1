# P0-P2 PreToolUse gate. First explicit deny/ask wins.
# 2026-09-11: a crash now logs to .grok/hooks/logs/ and DENIES — an unparsable
# event must not silently allow the MCP trade surface (trade_send_market_order
# and friends). The earlier "fail open on crash" convention predates that
# discovery.
. (Join-Path $PSScriptRoot 'lib.ps1')
. (Join-Path $PSScriptRoot 'hygiene.ps1')

$script:SubagentAppendix = @'
[workspace-hook] Two MT5 planes. Research: alpha.ps1 + portable isolate under 02. AlphaFactory/runtime. Observation: MCP / session_trader probe on the Owner GUI, read-only. Never mt5.initialize(path=) targeting D:\Meta 5\terminal64.exe in ad-hoc scripts; never spawn terminal64.exe / metaeditor64.exe / metatester64.exe outside alpha.ps1; never call mt5__trade_*. Compile and backtest only via alpha.ps1. Do not create git worktrees unless the Owner approved this turn (token OWNER_APPROVED_WORKTREE). Do not commit or push unless the Owner asked in the current message. Do not kill MT5 processes you did not start.
'@

function Remove-CommandComments {
    # Strip #-to-EOL comments so a mention inside a comment cannot satisfy an
    # allow shape, e.g. "Start-Process terminal64.exe # use alpha.ps1 instead".
    param([string]$Command)
    if ([string]::IsNullOrWhiteSpace($Command)) { return '' }
    $lines = $Command -split "`r?`n"
    $clean = foreach ($line in $lines) {
        $idx = $line.IndexOf('#')
        if ($idx -ge 0) { $line.Substring(0, $idx) } else { $line }
    }
    return ($clean -join "`n")
}

function Split-CommandStatements {
    # Split on statement separators so an allow shape in one statement cannot
    # whitewash a different one ("alpha.ps1 compile; Start-Process …").
    # -IncludePipe also splits on single '|'; omit it where pipe-chained names
    # matter (e.g. "Get-Process terminal64 | Stop-Process" must stay one unit).
    param([string]$Command, [switch]$IncludePipe)
    if ([string]::IsNullOrWhiteSpace($Command)) { return @() }
    if ($IncludePipe) {
        return [regex]::Split($Command, '[;\r\n]+|&&|\|\|?')
    }
    return [regex]::Split($Command, '[;\r\n]+|&&|\|\|')
}

function Test-AlphaPs1Invocation {
    # True only when alpha.ps1 is the script being invoked in this statement —
    # & "…\alpha.ps1", .\alpha.ps1, <path>\alpha.ps1 at statement start, or
    # powershell|pwsh -File <path>\alpha.ps1 / the documented
    # "powershell … alpha.ps1 compile|backtest" runner shape. Merely naming
    # alpha.ps1 (comment stripped already, flag argument, prose) is NOT enough.
    param([string]$Command)
    if ([string]::IsNullOrWhiteSpace($Command)) { return $false }
    # call operator on a quoted or bare path ending in alpha.ps1
    if (Test-TextMatch $Command '&\s*[\x22\x27\x60][^\x22\x27\x60\r\n]*alpha\.ps1') { return $true }
    if (Test-TextMatch $Command '&\s*[^\s\x22\x27\x60|;]*alpha\.ps1') { return $true }
    # statement start: .\alpha.ps1, D:\…\alpha.ps1, "…\alpha.ps1" args
    if (Test-TextMatch $Command '^\s*[\x22\x27\x60][^\x22\x27\x60\r\n]*alpha\.ps1') { return $true }
    if (Test-TextMatch $Command '^\s*[^\s\x22\x27\x60|;]*alpha\.ps1') { return $true }
    # powershell|pwsh … -File <path>\alpha.ps1
    if (Test-TextMatch $Command '\b(?:powershell|pwsh)(?:\.exe)?\b[^;\r\n|]*-File\s*[\x22\x27\x60]?[^\s\x22\x27\x60|;]*alpha\.ps1') { return $true }
    # powershell|pwsh … alpha.ps1 compile|backtest
    if (Test-TextMatch $Command '\b(?:powershell|pwsh)(?:\.exe)?\b[^;\r\n|]*alpha\.ps1\b[^;\r\n|]*\b(?:compile|backtest)\b') { return $true }
    return $false
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

function Test-Mt5LaunchVerb {
    # True when the statement actually starts an MT5 exe: call operator,
    # Start-Process / Invoke-Item / saps / start, cmd /c, or the exe path used
    # as the command token. Naming the exe as an argument is not a launch.
    param([string]$Command)
    if ([string]::IsNullOrWhiteSpace($Command)) { return $false }
    $exe = '(?:terminal64|metaeditor64|metatester64)\s*\.\s*exe'
    if (Test-TextMatch $Command ("(?:Start-Process|Invoke-Item|Invoke-WmiMethod|\bsaps\b|\bii\b|\bstart\b)[^;\r\n]*" + $exe)) { return $true }
    if (Test-TextMatch $Command ($exe + '[^;\r\n]*(?:Start-Process|\bsaps\b)')) { return $true }
    if (Test-TextMatch $Command ('&\s*[\x22\x27\x60][^\x22\x27\x60\r\n]*' + $exe)) { return $true }
    if (Test-TextMatch $Command ('&\s*[^\s\x22\x27\x60|;]*' + $exe)) { return $true }
    if (Test-TextMatch $Command ('^\s*[\x22\x27\x60][^\x22\x27\x60\r\n]*' + $exe)) { return $true }
    if (Test-TextMatch $Command ('^\s*[^\s\x22\x27\x60|;]*' + $exe)) { return $true }
    if (Test-TextMatch $Command ('\bcmd(?:\.exe)?\s+/(?:c|k)\b[^;\r\n]*' + $exe)) { return $true }
    return $false
}

function Test-LaunchesMt5Binary {
    # 2026-09-11 hardening: allow-shapes are evaluated per statement on the
    # comment-stripped command. An MT5 exe mention passes only when that
    # statement itself invokes alpha.ps1 (runner-owned launch) or names the
    # binary for observation without a launch verb (probe --terminal, factory
    # kwargs). Anything unclassifiable is treated as a launch.
    param([string]$Command)
    if ([string]::IsNullOrWhiteSpace($Command)) { return $false }
    $exeName = '(?:terminal64|metaeditor64|metatester64)\s*\.\s*exe'
    if (-not (Test-TextMatch $Command $exeName)) { return $false }
    $stripped = Remove-CommandComments $Command
    foreach ($stmt in (Split-CommandStatements $stripped -IncludePipe)) {
        if (-not (Test-TextMatch $stmt $exeName)) { continue }
        if (Test-AlphaPs1Invocation $stmt) { continue }
        if (Test-Mt5LaunchVerb $stmt) { return $true }
        # --terminal <path> names the Owner GUI for observation; not a launch.
        if (Test-TextMatch $stmt '--terminal') { continue }
        if (Test-SessionTraderProbeCommand $stmt) { continue }
        if (Test-FactoryIsolateCommand $stmt) { continue }
        return $true
    }
    return $false
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
    if ([string]::IsNullOrWhiteSpace($ToolName)) { return }
    # 2026-09-11: cover every naming scheme — bare mt5__ names, the mcp__
    # dispatch prefix, and the six raw trade_* tool names forwarded through
    # use_tool / mcp_call_tool (Get-EffectiveMcpToolName unwraps them before we
    # see the name here). Policy: Linh/OpenClaw holds trade rights
    # (Owner 2026-09-08) but this hook guards the Grok client and cannot verify
    # the caller — the exemption is enforced on the OpenClaw side, not here.
    $isMt5Trade = (Test-TextMatch $ToolName '^(?:mcp__)?mt5__trade_') -or
                  (Test-TextMatch $ToolName '(?:^|__|:|\.)trade_(?:send_market_order|send_pending_order|modify_sl_tp|close_single_position|close_by_position|delete_order)\b')
    if ($isMt5Trade) {
        Write-HookDeny 'Blocked MCP trade execution (mt5__trade_* / mcp__mt5__trade_* / raw trade_* tool names, including use_tool and mcp_call_tool dispatch). MCP orders bypass session_trader / Risk Gateway. Route execution through the Risk Gateway. AutoTrading OFF does not cover this path (mcp_trade_allowed is independent). Linh/OpenClaw exemption is enforced on that client, not here.'
    }
}

function Invoke-TesterGate {
    param([string]$ToolName)
    if (Test-TextMatch $ToolName '(?:mcp__)?mt5__tester_run_backtest') {
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
    # EnterWorktree / git_worktree-style tools create a worktree without a
    # shell command — gate the tool itself (2026-09-11). Approval is the same
    # OWNER_APPROVED_WORKTREE marker, looked up anywhere in the tool input.
    if (Test-TextMatch $ToolName 'EnterWorktree|(^|_)worktree(_|$)') {
        $approved = $false
        if ($null -ne $InputObj) {
            try { $approved = Test-TextMatch (ConvertTo-HookJson $InputObj) 'OWNER_APPROVED_WORKTREE' } catch { $approved = $false }
        }
        if (-not $approved) {
            Write-HookDeny ("Blocked " + $ToolName + ". Do not create a worktree unless the Owner asked this turn. If he did, put OWNER_APPROVED_WORKTREE in the tool input and retry.")
        }
    }
    $stripped = Remove-CommandComments $Command
    if (Test-TextMatch $stripped 'git\s+worktree\s+add') {
        if (-not (Test-TextMatch $stripped 'OWNER_APPROVED_WORKTREE')) {
            Write-HookDeny 'Blocked git worktree add. Owner rule: do not create a worktree unless he asked in this message. Wait for a yes.'
        }
    }
}

function Invoke-ShellProcessGate {
    param([string]$Command)
    if ([string]::IsNullOrWhiteSpace($Command)) { return }

    $stripped = Remove-CommandComments $Command

    # Per statement, but keep '|' intact: "Get-Process terminal64 | Stop-Process"
    # is one pipeline and must still match the kill pattern. Kill check runs
    # first so a taskkill/Stop-Process line gets the kill reason, not launch.
    foreach ($stmt in (Split-CommandStatements $stripped)) {
        $killsMt5 = (Test-TextMatch $stmt '(taskkill|Stop-Process)[^\r\n]*(terminal64|metaeditor64|metatester64)') -or
                    (Test-TextMatch $stmt '(terminal64|metaeditor64|metatester64)[^\r\n]*(taskkill|Stop-Process)')
        if ($killsMt5 -and -not (Test-RunnerOwnedStopCommand $stmt) -and -not (Test-AlphaPs1Invocation $stmt)) {
            Write-HookDeny 'Blocked killing an MT5 process. alpha.ps1 only stops terminals it started (Stop-RunnerOwnedTerminal). Ask the Owner before touching the GUI terminal.'
        }
    }

    # Bare no-arg attach: initialize() with no arguments. Credential-bearing
    # initialize(login=..., server=..., password=...) attaching to a running
    # terminal stays allowed (workspace doctrine). An mt5 hint must be present
    # so unrelated initialize() functions are not flagged.
    $mt5Anywhere = Test-TextMatch $stripped 'MetaTrader5|\bmt5\b'
    $bareInit = (Test-TextMatch $stripped '\binitialize\s*\(\s*\)') -and $mt5Anywhere
    if ($bareInit -and -not (Test-SessionTraderProbeCommand $stripped) -and -not (Test-FactoryIsolateCommand $stripped)) {
        Write-HookDeny 'Blocked bare mt5.initialize(). Research attach must use mt5_initialize_kwargs() from 02. AlphaFactory/tools/factory_paths.py. Observation uses session_trader probe --terminal <Owner GUI>. initialize(login=..., server=..., password=...) attaching to a running terminal stays allowed.'
    }

    # path= is allowed only when the statement clearly resolves under
    # 02. AlphaFactory/runtime (or mt5-portable) or goes through
    # mt5_initialize_kwargs()/factory_paths. Any other path= — an Owner GUI
    # literal, another machine path, or a variable we cannot verify — is
    # denied. Quoting/escaping no longer decides this; the target does.
    # Checked before the launch gate so ad-hoc path= gets this specific reason.
    # 2026-09-11.
    foreach ($stmt in (Split-CommandStatements $stripped)) {
        if (-not (Test-TextMatch $stmt '\binitialize\s*\([^)]*\bpath\s*=')) { continue }
        $dotted = Test-TextMatch $stmt '(?:mt5|MetaTrader5)\s*\.\s*initialize'
        if (-not $dotted -and -not $mt5Anywhere) { continue }
        if (Test-FactoryIsolateCommand $stmt) { continue }
        $pm = [regex]::Match($stmt, '\bpath\s*=\s*[urbfURBF]{0,2}[\x22\x27\x60](?<v>[^\x22\x27\x60]*)', 'IgnoreCase')
        if (-not $pm.Success) {
            $pm = [regex]::Match($stmt, '\bpath\s*=\s*(?<v>[^\s,)\x22\x27\x60]+)', 'IgnoreCase')
        }
        $pv = ''
        if ($pm.Success) { $pv = $pm.Groups['v'].Value }
        # path=<variable>: allow only when the command itself establishes the
        # runtime isolate; a concrete non-runtime literal is always denied.
        if ((Test-TextMatch $pv '^\w+$') -and (Test-FactoryIsolateCommand $stripped)) { continue }
        Write-HookDeny 'Blocked mt5.initialize(path=) that does not resolve under 02. AlphaFactory/runtime. path= launches that terminal when it is not running (2026-08-31 empty isolate). Research: mt5_initialize_kwargs() onto the portable isolate. Observation: python -m session_trader probe --terminal <Owner GUI path>.'
    }

    if (Test-LaunchesMt5Binary $Command) {
        Write-HookDeny 'Blocked launching terminal64.exe / metaeditor64.exe / metatester64.exe outside an alpha.ps1 invocation. 2026-08-31: path= / a bare terminal starts an empty process. 2026-09-11: naming alpha.ps1, session_trader, or runtime in a comment or argument is not an invocation. Allowed: alpha.ps1 compile (MetaEditor -Wait) and alpha.ps1 backtest (isolate /config: + Register-RunnerOwnedTerminal). Attach to a terminal that is already running; do not start one.'
    }
}

function Invoke-GitGate {
    param([string]$Command)
    if ([string]::IsNullOrWhiteSpace($Command)) { return }

    # git -C <path> may be quoted and contain spaces — allow a quoted segment.
    $gitC = '(?:\s+-C\s+(?:[\x22\x27\x60][^\x22\x27\x60]*[\x22\x27\x60]|\S+))?'
    $blanketAdd = Test-TextMatch $Command ("git" + $gitC + '\s+add\s+(?:-A\b|--all\b|-u\b|--update\b|--intent-to-add\b|\.(?:\s|$)|(?:--\s+)?\*)')
    # -N is case-sensitive: lowercase -n is a harmless dry-run, -N stages
    # intent-to-add entries. Check it without IgnoreCase.
    $intentAdd = [regex]::IsMatch($Command, ("git" + $gitC + '\s+add\s+(?:-N\b|--intent-to-add\b)'))
    if ($blanketAdd -or $intentAdd) {
        Write-HookDeny 'Blocked git add -A / . / * / -u / --update / -N / --intent-to-add. Stage named paths only. This repo has secrets, parquet, and machine-local files that a blanket add will pick up.'
    }

    # --no-verify (-n, or n inside a flag cluster like -an) skips pre-commit —
    # the only staged-secret scan — so it is a deny, not an ask.
    if (Test-TextMatch $Command ("git" + $gitC + '\s+commit\b[^;\r\n|]*(?:--no-verify\b|\s-[a-zA-Z]*n[a-zA-Z]*\b)')) {
        Write-HookDeny 'Blocked git commit --no-verify / -n. The pre-commit hygiene scan is the only staged-secret check; bypassing it is not allowed.'
    }

    # Overriding core.hooksPath disables the same gate.
    if (Test-TextMatch $Command 'git\b[^;\r\n|]*(?:-c\s+[^\s]*core\.hooksPath|core\.hooksPath\s*=)') {
        Write-HookDeny 'Blocked overriding core.hooksPath — that disables the pre-commit hygiene gate.'
    }

    if (Test-TextMatch $Command 'git_sync\.ps1.*\b(push|backup)\b') {
        Write-HookAsk 'git_sync.ps1 push/backup stages with git add -A. Owner must confirm commit/push in this message. Prefer named git add of the files he asked for.'
    }

    if (Test-TextMatch $Command ("git" + $gitC + '\s+push')) {
        Write-HookAsk 'git push requires the Owner to ask in the current message. Confirm before sending.'
    }

    if (Test-TextMatch $Command ("git" + $gitC + '\s+commit')) {
        Write-HookAsk 'git commit requires the Owner to ask in the current message. Confirm before creating a commit.'
    }
}

function Invoke-SecretWriteGate {
    param([string]$FilePath, [string]$Command = '')
    if (-not [string]::IsNullOrWhiteSpace($FilePath)) {
        $norm = $FilePath.Replace('\', '/')
        if (Test-ForbiddenRelativePath $norm) {
            Write-HookDeny "Blocked write to protected path: $FilePath. Secrets, MCP config, parquet, and alpha.local.ps1 stay untracked."
        }
    }
    if ([string]::IsNullOrWhiteSpace($Command)) { return }
    # 2026-09-11: shell writes count too. Any statement carrying a write
    # operator (>, >>, Out-File, *-Content, Copy/Move/New-Item, tee, robocopy,
    # certutil, …) has every path-like token checked against the same
    # forbidden-name list used for file_path inputs.
    $stripped = Remove-CommandComments $Command
    $writeOp = '>>?|\b(?:Out-File|Tee-Object|tee|Set-Content|Add-Content|sc|ac|New-Item|ni|Copy-Item|Move-Item|Rename-Item|cp|mv|copy|move|xcopy|robocopy|mkdir|md|Set-ItemProperty|New-ItemProperty|fsutil|certutil)\b'
    foreach ($stmt in (Split-CommandStatements $stripped -IncludePipe)) {
        if (-not (Test-TextMatch $stmt $writeOp)) { continue }
        foreach ($m in [regex]::Matches($stmt, '[\x22\x27\x60]([^\x22\x27\x60\r\n]+)[\x22\x27\x60]|[^\s\x22\x27\x60|;&(){}<>]+')) {
            $tok = $m.Value.Trim()
            if ([string]::IsNullOrWhiteSpace($tok)) { continue }
            if (Test-ForbiddenRelativePath $tok) {
                Write-HookDeny ("Blocked shell write touching protected path: " + $tok + ". Secrets, MCP config, parquet, keys, and alpha.local.ps1 stay untracked.")
            }
        }
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
    Invoke-SecretWriteGate -FilePath $filePath -Command $command
    Invoke-SubagentRewrite $event $toolName $inputObj
    exit 0
}
catch {
    # 2026-09-11 decision: log the crash, then DENY. The older fail-open note
    # predates the trade-surface discovery — an unparsable event must not
    # silently allow trade_send_market_order & friends.
    $errMsg = 'unknown'
    try { $errMsg = [string]$_.Exception.Message } catch { }
    try {
        $hookDir = $PSScriptRoot
        if ([string]::IsNullOrWhiteSpace($hookDir)) {
            try { $hookDir = Join-Path (Get-TradingRepoRoot) '.grok\hooks\bin' } catch { $hookDir = '' }
        }
        if (-not [string]::IsNullOrWhiteSpace($hookDir)) {
            $logDir = [System.IO.Path]::GetFullPath((Join-Path $hookDir '..\logs'))
            if (-not (Test-Path -LiteralPath $logDir)) {
                New-Item -ItemType Directory -Path $logDir -Force | Out-Null
            }
            $tn = ''; $mn = ''
            try { $tn = [string]$toolName } catch { }
            try { $mn = [string]$mcpName } catch { }
            $entry = [pscustomobject]@{
                ts    = [DateTime]::UtcNow.ToString('o')
                hook  = 'pretool'
                error = $errMsg
                tool  = $tn
                mcp   = $mn
            }
            $line = ($entry | ConvertTo-Json -Compress -Depth 5)
            Add-Content -LiteralPath (Join-Path $logDir 'pretool-errors.jsonl') -Value $line -Encoding UTF8
        }
    } catch { }
    try { [Console]::Error.WriteLine("pretool hook error: $errMsg") } catch { }
    try {
        if (Get-Command Write-HookDeny -ErrorAction SilentlyContinue) {
            Write-HookDeny 'pretool hook crashed — denied conservatively (detail in .grok/hooks/logs/pretool-errors.jsonl).'
        }
    } catch { }
    exit 2
}
