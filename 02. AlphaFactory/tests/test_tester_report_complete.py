from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


ALPHA_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ALPHA_ROOT.parent
ALPHA = ALPHA_ROOT / "alpha.ps1"
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")

HELPERS = [
    "Test-PathSafe",
    "Get-FileLengthSafe",
    "Get-Mt5ReportHtml",
    "Get-ReportLabeledValue",
    "Test-Mt5TesterReportComplete",
]


def run_ps(tmp_path: Path, body: str) -> subprocess.CompletedProcess[str]:
    assert POWERSHELL, "PowerShell is required"
    script = tmp_path / "harness.ps1"
    helper_literal = "@(" + ",".join("'" + name + "'" for name in HELPERS) + ")"
    script.write_text(
        rf"""
$ErrorActionPreference = 'Stop'
$alpha = '{str(ALPHA)}'
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($alpha, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count -gt 0) {{ throw ($parseErrors | ForEach-Object {{ $_.Message }} | Out-String) }}
$needed = {helper_literal}
foreach ($name in $needed) {{
    $fn = $ast.Find({{ param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq $name
    }}, $true)
    if ($null -eq $fn) {{ throw "Missing function $name" }}
    Invoke-Expression $fn.Extent.Text
}}
{body}
""",
        encoding="utf-8",
    )
    return subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
        ],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=30,
    )


def pad(html: str) -> str:
    extra = max(0, 1100 - len(html.encode("utf-8")))
    return html + ("<!--" + ("x" * extra) + "-->")


STUB = pad(
    """
<html><body><table>
<tr align="right"><td>Expert:</td><td align="left"><b></b></td></tr>
<tr align="right"><td>Symbol:</td><td align="left"><b></b></td></tr>
<tr align="right"><td>Chu kỳ:</td><td align="left"><b>M0 (1970.01.01 - 1970.01.01)</b></td></tr>
<tr align="right"><td>History Quality:</td><td><b>0%</b></td></tr>
</table></body></html>
"""
)

FINISHED = pad(
    """
<html><body><table>
<tr align="right"><td>Expert:</td><td align="left"><b>EA_GBB_TrendPullback</b></td></tr>
<tr align="right"><td>Symbol:</td><td align="left"><b>XAUUSD</b></td></tr>
<tr align="right"><td>Chu kỳ:</td><td align="left"><b>H1 (2016.01.01 - 2026.08.15)</b></td></tr>
<tr align="right"><td>History Quality:</td><td><b>99%</b></td></tr>
</table></body></html>
"""
)

WRONG_WINDOW = pad(
    """
<html><body><table>
<tr align="right"><td>Expert:</td><td align="left"><b>EA_GBB_TrendPullback</b></td></tr>
<tr align="right"><td>Symbol:</td><td align="left"><b>XAUUSD</b></td></tr>
<tr align="right"><td>Period:</td><td align="left"><b>H1 (2020.01.01 - 2024.12.31)</b></td></tr>
<tr align="right"><td>History Quality:</td><td><b>99%</b></td></tr>
</table></body></html>
"""
)


def _eval(tmp_path: Path, html: str) -> bool:
    report = tmp_path / "report.html"
    report.write_text(html, encoding="utf-8")
    body = f"""
$path = '{report}'
$ready = Test-Mt5TesterReportComplete $path 'EA_GBB_TrendPullback' 'XAUUSD' 'H1' '2016.01.01' '2026.08.15'
Write-Output (@{{ ready = [bool]$ready }} | ConvertTo-Json -Compress)
"""
    result = run_ps(tmp_path, body)
    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    return bool(payload["ready"])


def test_startup_stub_is_not_complete(tmp_path: Path) -> None:
    assert _eval(tmp_path, STUB) is False


def test_finished_identity_is_complete(tmp_path: Path) -> None:
    assert _eval(tmp_path, FINISHED) is True


def test_wrong_window_is_not_complete(tmp_path: Path) -> None:
    assert _eval(tmp_path, WRONG_WINDOW) is False


def test_utf16_le_finished_report_is_complete(tmp_path: Path) -> None:
    report = tmp_path / "report.html"
    report.write_bytes(b"\xff\xfe" + FINISHED.encode("utf-16-le"))
    body = f"""
$path = '{report}'
$ready = Test-Mt5TesterReportComplete $path 'EA_GBB_TrendPullback' 'XAUUSD' 'H1' '2016.01.01' '2026.08.15'
Write-Output (@{{ ready = [bool]$ready }} | ConvertTo-Json -Compress)
"""
    result = run_ps(tmp_path, body)
    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert bool(payload["ready"]) is True
