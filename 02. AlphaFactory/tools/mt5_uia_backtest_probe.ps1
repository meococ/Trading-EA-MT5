param(
    [Parameter(Mandatory = $true)]
    [string]$ConfigPath,

    [Parameter(Mandatory = $true)]
    [string]$ReportPath,

    [int]$StartupWaitSec = 8,
    [int]$PostCancelWaitSec = 2,
    [int]$PollSeconds = 60
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class MT5Native
{
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool SetCursorPos(int X, int Y);

    [DllImport("user32.dll")]
    public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, UIntPtr dwExtraInfo);

    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    public static extern IntPtr SendMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);

    public const uint MOUSEEVENTF_LEFTDOWN = 0x0002;
    public const uint MOUSEEVENTF_LEFTUP   = 0x0004;
    public const uint BM_CLICK             = 0x00F5;
}
'@

function Find-ElementByName {
    param(
        [System.Windows.Automation.AutomationElement]$Root,
        [string]$Name
    )

    if ($null -eq $Root) { return $null }
    $cond = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::NameProperty,
        $Name
    )
    return $Root.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $cond)
}

function Click-ElementByName {
    param(
        [System.Windows.Automation.AutomationElement]$Root,
        [string]$Name
    )

    $el = Find-ElementByName -Root $Root -Name $Name
    if ($null -eq $el) {
        Write-Output "MISS:$Name"
        return $false
    }

    $nativeHandle = $el.Current.NativeWindowHandle
    if ($nativeHandle -gt 0) {
        try {
            [MT5Native]::SendMessage([IntPtr]$nativeHandle, [MT5Native]::BM_CLICK, [IntPtr]::Zero, [IntPtr]::Zero) | Out-Null
            Write-Output "BM_CLICK:$Name@$nativeHandle"
            return $true
        }
        catch {}
    }

    $rect = $el.Current.BoundingRectangle
    $x = [int](($rect.Left + $rect.Right) / 2)
    $y = [int](($rect.Top + $rect.Bottom) / 2)

    [MT5Native]::SetCursorPos($x, $y) | Out-Null
    Start-Sleep -Milliseconds 150
    [MT5Native]::mouse_event([MT5Native]::MOUSEEVENTF_LEFTDOWN, 0, 0, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 80
    [MT5Native]::mouse_event([MT5Native]::MOUSEEVENTF_LEFTUP, 0, 0, 0, [UIntPtr]::Zero)

    Write-Output "CLICK:$Name@$x,$y"
    return $true
}

if (-not (Test-Path $ConfigPath)) {
    throw "Config not found: $ConfigPath"
}

# Factory isolate only. Was "C:\Program Files\MetaTrader 5\terminal64.exe",
# a path absent on this machine.
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$localPin = Join-Path $repoRoot "02. AlphaFactory\alpha.local.ps1"
if (-not (Test-Path -LiteralPath $localPin -PathType Leaf)) {
    throw "Machine pin missing: $localPin. Run tools\init_machine_paths.ps1."
}
. $localPin
$factoryRuntime = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "02. AlphaFactory\runtime"))
$factoryInstall = [System.IO.Path]::GetFullPath($MT5InstallRoot)
if (-not $factoryInstall.StartsWith($factoryRuntime, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing '$factoryInstall': the probe target must sit under '$factoryRuntime'."
}
$terminalExe = Join-Path $factoryInstall "terminal64.exe"
if (-not (Test-Path -LiteralPath $terminalExe -PathType Leaf)) {
    throw "Factory terminal missing: $terminalExe"
}

# Only stop terminals launched from the factory isolate. The previous
# `Get-Process terminal64 | Stop-Process -Force` killed EVERY terminal64,
# including the Owner GUI being traded from.
$existing = @(Get-CimInstance Win32_Process -Filter "Name='terminal64.exe'" -ErrorAction SilentlyContinue |
    Where-Object {
        $_.ExecutablePath -and
        ([System.IO.Path]::GetFullPath($_.ExecutablePath)).Equals($terminalExe, [System.StringComparison]::OrdinalIgnoreCase)
    })
if ($existing.Count -gt 0) {
    $existing | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 3
}

if (Test-Path $ReportPath) {
    Remove-Item $ReportPath -Force
}

$proc = Start-Process -FilePath $terminalExe -ArgumentList "/config:`"$ConfigPath`"" -PassThru
Start-Sleep -Seconds $StartupWaitSec

$live = Get-Process -Id $proc.Id -ErrorAction SilentlyContinue
if ($null -eq $live) {
    Write-Output "STATE:PROCESS_EXITED_EARLY"
    exit 1
}

[MT5Native]::SetForegroundWindow($live.MainWindowHandle) | Out-Null
Start-Sleep -Milliseconds 500

$root = [System.Windows.Automation.AutomationElement]::FromHandle($live.MainWindowHandle)
if ($null -eq $root) {
    Write-Output "STATE:NO_AUTOMATION_ROOT"
    exit 1
}

$accountDialog = Find-ElementByName -Root $root -Name "Open an Account"
if ($null -ne $accountDialog) {
    $windowPattern = $null
    if ($accountDialog.TryGetCurrentPattern([System.Windows.Automation.WindowPattern]::Pattern, [ref]$windowPattern)) {
        try { $windowPattern.Close() } catch {}
    }
    else {
        try { $accountDialog.SetFocus() } catch {}
        Start-Sleep -Milliseconds 250
        [System.Windows.Forms.SendKeys]::SendWait("{ESC}")
    }
    Start-Sleep -Seconds $PostCancelWaitSec
    $root = [System.Windows.Automation.AutomationElement]::FromHandle($live.MainWindowHandle)
    $accountDialog = Find-ElementByName -Root $root -Name "Open an Account"
    if ($null -ne $accountDialog) {
        Click-ElementByName -Root $root -Name "Cancel"
        Start-Sleep -Seconds 1
    }
    $root = [System.Windows.Automation.AutomationElement]::FromHandle($live.MainWindowHandle)
}

$startElement = $null
for ($j = 0; $j -lt 10; $j++) {
    $root = [System.Windows.Automation.AutomationElement]::FromHandle($live.MainWindowHandle)
    $startElement = Find-ElementByName -Root $root -Name "Start"
    if ($null -ne $startElement -and $startElement.Current.IsEnabled) {
        break
    }
    Start-Sleep -Seconds 1
}

if ($null -eq $startElement) {
    Write-Output "STATE:NO_START_BUTTON"
    exit 1
}

Write-Output ("START_ENABLED:" + $startElement.Current.IsEnabled)

if (-not $startElement.Current.IsEnabled) {
    Write-Output "STATE:START_DISABLED"
    exit 1
}

Click-ElementByName -Root $root -Name "Start"
Start-Sleep -Seconds 1
$root = [System.Windows.Automation.AutomationElement]::FromHandle($live.MainWindowHandle)
$startAfter = Find-ElementByName -Root $root -Name "Start"
$stopAfter  = Find-ElementByName -Root $root -Name "Stop"
if ($null -eq $stopAfter) {
    [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
    Start-Sleep -Milliseconds 500
    [System.Windows.Forms.SendKeys]::SendWait(" ")
    Start-Sleep -Milliseconds 500
    $root = [System.Windows.Automation.AutomationElement]::FromHandle($live.MainWindowHandle)
    $startAfter = Find-ElementByName -Root $root -Name "Start"
    $stopAfter  = Find-ElementByName -Root $root -Name "Stop"
}
Write-Output ("POST_CLICK_START_PRESENT:" + ($null -ne $startAfter))
Write-Output ("POST_CLICK_STOP_PRESENT:" + ($null -ne $stopAfter))

for ($i = 1; $i -le $PollSeconds; $i++) {
    Start-Sleep -Seconds 1

    $alive = Get-Process -Id $proc.Id -ErrorAction SilentlyContinue
    $exists = Test-Path $ReportPath
    $len = if ($exists) { (Get-Item $ReportPath).Length } else { 0 }
    $cpu = if ($alive) { $alive.CPU } else { -1 }

    Write-Output ("T={0} CPU={1} REPORT={2} LEN={3}" -f $i, $cpu, $exists, $len)

    if ($exists -and $len -gt 1000) {
        Write-Output "STATE:REPORT_READY"
        exit 0
    }

    if ($null -eq $alive) {
        Write-Output "STATE:PROCESS_EXITED"
        exit 2
    }
}

Write-Output "STATE:TIMEOUT"
exit 3
