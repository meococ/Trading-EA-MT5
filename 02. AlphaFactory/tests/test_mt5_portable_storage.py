from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


ALPHA_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ALPHA_ROOT.parent
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")
CONTRACT = ALPHA_ROOT / "tools" / "mt5_storage_contract.ps1"


def run_contract(command: str) -> subprocess.CompletedProcess[str]:
    assert POWERSHELL, "PowerShell is required"
    return subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            f". '{CONTRACT}'; {command}",
        ],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def test_portable_launch_and_compile_arguments_are_explicit() -> None:
    launch = run_contract(
        "@(Get-Mt5LaunchArguments -ConfigPath 'D:\\run\\config.ini' "
        "-PortableMode $true) | ConvertTo-Json -Compress"
    )
    assert launch.returncode == 0, launch.stdout + launch.stderr
    assert json.loads(launch.stdout) == ["/portable", '/config:"D:\\run\\config.ini"']

    compile_result = run_contract(
        "@(Get-MetaEditorCompileArguments -SourcePath 'D:\\ea\\EA.mq5' "
        "-LogPath 'D:\\ea\\EA.log' -PortableMode $true) | ConvertTo-Json -Compress"
    )
    assert compile_result.returncode == 0, compile_result.stdout + compile_result.stderr
    assert json.loads(compile_result.stdout) == [
        "/portable",
        '/compile:"D:\\ea\\EA.mq5"',
        '/log:"D:\\ea\\EA.log"',
    ]


def test_d_only_contract_rejects_any_c_storage_root() -> None:
    good = run_contract(
        "Assert-Mt5StorageContract -InstallRoot 'D:\\mt5' -DataRoot 'D:\\mt5' "
        "-CommonFilesRoot 'D:\\mt5\\Common\\Files' -TesterRoot 'D:\\mt5\\Tester' "
        "-PortableMode $true -RequiredDrive 'D:' | ConvertTo-Json -Compress"
    )
    assert good.returncode == 0, good.stdout + good.stderr
    payload = json.loads(good.stdout)
    assert payload["portable_mode"] is True
    assert payload["required_drive"] == "D:"

    bad = run_contract(
        "Assert-Mt5StorageContract -InstallRoot 'D:\\mt5' -DataRoot 'D:\\mt5' "
        "-CommonFilesRoot 'C:\\Users\\ADMIN\\AppData\\Roaming\\MetaQuotes\\Terminal\\Common\\Files' "
        "-TesterRoot 'D:\\mt5\\Tester' -PortableMode $true -RequiredDrive 'D:'"
    )
    assert bad.returncode != 0
    assert "CommonFilesRoot must be on D:" in (bad.stdout + bad.stderr)

    prohibited = run_contract(
        "Assert-Mt5StorageContract -InstallRoot 'D:\\mt5' -DataRoot 'D:\\mt5' "
        "-CommonFilesRoot 'C:\\Users\\ADMIN\\AppData\\Roaming\\MetaQuotes\\Terminal\\Common\\Files' "
        "-TesterRoot 'D:\\mt5\\Tester' -PortableMode $true -RequiredDrive 'D:' "
        "-AllowCommonFiles $false | ConvertTo-Json -Compress"
    )
    assert prohibited.returncode == 0, prohibited.stdout + prohibited.stderr
    assert json.loads(prohibited.stdout)["common_files_allowed"] is False


def test_alpha_uses_storage_contract_for_every_mt5_process_and_manifest() -> None:
    alpha = (ALPHA_ROOT / "alpha.ps1").read_text(encoding="utf-8-sig")
    assert "mt5_storage_contract.ps1" in alpha
    assert alpha.count("Get-Mt5LaunchArguments") >= 2
    assert "Get-MetaEditorCompileArguments" in alpha
    assert "mt5_storage_contract" in alpha
    assert "$MT5CommonFilesRoot" in alpha
    assert "$MT5AllowCommonFiles" in alpha
    assert "$MT5TesterRoot" in alpha
    assert "Get-Mt5SidecarRoots" in alpha
    assert "@($defaultSidecarPatterns) + @($requiredSidecarList)" in alpha
    assert "[string]$manifest.telemetry_tier -cne 'off'" in alpha
    assert "Do-AnalyzeZeroTradeCollection" in alpha
    assert "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE" in alpha


def test_local_template_and_archive_tool_are_portable_aware() -> None:
    template = (ALPHA_ROOT / "alpha.local.ps1.example").read_text(encoding="utf-8-sig")
    archive = (ALPHA_ROOT / "tools" / "archive_backtest_artifacts.ps1").read_text(
        encoding="utf-8-sig"
    )
    for field in (
        "$MT5PortableMode",
        "$MT5CommonFilesRoot",
        "$MT5TesterRoot",
        "$MT5RequiredStorageDrive",
        "$MT5AllowCommonFiles",
    ):
        assert field in template
    assert "[string]$CommonFilesRoot" in archive
    assert "alpha.local.ps1" in archive
