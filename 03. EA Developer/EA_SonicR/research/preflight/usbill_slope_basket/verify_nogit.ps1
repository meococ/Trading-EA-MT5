$ErrorActionPreference = "Stop"
$AdvisorsRoot = "d:\Trading EA MT5"

function Get-TextSha256([string]$Text) {
  $sha = [System.Security.Cryptography.SHA256]::Create()
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
  -join ($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString("X2") })
}

function Get-NoGitProvenanceSnapshot {
  $agentsPath = Join-Path $AdvisorsRoot "AGENTS.md"
  $goalPath = Join-Path $AdvisorsRoot "01. GOAL\GOAL.md"
  $provenancePaths = @($agentsPath, $goalPath)
  $activeEa = Join-Path $AdvisorsRoot "03. EA Developer\EA_M15VolExpansion\EA_M15VolExpansion.mq5"
  if (Test-Path -LiteralPath $activeEa -PathType Leaf) { $provenancePaths += $activeEa }
  $records = New-Object System.Collections.Generic.List[string]
  foreach ($path in $provenancePaths) {
    $full = [System.IO.Path]::GetFullPath($path)
    $rootFull = [System.IO.Path]::GetFullPath($AdvisorsRoot).TrimEnd('\', '/')
    $rel = if ($full.StartsWith($rootFull, [System.StringComparison]::OrdinalIgnoreCase)) {
      $full.Substring($rootFull.Length).TrimStart('\', '/').Replace('\', '/')
    } else {
      $full.Replace('\', '/')
    }
    $fileHash = (Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash.ToUpperInvariant()
    $records.Add(("{0}`t{1}" -f $rel, $fileHash))
  }
  $payload = [string]::Join("`n", @($records))
  $provSha = (Get-TextSha256 $payload).ToUpperInvariant()
  $commit = "NOGIT-$provSha"
  $statusLines = @("nogit=true", "dirty=true", "provenance_sha256=$provSha")
  return [pscustomobject]@{
    Commit = $commit
    StatusSha256 = Get-TextSha256 ([string]::Join("`n", $statusLines))
    Payload = $payload
  }
}

$s = Get-NoGitProvenanceSnapshot
Write-Output ("ALPHA_COMMIT=" + $s.Commit)
Write-Output ("ALPHA_STATUS=" + $s.StatusSha256)
Write-Output ("PAYLOAD=`n" + $s.Payload)
