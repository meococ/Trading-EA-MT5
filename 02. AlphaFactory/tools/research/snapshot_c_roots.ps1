# Snapshot the 4 protected C roots via the canonical digest tool.
# The only valid hashing implementation is tools/snapshot_mt5_storage.ps1;
# never reimplement the digest — divergent implementations make before/after
# receipts incomparable.
param([Parameter(Mandatory = $true)][string]$OutputPath)

& (Join-Path $PSScriptRoot '..\snapshot_mt5_storage.ps1') -OutputPath $OutputPath -Roots @(
    'C:\Users\ADMIN\AppData\Roaming\MetaQuotes\Terminal\Common\Files',
    'C:\Users\ADMIN\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\Tester',
    'C:\Users\ADMIN\AppData\Roaming\MetaQuotes\Tester',
    'C:\ProgramData\MetaQuotes\Tester'
)
