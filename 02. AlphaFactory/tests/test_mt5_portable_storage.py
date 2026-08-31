from __future__ import annotations

import os
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
    combined = bad.stdout + bad.stderr
    assert ("CommonFilesRoot must stay under DataRoot" in combined) or (
        "CommonFilesRoot must be on D:" in combined
    )

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
    assert "Get-Mt5JournalLogRoots" in alpha
    assert "@($defaultSidecarPatterns) + @($requiredSidecarList)" in alpha
    assert "[string]$manifest.telemetry_tier -cne 'off'" in alpha
    assert "Do-AnalyzeZeroTradeCollection" in alpha
    assert "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE" in alpha


def test_journal_log_roots_are_scoped_to_logs_directories(tmp_path: Path) -> None:
    data = tmp_path / "mt5"
    tester = data / "Tester"
    (data / "logs").mkdir(parents=True)
    (tester / "logs").mkdir(parents=True)
    (tester / "Agent-127.0.0.1-3000" / "logs").mkdir(parents=True)
    (tester / "bases").mkdir()
    (tester / "cache").mkdir()
    (tester / "cache" / "nested.log").write_text("nope", encoding="utf-8")
    (data / "logs" / "20260101.log").write_text("term", encoding="utf-8")
    result = run_contract(
        "@(Get-Mt5JournalLogRoots -DataRoot '{0}' -TesterRoot '{1}') | "
        "ConvertTo-Json -Compress".format(data, tester)
    )
    assert result.returncode == 0, result.stdout + result.stderr
    roots = json.loads(result.stdout)
    if isinstance(roots, str):
        roots = [roots]
    normalized = [str(path).replace("/", "\\").lower() for path in roots]
    assert len(normalized) == 3
    assert all(path.endswith("\\logs") for path in normalized)
    assert all("\\bases" not in path and "\\cache" not in path for path in normalized)
    assert not any(path.endswith("\\tester") for path in normalized)
    assert sum(1 for path in normalized if "\\agent-" in path) == 1


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
    assert "mt5-portable-fivepercent" in template
    assert "mt5-portable-mqdemo" in template
    assert "alpha.ps1 clean" in template
    assert "C:\\Program Files\\MetaTrader 5" in template
    assert "$MT5PortableMode = $true" in template


def test_portable_rejects_appdata_common_even_without_drive_pin() -> None:
    bad = run_contract(
        "Assert-Mt5StorageContract -InstallRoot 'D:\\mt5' -DataRoot 'D:\\mt5' "
        "-CommonFilesRoot 'C:\\Users\\ADMIN\\AppData\\Roaming\\MetaQuotes\\Terminal\\Common\\Files' "
        "-TesterRoot 'D:\\mt5\\Tester' -PortableMode $true -AllowCommonFiles $true"
    )
    assert bad.returncode != 0
    combined = bad.stdout + bad.stderr
    assert "CommonFilesRoot must stay under DataRoot" in combined


def test_factory_target_rejects_program_files_and_appdata() -> None:
    """Every non-isolate target must be refused.

    The fixture paths below are synthetic sentinels and must stay
    forbidden-shaped; do not retarget them at this machine's real portable.
    """
    sep = chr(92)
    runtime = f"D:{sep}Trading EA MT5{sep}02. AlphaFactory{sep}runtime"
    isolate = f"{runtime}{sep}mt5-portable-mqdemo"

    def esc(path: str) -> str:
        return path.replace(sep, sep * 2)

    bad_pf = run_contract(
        f"Assert-Mt5FactoryTargetIsolate -InstallRoot 'C:{sep*2}Program Files{sep*2}MetaTrader 5' "
        f"-DataRoot 'C:{sep*2}Users{sep*2}ADMIN{sep*2}AppData{sep*2}Roaming{sep*2}MetaQuotes{sep*2}Terminal{sep*2}D0E8209F77C8CF37AD8BF550E51FF075' "
        f"-CommonFilesRoot 'C:{sep*2}Users{sep*2}ADMIN{sep*2}AppData{sep*2}Roaming{sep*2}MetaQuotes{sep*2}Terminal{sep*2}Common{sep*2}Files' "
        f"-TesterRoot 'C:{sep*2}Users{sep*2}ADMIN{sep*2}AppData{sep*2}Roaming{sep*2}MetaQuotes{sep*2}Terminal{sep*2}D0E8209F77C8CF37AD8BF550E51FF075{sep*2}Tester' "
        f"-PortableMode $false -RuntimeRoot '{esc(runtime)}'"
    )
    assert bad_pf.returncode != 0
    assert "Program Files" in (bad_pf.stdout + bad_pf.stderr)

    # This machine's real AppData terminal root -- the only way to actually
    # exercise the AppData branch. The ADMIN fixture above only matches when
    # the current user happens to be named ADMIN, so it never covered it.
    appdata_term = str(Path(os.environ["APPDATA"]) / "MetaQuotes" / "Terminal" / "D0E8209F77C8CF37AD8BF550E51FF075")
    bad_appdata = run_contract(
        f"Assert-Mt5FactoryTargetIsolate -InstallRoot '{esc(isolate)}' "
        f"-DataRoot '{esc(appdata_term)}' "
        f"-CommonFilesRoot '{esc(appdata_term)}{sep*2}Common{sep*2}Files' "
        f"-TesterRoot '{esc(appdata_term)}{sep*2}Tester' "
        f"-PortableMode $true -RuntimeRoot '{esc(runtime)}'"
    )
    assert bad_appdata.returncode != 0
    assert "AppData Terminal" in (bad_appdata.stdout + bad_appdata.stderr)

    # Hardened 2026-08-31: an Owner GUI that lives outside Program Files -- on
    # the Owner machine that is "D:\Meta 5", the terminal the MT5 MCP server
    # attaches to -- must also be refused.
    bad_owner_gui = run_contract(
        f"Assert-Mt5FactoryTargetIsolate -InstallRoot 'D:{sep*2}Meta 5' "
        f"-DataRoot 'D:{sep*2}Meta 5' "
        f"-CommonFilesRoot 'D:{sep*2}Meta 5{sep*2}Common{sep*2}Files' "
        f"-TesterRoot 'D:{sep*2}Meta 5{sep*2}Tester' "
        f"-PortableMode $true -RuntimeRoot '{esc(runtime)}'"
    )
    assert bad_owner_gui.returncode != 0
    assert "outside the factory runtime" in (bad_owner_gui.stdout + bad_owner_gui.stderr)

    # DataRoot must equal the portable InstallRoot.
    bad_split = run_contract(
        f"Assert-Mt5FactoryTargetIsolate -InstallRoot '{esc(isolate)}' "
        f"-DataRoot '{esc(runtime)}{sep*2}mt5-portable-fivepercent' "
        f"-CommonFilesRoot '{esc(isolate)}{sep*2}Common{sep*2}Files' "
        f"-TesterRoot '{esc(isolate)}{sep*2}Tester' "
        f"-PortableMode $true -RuntimeRoot '{esc(runtime)}'"
    )
    assert bad_split.returncode != 0
    assert "DataRoot must equal" in (bad_split.stdout + bad_split.stderr)

    good = run_contract(
        f"Assert-Mt5FactoryTargetIsolate -InstallRoot '{esc(isolate)}' "
        f"-DataRoot '{esc(isolate)}' "
        f"-CommonFilesRoot '{esc(isolate)}{sep*2}Common{sep*2}Files' "
        f"-TesterRoot '{esc(isolate)}{sep*2}Tester' "
        f"-PortableMode $true -RuntimeRoot '{esc(runtime)}' | ConvertTo-Json -Compress"
    )
    assert good.returncode == 0, good.stdout + good.stderr
    payload = json.loads(good.stdout)
    assert payload["portable_mode"] is True


def test_process_isolate_allows_program_files_gui_only() -> None:
    allow = run_contract(
        "Resolve-Mt5ProcessIsolateDecision -ExecutablePath 'C:\\Program Files\\MetaTrader 5\\terminal64.exe' "
        "-CommandLine '\"C:\\Program Files\\MetaTrader 5\\terminal64.exe\"' "
        "-InstallRoot 'D:\\mt5' -DataRoot 'D:\\mt5' "
        "-RuntimeRoot 'D:\\Trading EA MT5\\02. AlphaFactory\\runtime' "
        "-PortableMode $true | ConvertTo-Json -Compress"
    )
    assert allow.returncode == 0, allow.stdout + allow.stderr
    payload = json.loads(allow.stdout)
    assert payload["Allowed"] is True

    block_portable = run_contract(
        "Resolve-Mt5ProcessIsolateDecision "
        "-ExecutablePath 'D:\\Trading EA MT5\\02. AlphaFactory\\runtime\\mt5-portable-fivepercent\\terminal64.exe' "
        "-CommandLine '\"D:\\Trading EA MT5\\02. AlphaFactory\\runtime\\mt5-portable-fivepercent\\terminal64.exe\"' "
        "-InstallRoot 'D:\\Trading EA MT5\\02. AlphaFactory\\runtime\\mt5-portable-mqdemo' "
        "-DataRoot 'D:\\Trading EA MT5\\02. AlphaFactory\\runtime\\mt5-portable-mqdemo' "
        "-RuntimeRoot 'D:\\Trading EA MT5\\02. AlphaFactory\\runtime' "
        "-PortableMode $true | ConvertTo-Json -Compress"
    )
    assert block_portable.returncode == 0, block_portable.stdout + block_portable.stderr
    blocked = json.loads(block_portable.stdout)
    assert blocked["Allowed"] is False
    assert "runtime/portable" in blocked["Reason"]

    block_no_portable = run_contract(
        "Resolve-Mt5ProcessIsolateDecision "
        "-ExecutablePath 'D:\\Trading EA MT5\\02. AlphaFactory\\runtime\\mt5-portable-mqdemo\\terminal64.exe' "
        "-CommandLine '\"D:\\Trading EA MT5\\02. AlphaFactory\\runtime\\mt5-portable-mqdemo\\terminal64.exe\"' "
        "-InstallRoot 'D:\\Trading EA MT5\\02. AlphaFactory\\runtime\\mt5-portable-mqdemo' "
        "-DataRoot 'D:\\Trading EA MT5\\02. AlphaFactory\\runtime\\mt5-portable-mqdemo' "
        "-RuntimeRoot 'D:\\Trading EA MT5\\02. AlphaFactory\\runtime' "
        "-PortableMode $true | ConvertTo-Json -Compress"
    )
    assert block_no_portable.returncode == 0, block_no_portable.stdout + block_no_portable.stderr
    no_flag = json.loads(block_no_portable.stdout)
    assert no_flag["Allowed"] is False
    assert "/portable" in no_flag["Reason"]

    liveupdate = run_contract(
        "Resolve-Mt5ProcessIsolateDecision "
        "-ExecutablePath 'C:\\Users\\ADMIN\\AppData\\Roaming\\MetaQuotes\\Terminal\\36E211F7128BF6ACAF51E2F59961553F\\liveupdate\\terminal64.exe' "
        "-CommandLine '\"C:\\Users\\ADMIN\\AppData\\Roaming\\MetaQuotes\\Terminal\\36E211F7128BF6ACAF51E2F59961553F\\liveupdate\\terminal64.exe\" /update /path:\"D:\\Trading EA MT5\\02. AlphaFactory\\runtime\\mt5-portable-mqdemo\" /portable' "
        "-InstallRoot 'D:\\Trading EA MT5\\02. AlphaFactory\\runtime\\mt5-portable-mqdemo' "
        "-DataRoot 'D:\\Trading EA MT5\\02. AlphaFactory\\runtime\\mt5-portable-mqdemo' "
        "-RuntimeRoot 'D:\\Trading EA MT5\\02. AlphaFactory\\runtime' "
        "-PortableMode $true | ConvertTo-Json -Compress"
    )
    assert liveupdate.returncode == 0, liveupdate.stdout + liveupdate.stderr
    helper = json.loads(liveupdate.stdout)
    assert helper["Allowed"] is True
    assert "liveupdate" in helper["Reason"]


def test_init_machine_paths_refuses_owner_gui_and_alpha_uses_process_isolate() -> None:
    init = (ALPHA_ROOT / "tools" / "init_machine_paths.ps1").read_text(encoding="utf-8-sig")
    assert "Program Files" in init
    assert "Refusing to pin Owner Program Files" in init
    assert "mt5-portable-mqdemo" in init
    alpha = (ALPHA_ROOT / "alpha.ps1").read_text(encoding="utf-8-sig")
    assert "Assert-Mt5FactoryTargetIsolate" in alpha
    assert "Assert-Mt5FactoryProcessIsolate" in alpha
    assert alpha.count("Assert-NoUnrelatedTerminal") >= 3
    assert "Resolve-LocalTesterAgentPort" in alpha
    assert "Port=$testerAgentPort" in alpha
    assert "Wait-PortableLiveUpdate" in alpha
    assert "Find-PortablePostUpdateTester" in alpha
    assert "Stop-OrphanPortableTesters" in alpha
