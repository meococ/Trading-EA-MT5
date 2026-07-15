# Auto-retry Wave4 Model 0 when exclusive tester slot is free (terminal64=0).
# Does NOT kill any process.
$ErrorActionPreference = "Stop"
$Root = "d:\Trading EA MT5"
$LogDir = Join-Path $Root "03. EA Developer\EA_SonicR\research\preflight"
$Out = Join-Path $LogDir "20260714_WAVE4_MODEL0_AUTORETRY_STATUS.json"
$Deadline = (Get-Date).AddMinutes(25)
$Attempts = 0
$Batch = Join-Path $LogDir "20260714_wave4_run_model0.ps1"

while ((Get-Date) -lt $Deadline) {
    $Attempts = $Attempts + 1
    $terms = @(Get-Process -Name "terminal64" -ErrorAction SilentlyContinue)
    if ($terms.Count -eq 0) {
        Write-Host "SLOT_FREE attempt=$Attempts launching Wave4 Model 0 batch"
        & powershell -NoProfile -ExecutionPolicy Bypass -File $Batch
        $payload = [ordered]@{
            schema = "wave4_model0_autoretry.v1"
            outcome = "LAUNCHED"
            attempts = $Attempts
            launched_at = (Get-Date).ToString("s")
            batch_status = (Join-Path $LogDir "20260714_WAVE4_MODEL0_BATCH_STATUS.json")
        }
        ($payload | ConvertTo-Json -Depth 4) | Set-Content -Path $Out -Encoding utf8
        exit 0
    }
    $pids = ($terms | ForEach-Object { $_.Id }) -join ","
    Write-Host ("WAIT attempt={0} terminal64=[{1}]" -f $Attempts, $pids)
    Start-Sleep -Seconds 45
}

$timeoutPayload = [ordered]@{
    schema = "wave4_model0_autoretry.v1"
    outcome = "TIMEOUT_SLOT_STILL_BUSY"
    attempts = $Attempts
    deadline = $Deadline.ToString("s")
    note = "Ceremony frozen+compiled; Model 0 pending exclusive tester. Not a QFSI/login research decision."
}
($timeoutPayload | ConvertTo-Json -Depth 4) | Set-Content -Path $Out -Encoding utf8
Write-Host "TIMEOUT wrote $Out"
exit 2
