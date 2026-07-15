# CLAUDE.md

File con trỏ (pointer-only) — không thêm trạng thái dự án hay doctrine vào đây.

Chuỗi đọc-trước, theo thứ tự:

1. `04. Project Control/ai/hot.md` — sự thật SỐNG. Đọc trước mọi thứ khác.
2. `01. GOAL/GOAL.md` — mục tiêu chúng ta đang hướng tới.
3. `INDEX.md` (root) — bản đồ workspace: mọi thứ nằm ở đâu.
4. `AGENTS.md` — quy tắc vận hành cho mọi agent làm việc trong workspace này.
5. `04. Project Control/ai/do_not_repeat_failures.md` — trước hypothesis/EA mới.

Nguyên tắc nhanh:

- Giao tiếp với Owner và file chỉ dẫn: tiếng Việt. Doc nghiên cứu/evidence
  (hot.md, gates, prereg, readout, registry): tiếng Anh.
- Không bao giờ trả lời từ trí nhớ điều mà `hot.md` có thể trả lời.
- Không backtest có ý nghĩa nào thiếu `hypothesis_id` + registry row
  (hard rules trong `AGENTS.md`).
- Probe rẻ và offline trước; validation nặng chỉ dành cho survivor.
- Harness EA/backtest: `02. AlphaFactory/alpha.ps1` (+ `alpha.local.ps1` máy
  cục bộ, không commit). Không invent toolchain song song.
- Không commit/push Git trừ khi Owner yêu cầu rõ trong message hiện tại.
- Source shelf/failed (SonicR full ledger + SilverBullet binary + 78 stub
  `.ex5` đã archive THẬT 2026-07-15): `00. Old File/EA_Archive/` — không compile
  làm evidence. Active shelf `03. EA Developer/` = 2 lane (`EA_FVGConfluence`,
  `EA_HybridICT_Sonic`) — xem README + `hot.md`.
- Đây là dự án cá nhân: mặc định một checkout/một nhánh hiện tại; không tự tạo
  branch, worktree, clone hay nhánh riêng cho sub-agent nếu Owner chưa yêu cầu.
- Multi-agent roster: `04. Project Control/ai/multi_agent_roster.md` +
  `04. Project Control/ai/agents/` (subs mặc định
  `cursor-grok-4.5-high-fast`; parent = coordinator; parallel READ / serial
  WRITE). Launcher local (gitignored): `.cursor/agents/ea-*.md`.
- Standing: chốt phiên (docs + self-improve merge + cleanup) — `AGENTS.md`
  §6; parent chủ động, sub propose-only cho standing ops; skill
  `04. Project Control/ai/skills/session-closeout/`.
