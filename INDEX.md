# INDEX — Workspace map

INDEX chỉ là sitemap. Trạng thái hypothesis nằm ở registry và artifact, không nằm tại đây.

| Cần tìm | Nguồn canonical |
|---|---|
| Quy tắc agent | `AGENTS.md` |
| Mục tiêu và DONE | `01. GOAL/GOAL.md` |
| Workflow duy nhất | `05. Playbook/WORKFLOW.md` |
| MT5/AlphaFactory CLI | `02. AlphaFactory/alpha.ps1` |
| EA/indicator package | `03. EA Developer/README.md` |
| Source EA | `03. EA Developer/<EA>/<EA>.mq5` |
| Custom indicators | `06.Indicator Alpha/` |
| Hypothesis state | `04. Memory/research/CANDIDATE_REGISTRY.jsonl` |
| Hypothesis result/failure packet | `03. EA Developer/<EA>/research/` |
| Registry validator | `04. Memory/research/validate_candidate_registry.py` |
| Recent handoff | `04. Memory/hot.md` |
| Failure radius | `04. Memory/do_not_repeat_failures.md` |
| Strategy history | `02. AlphaFactory/STRATEGY_LOG.md` |
| Runs | `02. AlphaFactory/runs/<EA>/<run_id>/` |
| Research templates | `02. AlphaFactory/templates/research/` |
| Tests/schemas | `02. AlphaFactory/tests/`, `02. AlphaFactory/schemas/` |
| Source registry | `04. Memory/source_of_truth.json` |
| Source validator | `04. Memory/validate_source_of_truth.py` |
| Archive | `00. Old File/` — không dùng làm source/run evidence mới |

Lệnh bắt đầu:

```powershell
./02. AlphaFactory/alpha.ps1 status
python "04. Memory/validate_source_of_truth.py"
python "04. Memory/research/validate_candidate_registry.py"
```
