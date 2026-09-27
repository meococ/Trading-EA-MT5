<#
.SYNOPSIS
    Inventory MT5 data available in the VM isolate (MetaQuotes-Demo plane).
.DESCRIPTION
    Wraps vm_data_inventory.py: attaches MetaTrader5 to the portable isolate
    (tools.factory_paths contract), probes EURUSD, XAUUSD + 10-symbol basket,
    writes inventory.csv + inventory.json under OutDir.
    Exit code: 0 = PASS (all symbols), 1 = WARN (some missing), 2 = FAIL.
#>
[CmdletBinding()]
param(
    [string]$OutDir = '',
    [switch]$Json
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Off

$vmToolsRoot = $PSScriptRoot
$toolsRoot = Split-Path -Parent $vmToolsRoot
$alphaRoot = Split-Path -Parent $toolsRoot
if ([string]::IsNullOrWhiteSpace($OutDir)) {
    $OutDir = Join-Path $alphaRoot 'runtime\vm_inventory'
}

$python = 'C:\Python312\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    $python = 'python'
}

$out = & $python (Join-Path $vmToolsRoot 'vm_data_inventory.py') --out-dir $OutDir 2>&1 | Out-String
$code = $LASTEXITCODE

if ($Json) {
    $out.Trim()
} else {
    Write-Host "inventory exit=$code out_dir=$OutDir"
    try {
        $payload = $out.Trim() | ConvertFrom-Json
        if ($payload.attached) {
            Write-Host ("plane=" + $payload.plane + " server=" + $payload.server + " build=" + $payload.terminal_build + " disk_free_gb=" + $payload.vm_disk_free_gb)
            foreach ($s in $payload.symbols) {
                Write-Host ("  " + $s.symbol + " avail=" + $s.available + " m1=" + $s.m1_first + ".." + $s.m1_last + " tick_years=" + ($s.tick_years_with_data -join ',') + " bytes=" + $s.disk_bytes)
            }
        } else {
            Write-Host ("attach failed: " + $payload.attach_error)
        }
    } catch {
        Write-Host $out
    }
}
exit $code
