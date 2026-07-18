from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "02. AlphaFactory" / "tools" / "acquire_sge_shau_auction.py"


def load_module():
    spec = importlib.util.spec_from_file_location("acquire_sge_shau_auction", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_listing_parser_extracts_date_link_and_last_page() -> None:
    module = load_module()
    html = '''
    <a href="/sjzx/shjzjhq/100?top=abc" class="title">
      上海黄金交易所集中定价2023年12月29日行情
    </a>
    <li onclick="gotoPage('/sjzx/shjzjhq?p=','188')">188</li>
    '''
    rows, pages = module.parse_listing_html(html)
    assert rows == [module.Article("2023-12-29", "/sjzx/shjzjhq/100?top=abc")]
    assert pages == 188


def test_article_parser_extracts_two_sessions() -> None:
    module = load_module()
    html = '''
    <table>
      <tr><td>早盘轮次/SESSION 1 ROUND</td><td>价格/PRC</td><td>买量/BID</td><td>卖量/ASK</td><td>补充申报量/SUP.BAL.VOL</td></tr>
      <tr><td>1</td><td>478.84</td><td>438</td><td>0</td><td>3</td></tr>
      <tr><td>午盘轮次/SESSION 2 ROUND</td><td>价格/PRC</td><td>买量/BID</td><td>卖量/ASK</td><td>补充申报量/SUP.BAL.VOL</td></tr>
      <tr><td>1</td><td>480.93</td><td>196</td><td>13</td><td>68</td></tr>
    </table>
    '''
    rows = module.parse_article_rounds(html, "2023-12-29", "https://official")
    assert len(rows) == 2
    assert rows[0]["session"] == 1
    assert rows[0]["supplemental_balance_kg"] == 3.0
    assert rows[1]["session"] == 2
    assert rows[1]["bid_kg"] == 196.0
    assert rows[1]["ask_kg"] == 13.0


def test_legacy_mislabeled_afternoon_uses_chinese_authority() -> None:
    module = load_module()
    html = '''
    <table>
      <tr><td>早盘轮次/SESSION 1 ROUND</td><td>价格</td><td>买量</td><td>卖量</td><td>补充申报量</td></tr>
      <tr><td>1</td><td>264.04</td><td>1354</td><td>0</td><td>0</td></tr>
    </table>
    <table>
      <tr><td>午盘轮次/SESSION 1 ROUND</td><td>价格</td><td>买量</td><td>卖量</td><td>补充申报量</td></tr>
      <tr><td>1</td><td>264.40</td><td>0</td><td>1404</td><td>0</td></tr>
    </table>
    '''
    rows = module.parse_article_rounds(html, "2017-01-03", "https://official")
    assert [(row["session"], row["round"]) for row in rows] == [(1, 1), (2, 1)]


def test_current_endpoint_is_exact_shau_contract() -> None:
    module = load_module()
    url = module.current_xlsx_url("2025-01-02", "2025-01-02", "2")
    assert "downloadExcelForVmShAuRoundInfo" in url
    assert "inst_ids=SHAU" in url
    assert "session_id=2" in url


def test_holdout_guard_precedes_network(monkeypatch, tmp_path: Path) -> None:
    module = load_module()
    monkeypatch.setattr(module, "require_d_external", lambda path: path)
    try:
        module.acquire(tmp_path, 2017, 2024, 1)
    except ValueError as exc:
        assert "sealed" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("holdout guard did not fail")
