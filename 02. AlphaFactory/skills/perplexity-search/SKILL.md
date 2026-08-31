---
name: perplexity-search
description: Web research fallback. Claude Code có web_search/web_fetch native — dùng native tools trước, perplexity chỉ khi cần deep research hoặc source-backed summaries.
status: DEPRECATED-SOFT — prefer native Claude Code tools
---

## Status
- **Claude Code native tools**: `web_search` + `web_fetch` đã có sẵn → dùng trước
- **Perplexity script**: chỉ dùng khi cần deep research với citations hoặc native tools không đủ
- **External dependency**: script ở `.openclaw/workspace/` — không nằm trong AlphaFactory

## Khi nào dùng native tools (ưu tiên)
- Fact lookup nhanh → `web_search`
- Đọc URL cụ thể → `web_fetch`
- MQL5 docs, MetaQuotes API → `web_search` hoặc Context7 MCP

## Khi nào dùng Perplexity (fallback)
- Cần deep research với source citations
- Cần tổng hợp từ nhiều nguồn (academic, forum, broker docs)
- Native tools trả kết quả không đủ tốt

## Lệnh chạy (nếu cần)
- `$env:PYTHONIOENCODING='utf-8'; python "C:\Users\ADMIN\.openclaw\workspace\skills\perplexity-search\scripts\search.py" "<query>"`

## Rules
- Query concise và specific
- Report error nếu script fail, tiếp tục với native tools
