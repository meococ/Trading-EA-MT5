#!/usr/bin/env python3
"""Acquire outcome-blind SHAU fixing-round history from the official SGE archive.

Only 2017-2023 is authorized before the hypothesis is frozen.  The 2024-2025
holdout is exposed by a separate current XLSX endpoint and remains sealed.
All retained files and manifests must stay below AlphaFactory/external on D:.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import NamedTuple, Sequence


BASE_URL = "https://www.sge.com.cn"
LISTING_PATH = "/sjzx/shjzjhq"
CURRENT_XLSX_PATH = "/portal/marketAutomation/downloadExcelForVmShAuRoundInfo"
SCHEMA_VERSION = "sge_shau_auction_acquisition.v1"
ARTICLE_RE = re.compile(
    r'href="(?P<href>/sjzx/shjzjhq/\d+\?top=[^"]+)"[^>]*>.*?'
    r'上海黄金交易所集中定价(?P<year>\d{4})年(?P<month>\d{1,2})月'
    r'(?P<day>\d{1,2})日行情.*?</a>',
    re.DOTALL,
)
PAGE_RE = re.compile(r"gotoPage\('/sjzx/shjzjhq\?p=',\s*'(\d+)'\)")


class Article(NamedTuple):
    trade_date: str
    href: str

    @property
    def year(self) -> int:
        return int(self.trade_date[:4])

    @property
    def url(self) -> str:
        return BASE_URL + self.href


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            stripped = " ".join(data.split())
            if stripped:
                self._cell.append(stripped)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(" ".join(self._cell))
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            if self._row:
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            if self._table:
                self.tables.append(self._table)
            self._table = None


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest().upper()


def require_d_external(path: Path) -> Path:
    resolved = path.resolve()
    if os.name == "nt" and resolved.drive.upper() != "D:":
        raise ValueError(f"SGE corpus must be on D:, got {resolved}")
    expected = Path(__file__).resolve().parents[1] / "external"
    if expected.resolve() not in (resolved, *resolved.parents):
        raise ValueError(f"corpus must remain below {expected.resolve()}, got {resolved}")
    return resolved


def fetch_bytes(url: str, timeout_seconds: int = 45, attempts: int = 3) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AlphaFactory/1.0 source-feasibility (official public data)",
            "Accept": "text/html,application/xhtml+xml,application/octet-stream",
        },
    )
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                payload = response.read()
            if not payload:
                raise OSError(f"empty response: {url}")
            return payload
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(0.5 * (attempt + 1))
    raise OSError(f"failed to fetch {url}: {last_error}")


def parse_listing_html(html: str) -> tuple[list[Article], int]:
    articles: list[Article] = []
    for match in ARTICLE_RE.finditer(html):
        trade_date = (
            f"{int(match.group('year')):04d}-{int(match.group('month')):02d}-"
            f"{int(match.group('day')):02d}"
        )
        articles.append(Article(trade_date, match.group("href")))
    pages = [int(value) for value in PAGE_RE.findall(html)]
    return articles, max(pages, default=1)


def parse_article_rounds(html: str, trade_date: str, source_url: str) -> list[dict]:
    parser = TableParser()
    parser.feed(html)
    rows: list[dict] = []
    for table in parser.tables:
        session: int | None = None
        for cells in table:
            normalized = " ".join(cells).upper()
            # Legacy 2017 articles sometimes mistranslate the afternoon header
            # as SESSION 1.  The Chinese labels are unambiguous and authoritative.
            if "早盘" in normalized:
                session = 1
                continue
            if "午盘" in normalized:
                session = 2
                continue
            if "SESSION 1 ROUND" in normalized:
                session = 1
                continue
            if "SESSION 2 ROUND" in normalized:
                session = 2
                continue
            if session is None or len(cells) < 5 or not re.fullmatch(r"\d+", cells[0]):
                continue
            try:
                round_number = int(cells[0])
                price = float(cells[1].replace(",", ""))
                bid = float(cells[2].replace(",", ""))
                ask = float(cells[3].replace(",", ""))
                supplemental = float(cells[4].replace(",", ""))
            except ValueError:
                continue
            rows.append(
                {
                    "trade_date": trade_date,
                    "contract": "SHAU",
                    "session": session,
                    "round": round_number,
                    "price_cny_per_gram": price,
                    "bid_kg": bid,
                    "ask_kg": ask,
                    "supplemental_balance_kg": supplemental,
                    "source_url": source_url,
                }
            )
    return rows


def current_xlsx_url(start_date: str, end_date: str, session_id: str = "") -> str:
    return (
        BASE_URL
        + CURRENT_XLSX_PATH
        + f"?start_date={start_date}&end_date={end_date}"
        + "&inst_ids=SHAU"
        + f"&session_id={session_id}"
    )


def inventory_articles(year_from: int, year_to: int, workers: int) -> list[Article]:
    first = fetch_bytes(BASE_URL + LISTING_PATH).decode("utf-8", errors="replace")
    first_rows, page_count = parse_listing_html(first)
    page_numbers = list(range(2, page_count + 1))

    def load_page(page: int) -> list[Article]:
        payload = fetch_bytes(f"{BASE_URL}{LISTING_PATH}?p={page}")
        return parse_listing_html(payload.decode("utf-8", errors="replace"))[0]

    rows = list(first_rows)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for page_rows in pool.map(load_page, page_numbers):
            rows.extend(page_rows)
    selected = {
        row.trade_date: row
        for row in rows
        if year_from <= row.year <= year_to
    }
    return [selected[key] for key in sorted(selected)]


def acquire(root: Path, year_from: int, year_to: int, workers: int) -> dict:
    if year_to >= 2024:
        raise ValueError("holdout years 2024-2025 are sealed before frozen outcomes")
    root = require_d_external(root)
    raw_root = root / "raw"
    raw_root.mkdir(parents=True, exist_ok=True)
    prior_manifest = root / "source_manifest.json"
    articles: list[Article] = []
    if prior_manifest.is_file():
        prior = json.loads(prior_manifest.read_text(encoding="utf-8"))
        selection = prior.get("selection", {})
        if selection.get("year_from") == year_from and selection.get("year_to") == year_to:
            for record in prior.get("articles", []):
                parts = urllib.parse.urlsplit(record["source_url"])
                href = parts.path + (f"?{parts.query}" if parts.query else "")
                candidate = Article(record["trade_date"], href)
                cached = raw_root / str(candidate.year) / f"{candidate.trade_date}.html"
                if cached.is_file():
                    articles.append(candidate)
    if not articles:
        articles = inventory_articles(year_from, year_to, workers)
    if not articles:
        raise RuntimeError("official SGE archive returned no selected articles")

    def load_article(article: Article) -> tuple[dict, list[dict]]:
        destination = raw_root / str(article.year) / f"{article.trade_date}.html"
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.is_file():
            payload = fetch_bytes(article.url)
            partial = destination.with_suffix(".html.part")
            partial.write_bytes(payload)
            os.replace(partial, destination)
        html = destination.read_text(encoding="utf-8", errors="replace")
        rounds = parse_article_rounds(html, article.trade_date, article.url)
        if not rounds:
            raise ValueError(f"no SHAU rounds parsed for {article.trade_date}: {article.url}")
        workspace = Path(__file__).resolve().parents[2]
        record = {
            "trade_date": article.trade_date,
            "source_url": article.url,
            "path": destination.relative_to(workspace).as_posix(),
            "size_bytes": destination.stat().st_size,
            "sha256": sha256_file(destination),
            "round_count": len(rounds),
            "sessions": sorted({row["session"] for row in rounds}),
        }
        return record, rounds

    records: list[dict] = []
    round_rows: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = [pool.submit(load_article, article) for article in articles]
        for completed, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            record, rows = future.result()
            records.append(record)
            round_rows.extend(rows)
            if completed % 100 == 0 or completed == len(futures):
                print(f"SGE_SHAU_ACQUIRE articles={completed}/{len(futures)}")
    records.sort(key=lambda row: row["trade_date"])
    round_rows.sort(key=lambda row: (row["trade_date"], row["session"], row["round"]))

    csv_path = root / "shau_fixing_rounds.csv"
    csv_tmp = csv_path.with_suffix(".csv.tmp")
    fieldnames = [
        "trade_date",
        "contract",
        "session",
        "round",
        "price_cny_per_gram",
        "bid_kg",
        "ask_kg",
        "supplemental_balance_kg",
        "source_url",
    ]
    with csv_tmp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(round_rows)
    os.replace(csv_tmp, csv_path)

    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": {
            "official_archive": BASE_URL + LISTING_PATH,
            "official_current_page": BASE_URL + "/sjzx/shanghaiAuAuto",
            "official_rules": "https://en.sge.com.cn/upload/file/202001/17/RnByn7qMIWiZca3s.pdf",
            "contract": "SHAU",
        },
        "selection": {
            "year_from": year_from,
            "year_to": year_to,
            "holdout_2024_2025_acquired": False,
            "holdout_endpoint_verified_schema_only": True,
            "legacy_session_authority": "Chinese AM/PM label before English session number",
        },
        "article_count": len(records),
        "round_count": len(round_rows),
        "first_trade_date": records[0]["trade_date"],
        "last_trade_date": records[-1]["trade_date"],
        "total_size_bytes": sum(row["size_bytes"] for row in records),
        "rounds_csv": csv_path.relative_to(Path(__file__).resolve().parents[2]).as_posix(),
        "rounds_csv_sha256": sha256_file(csv_path),
        "articles": records,
        "price_outcomes_accessed": False,
        "research_authorized": False,
    }
    manifest = root / "source_manifest.json"
    temporary = manifest.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, manifest)
    return payload


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    alpha_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=alpha_root / "external" / "sge_shau_auction")
    parser.add_argument("--year-from", type=int, default=2017)
    parser.add_argument("--year-to", type=int, default=2023)
    parser.add_argument("--workers", type=int, default=12)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.year_from > args.year_to:
        raise SystemExit("year-from must be <= year-to")
    payload = acquire(args.root, args.year_from, args.year_to, args.workers)
    print(
        "SGE_SHAU_ACQUIRE "
        f"articles={payload['article_count']} rounds={payload['round_count']} "
        f"dates={payload['first_trade_date']}..{payload['last_trade_date']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
