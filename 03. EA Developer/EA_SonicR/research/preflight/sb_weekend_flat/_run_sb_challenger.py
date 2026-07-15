from pathlib import Path
import hashlib, json, subprocess, sys
from datetime import datetime, timezone
ROOT = Path(r"d:\Trading EA MT5")
EA = ROOT / "03. EA Developer" / "EA_SilverBullet" / "EA_SilverBullet_v2.mq5"
STUBS = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight" / "sb_weekend_flat" / "receipt_stubs_HYP_SB_WEEKEND_FLAT_001"
CTRL_DIR = ROOT / "02. AlphaFactory" / "runs" / "EA_SilverBullet" / "20260714_002046"
RECEIPT = STUBS.parent / "20260714_HYP_SB_WEEKEND_FLAT_001_CHALLENGER_RECEIPT.json"
HID = "HYP-SB-WEEKEND-FLAT-001"
# alpha sorts override keys
OVERRIDES = "InpFridayFlatHour=21;InpFridayFlatMinute=45;InpUseWeekendFlat=1"

def sha256_file(p): return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def sha256_text(t): return hashlib.sha256(t.encode("utf-8")).hexdigest().upper()
def rel(p): return p.resolve().relative_to(ROOT.resolve()).as_posix()

# refresh challenger stubs lightly (reuse control stubs + control hashes)
paths = [ROOT / "AGENTS.md", ROOT / "01. GOAL" / "GOAL.md", EA]
records = [f"{rel(p)}\t{sha256_file(p)}" for p in paths]
prov = sha256_text("\n".join(records))
git_commit = f"NOGIT-{prov}"
git_status = sha256_text("\n".join(["nogit=true", "dirty=true", f"provenance_sha256={prov}"]))
print("COMMIT", git_commit)

# update task packet for challenger role
task = {
  "schema_version": "sonic_research_task_packet.v1",
  "hypothesis_id": HID,
  "run_role": "challenger",
  "matched_control_run_id": "20260714_002046",
  "overrides": OVERRIDES,
}
task_path = STUBS / "task_packet_challenger.json"
task_path.write_text(json.dumps(task, indent=2) + "\n", encoding="utf-8")
prereg = STUBS / "prereg.json"
cost = STUBS / "cost_source_manifest.json"
include = STUBS / "include_note.txt"
ctrl_manifest = CTRL_DIR / "run_manifest.json"
ctrl_report = CTRL_DIR / "report.html"

h_task = sha256_file(task_path)
h_prereg = sha256_file(prereg)
h_cost = sha256_file(cost)
h_include = sha256_file(include)
h_source = sha256_file(EA)
h_ctrl_m = sha256_file(ctrl_manifest)
h_ctrl_r = sha256_file(ctrl_report)
include_closure = sha256_text(f"{str(include.resolve()).lower()}\t{h_include}")

receipt = {
  "schema_version": "sonic_execution_receipt.v1",
  "hypothesis_id": HID,
  "task_packet_sha256": h_task,
  "git_commit": git_commit,
  "git_status_sha256": git_status,
  "binding": {
    "hypothesis_id": HID, "run_role": "challenger", "ea_name": "EA_SilverBullet",
    "symbol": "USDJPY", "period": "M15", "from": "2021.01.01", "to": "2025.12.31",
    "model": 0, "execution_mode": 0, "fixed_delay_ms": 0, "overrides": OVERRIDES,
    "telemetry_tier": "off", "deposit": 100000, "leverage": 100, "spread": "current",
    "required_sidecars": [],
    "symbol_geometry": {"digits": 3, "point": 0.001, "pip_size": 0.01},
    "include_closure_sha256": include_closure,
  },
  "evidence": [
    {"label": "task_packet", "kind": "file", "path": str(task_path.resolve()), "sha256": h_task},
    {"label": "source", "kind": "file", "path": str(EA.resolve()), "sha256": h_source},
    {"label": "prereg", "kind": "file", "path": str(prereg.resolve()), "sha256": h_prereg},
    {"label": "cost_source_manifest", "kind": "file", "path": str(cost.resolve()), "sha256": h_cost},
    {"label": "include_0001", "kind": "file", "path": str(include.resolve()), "sha256": h_include},
    {"label": "matched_control_manifest", "kind": "file", "path": str(ctrl_manifest.resolve()), "sha256": h_ctrl_m},
    {"label": "matched_control_report", "kind": "file", "path": str(ctrl_report.resolve()), "sha256": h_ctrl_r},
  ],
  "generated_at_utc": datetime.now(timezone.utc).isoformat(),
  "note": "challenger weekend-flat vs control 20260714_002046",
}
RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
sha = sha256_file(RECEIPT)
print("RECEIPT_SHA", sha)
cmd = [
  "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
  str(ROOT / "02. AlphaFactory" / "alpha.ps1"), "backtest", "EA_SilverBullet",
  "-Symbol", "USDJPY", "-Period", "M15", "-From", "2021.01.01", "-To", "2025.12.31",
  "-Model", "0", "-Deposit", "100000", "-Leverage", "100", "-TimeoutSec", "7200",
  "-HypothesisId", HID, "-RunRole", "challenger", "-TelemetryTier", "off",
  "-Overrides", OVERRIDES, "-ContractReceipt", str(RECEIPT), "-ContractReceiptSha256", sha,
]
r = subprocess.run(cmd, cwd=str(ROOT))
print("EXIT", r.returncode)
sys.exit(r.returncode)
