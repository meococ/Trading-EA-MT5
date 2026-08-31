# Snapshot the protected C roots via the canonical digest tool.
# The only valid hashing implementation is tools/snapshot_mt5_storage.ps1;
# never reimplement the digest - divergent implementations make before/after
# receipts incomparable.
# Terminal data roots are discovered from %APPDATA% so the receipt is not
# pinned to one machine's user name or terminal id.
param([Parameter(Mandatory = $true)][string]$OutputPath)

$TerminalRoot = Join-Path $env:APPDATA 'MetaQuotes\Terminal'
$Roots = New-Object System.Collections.Generic.List[string]
$Roots.Add((Join-Path $TerminalRoot 'Common\Files'))
Get-ChildItem -LiteralPath $TerminalRoot -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^[A-F0-9]{32}$' } |
    ForEach-Object { $Roots.Add((Join-Path $_.FullName 'Tester')) }
$Roots.Add((Join-Path $env:APPDATA 'MetaQuotes\Tester'))
$Roots.Add('C:\ProgramData\MetaQuotes\Tester')

& (Join-Path $PSScriptRoot '..\snapshot_mt5_storage.ps1') -OutputPath $OutputPath -Roots @($Roots)
