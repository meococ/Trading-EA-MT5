# vm_seat_prompt.ps1 — compose an advisory-seat prompt for a Devin cloud child session.
# The seat is read-only: no commit/push, no MT5 process launches, no secret printing.
# Usage:
#   tools\vm\vm_seat_prompt.ps1 -Seat adversarial-auditor -Gate "PR review" `
#       -Artifacts "https://github.com/meococ/Trading-EA-MT5/pull/2" -Branch devin/vm-ops/phase1b
# Prints the prompt to stdout (or -OutFile). Feed it to devin_session_create.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Seat,          # e.g. adversarial-auditor (file basename in .devin/agents)
    [Parameter(Mandatory = $true)][string]$Gate,          # e.g. 'GATE B', 'PR review'
    [string]$Context = '',                                # what to review / task framing
    [string[]]$Artifacts = @(),                           # repo paths or PR URLs to review
    [string]$Branch = '',                                 # branch the child should checkout (default: repo default)
    [string]$OutFile = ''
)
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$cardPath = Join-Path $repoRoot ".devin\agents\$Seat.md"
if (-not (Test-Path $cardPath)) { Write-Error "seat card not found: $cardPath"; exit 2 }
$card = Get-Content $cardPath -Raw -Encoding UTF8

$artifactLines = if ($Artifacts.Count -gt 0) { ($Artifacts | ForEach-Object { "- $_" }) -join "`n" } else { '- (none given)' }

$prompt = @"
You are an advisory seat on the Trading-EA-MT5 EA campaign — a READ-ONLY reviewer
running as a Devin cloud child session. Repo: meococ/Trading-EA-MT5$(if ($Branch) { ", branch ``$Branch`` (checkout it first)" } else { ' (default branch)' }).

SEAT CARD (verbatim from .devin/agents/$Seat.md):
$card

GATE / OCCASION: $Gate

CONTEXT:
$Context

ARTIFACTS TO REVIEW:
$artifactLines

BAN LIST (hard — violating any of these voids your review):
- NEVER mcp__mt5__trade_* / trade_send_* — observe only.
- NEVER mt5.initialize(path=...) — attach bare only if a terminal is already running.
- Compile/backtest ONLY via ``02. AlphaFactory\alpha.ps1`` — you read logs, you do NOT launch.
- No worktrees, no commits, no pushes, no writes outside your own scratch files.
- No MT5 process launches (no terminal64.exe, no metatester).
- NEVER print secret values to chat/logs/files — including demo credentials.

OUTPUT CONTRACT — reply with exactly this structure:
VERDICT: PASS | FAIL | WARN
then numbered defects, each with file:line or data evidence, and one line
"what would change my verdict". If you cannot find a flaw, list the checks
you ran — silence is not a pass.
"@

if ($OutFile) { $prompt | Set-Content -LiteralPath $OutFile -Encoding UTF8; Write-Host "prompt -> $OutFile" }
else { $prompt }
exit 0
