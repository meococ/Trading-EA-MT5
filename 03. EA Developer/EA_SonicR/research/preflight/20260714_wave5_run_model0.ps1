# Run Discovery Wave5 Model 0 trio (contracts frozen).
$ErrorActionPreference = "Stop"
$Root = "d:\Trading EA MT5"
$Alpha = Join-Path $Root "02. AlphaFactory\alpha.ps1"
$Contracts = Get-Content (Join-Path $Root "03. EA Developer\EA_SonicR\research\preflight\20260714_DISCOVERY_WAVE5_CONTRACTS.json") -Raw | ConvertFrom-Json
$LogDir = Join-Path $Root "03. EA Developer\EA_SonicR\research\preflight"
$Results = @()

foreach ($c in $Contracts) {
    $hid = $c.hypothesis_id
    $ea = $c.ea_name
    $period = $c.period
    $sym = $c.symbol
    $dep = [int]$c.deposit
    $receipt = $c.receipt
    $sha = $c.receipt_sha256
    Write-Host "==== MODEL0 $hid / $ea / $sym $period ===="
    $log = Join-Path $LogDir ("20260714_WAVE5_MODEL0_{0}.log" -f ($hid -replace '-','_'))
    try {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $Alpha `
            backtest $ea `
            -Symbol $sym `
            -Period $period `
            -From "2021.01.01" `
            -To "2025.12.31" `
            -Model 0 `
            -Deposit $dep `
            -Leverage 100 `
            -HypothesisId $hid `
            -RunRole control `
            -ContractReceipt $receipt `
            -ContractReceiptSha256 $sha `
            -TimeoutSec 2400 `
            *>&1 | Tee-Object -FilePath $log
        $Results += [pscustomobject]@{ hypothesis_id = $hid; ea = $ea; symbol = $sym; status = "EXIT_$LASTEXITCODE"; log = $log }
    }
    catch {
        $_ | Out-File -FilePath $log -Append
        $Results += [pscustomobject]@{ hypothesis_id = $hid; ea = $ea; symbol = $sym; status = "THROW:$($_.Exception.Message)"; log = $log }
        Write-Host "FAIL $hid : $($_.Exception.Message)"
    }
}

$Results | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $LogDir "20260714_WAVE5_MODEL0_BATCH_STATUS.json")
$Results | Format-Table -AutoSize
