from pathlib import Path
import hashlib, json, re, subprocess, sys
from datetime import datetime, timezone
ROOT = Path(r"d:\Trading EA MT5")
alpha = (ROOT / "02. AlphaFactory" / "alpha.ps1").read_text(encoding="utf-8", errors="replace")
m = re.search(r'\$activeEa = Join-Path \$AdvisorsRoot "([^"]+)"', alpha)
active_rel = m.group(1).replace("\\", "/") if m else None
print("ACTIVE_REL", active_rel)
EA = ROOT / "03. EA Developer" / "EA_SilverBullet" / "EA_SilverBullet_v2.mq5"
STUBS = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight" / "sb_weekend_flat" / "receipt_stubs_HYP_SB_WEEKEND_FLAT_001"
RECEIPT = STUBS.parent / "20260713_HYP_SB_WEEKEND_FLAT_001_CONTROL_RECEIPT.json"

def sha256_file(p): return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def sha256_text(t): return hashlib.sha256(t.encode("utf-8")).hexdigest().upper()
def rel(p): return p.resolve().relative_to(ROOT.resolve()).as_posix()

paths = [ROOT / "AGENTS.md", ROOT / "01. GOAL" / "GOAL.md"]
if active_rel:
    active = ROOT / active_rel
    if active.exists():
        paths.append(active)
        print("ACTIVE_HASH", sha256_file(active))
    else:
        print("ACTIVE_MISSING", active)
records = [f"{rel(p)}\t{sha256_file(p)}" for p in paths]
prov = sha256_text("\n".join(records))
git_commit = f"NOGIT-{prov}"
git_status = sha256_text("\n".join(["nogit=true", "dirty=true", f"provenance_sha256={prov}"]))
print("COMMIT", git_commit)
print("STATUS", git_status)
HID = "HYP-SB-WEEKEND-FLAT-001"
OVERRIDES = "InpUseWeekendFlat=0"
include = STUBS / "include_note.txt"
h_task = sha256_file(STUBS / "task_packet.json")
h_prereg = sha256_file(STUBS / "prereg.json")
h_cost = sha256_file(STUBS / "cost_source_manifest.json")
h_include = sha256_file(include)
h_source = sha256_file(EA)
include_closure = sha256_text(f"{str(include.resolve()).lower()}\t{h_include}")
receipt = {
  "schema_version": "sonic_execution_receipt.v1",
  "hypothesis_id": HID,
  "task_packet_sha256": h_task,
  "git_commit": git_commit,
  "git_status_sha256": git_status,
  "binding": {
    "hypothesis_id": HID, "run_role": "control", "ea_name": "EA_SilverBullet",
    "symbol": "USDJPY", "period": "M15", "from": "2021.01.01", "to": "2025.12.31",
    "model": 0, "execution_mode": 0, "fixed_delay_ms": 0, "overrides": OVERRIDES,
    "telemetry_tier": "off", "deposit": 100000, "leverage": 100, "spread": "current",
    "required_sidecars": [],
    "symbol_geometry": {"digits": 3, "point": 0.001, "pip_size": 0.01},
    "include_closure_sha256": include_closure,
  },
  "evidence": [
    {"label": "task_packet", "kind": "file", "path": str((STUBS / "task_packet.json").resolve()), "sha256": h_task},
    {"label": "source", "kind": "file", "path": str(EA.resolve()), "sha256": h_source},
    {"label": "prereg", "kind": "file", "path": str((STUBS / "prereg.json").resolve()), "sha256": h_prereg},
    {"label": "cost_source_manifest", "kind": "file", "path": str((STUBS / "cost_source_manifest.json").resolve()), "sha256": h_cost},
    {"label": "include_0001", "kind": "file", "path": str(include.resolve()), "sha256": h_include},
  ],
  "generated_at_utc": datetime.now(timezone.utc).isoformat(),
  "note": f"control; NOGIT active={active_rel}",
}
RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
sha = sha256_file(RECEIPT)
print("RECEIPT_SHA", sha)
cmd = [
  "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
  str(ROOT / "02. AlphaFactory" / "alpha.ps1"), "backtest", "EA_SilverBullet",
  "-Symbol", "USDJPY", "-Period", "M15", "-From", "2021.01.01", "-To", "2025.12.31",
  "-Model", "0", "-Deposit", "100000", "-Leverage", "100", "-TimeoutSec", "7200",
  "-HypothesisId", HID, "-RunRole", "control", "-TelemetryTier", "off",
  "-Overrides", OVERRIDES, "-ContractReceipt", str(RECEIPT), "-ContractReceiptSha256", sha,
]
r = subprocess.run(cmd, cwd=str(ROOT))
print("EXIT", r.returncode)
sys.exit(r.returncode)
