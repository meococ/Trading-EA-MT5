from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import lancedb
from fastembed import TextEmbedding

MODEL_NAME = 'BAAI/bge-small-en-v1.5'
ROOT = Path(__file__).resolve().parents[2]
ALPHA_ROOT = ROOT / '02. AlphaFactory'
VECTOR_ROOT = ALPHA_ROOT / 'runtime' / 'vector_db'
DB_ROOT = VECTOR_ROOT / 'db'
MANIFEST_PATH = VECTOR_ROOT / 'index_manifest.json'
SOURCE_OF_TRUTH_PATH = ROOT / 'docs' / 'ai' / 'source_of_truth.json'
IGNORE_PARTS = {'.git', '__pycache__', '.claude/runtime', '02. AlphaFactory/runtime/vector_db/db', '02. AlphaFactory/runtime/vector_db/cache'}
COLLECTIONS = ['workspace_docs', 'ea_code', 'run_artifacts', 'lessons_memory', 'research_notes']


@dataclass
class ChunkRecord:
    collection: str
    payload: dict


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect_db():
    DB_ROOT.mkdir(parents=True, exist_ok=True)
    return lancedb.connect(str(DB_ROOT))


def load_registry() -> dict[str, str]:
    if not SOURCE_OF_TRUTH_PATH.exists():
        return {}
    data = json.loads(SOURCE_OF_TRUTH_PATH.read_text(encoding='utf-8'))
    return {entry['path'].replace('\\', '/'): entry['status'] for entry in data.get('entries', [])}


def status_for_path(path: Path, registry: dict[str, str]) -> str:
    rel = relative_path(path)
    return registry.get(rel, 'authoritative')


def relative_path(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT)).replace('\\', '/')


def priority_score(status: str) -> float:
    return {
        'authoritative': 1.0,
        'hypothesis': 0.55,
        'archive': 0.15,
        'invalidated': 0.05,
    }.get(status, 0.5)


def should_index(path: Path) -> bool:
    rel = relative_path(path)
    if any(part in rel for part in IGNORE_PARTS):
        return False
    if not path.is_file():
        return False
    if path.suffix.lower() not in {'.md', '.json', '.mq5', '.mqh'}:
        return False
    if path.stat().st_size > 750_000:
        return False
    return True


def iter_source_paths() -> list[Path]:
    patterns = [
        '.claude/rules/**/*.md',
        'CLAUDE.md',
        'AGENTS.md',
        '.claude/agents/**/*.md',
        '.claude/skills/**/*.md',
        'docs/ai/**/*.md',
        'docs/CLAUDE.md',
        '02. AlphaFactory/CLAUDE.md',
        '03. EA Developer/CLAUDE.md',
        '02. AlphaFactory/STRATEGY_LOG.md',
        'CLAUDE-EXP.md',
        '02. AlphaFactory/runs/*/*/analysis/*.json',
        '02. AlphaFactory/runs/*/*/run_manifest.json',
        '03. EA Developer/**/*.mq5',
        '03. EA Developer/**/*.mqh',
        '03. EA Developer/**/README.md',
        '03. EA Developer/**/REPRO_CHECKLIST.md',
    ]
    found: set[Path] = set()
    for pattern in patterns:
        found.update(ROOT.glob(pattern))
    return sorted(path for path in found if should_index(path))


def classify(path: Path) -> tuple[str, str]:
    rel = relative_path(path)
    suffix = path.suffix.lower()
    if suffix in {'.mq5', '.mqh'}:
        return 'ea_code', 'code'
    if rel.startswith('02. AlphaFactory/runs/'):
        return 'run_artifacts', 'run_artifact'
    if rel in {'CLAUDE-EXP.md', '02. AlphaFactory/STRATEGY_LOG.md'}:
        return 'lessons_memory', 'lessons'
    if rel.startswith('docs/ai/') or rel.startswith('.claude/rules/') or rel == 'CLAUDE.md' or rel == 'AGENTS.md':
        return 'workspace_docs', 'workspace_doc'
    return 'research_notes', 'research_note'


def parse_run_context(path: Path) -> tuple[str, str, str]:
    parts = relative_path(path).split('/')
    if len(parts) >= 5 and parts[0] == '02. AlphaFactory' and parts[1] == 'runs':
        return parts[2], parts[3], parts[3][:8]
    if '03. EA Developer' in parts:
        idx = parts.index('03. EA Developer')
        if len(parts) > idx + 1:
            return parts[idx + 1], '', ''
    return '', '', ''


def parse_manifest_context(path: Path) -> tuple[str, str]:
    if path.name != 'run_manifest.json':
        return '', ''
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return str(data.get('symbol', '')), str(data.get('period', ''))
    except Exception:
        return '', ''


def normalize_text(text: str) -> str:
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def chunk_markdown(text: str, max_chars: int = 1400) -> list[str]:
    blocks = [block.strip() for block in re.split(r'\n\s*\n', text) if block.strip()]
    chunks: list[str] = []
    current = ''
    for block in blocks:
        candidate = f'{current}\n\n{block}'.strip() if current else block
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(block) <= max_chars:
            current = block
        else:
            for i in range(0, len(block), max_chars):
                chunks.append(block[i:i + max_chars])
            current = ''
    if current:
        chunks.append(current)
    return chunks or [text[:max_chars]]


def chunk_code(text: str, lines_per_chunk: int = 90) -> list[str]:
    lines = text.splitlines()
    chunks = []
    for idx in range(0, len(lines), lines_per_chunk):
        chunk = '\n'.join(lines[idx:idx + lines_per_chunk]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks or [text]


def load_text(path: Path) -> str:
    if path.suffix.lower() == '.json':
        try:
            return json.dumps(json.loads(path.read_text(encoding='utf-8')), indent=2)
        except Exception:
            return path.read_text(encoding='utf-8', errors='ignore')
    return path.read_text(encoding='utf-8', errors='ignore')


def build_records() -> dict[str, list[dict]]:
    registry = load_registry()
    grouped: dict[str, list[dict]] = defaultdict(list)
    for path in iter_source_paths():
        text = normalize_text(load_text(path))
        if not text:
            continue
        collection, kind = classify(path)
        ea_name, run_id, date = parse_run_context(path)
        symbol, timeframe = parse_manifest_context(path)
        status = status_for_path(path, registry)
        chunks = chunk_code(text) if path.suffix.lower() in {'.mq5', '.mqh'} else chunk_markdown(text)
        updated_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
        rel = relative_path(path)
        for idx, chunk in enumerate(chunks):
            digest = hashlib.sha1(f'{rel}:{idx}:{chunk}'.encode('utf-8')).hexdigest()
            grouped[collection].append({
                'id': digest,
                'chunk_id': f'{collection}:{digest[:16]}',
                'path': rel,
                'kind': kind,
                'ea_name': ea_name,
                'run_id': run_id,
                'status': status,
                'symbol': symbol,
                'timeframe': timeframe,
                'date': date,
                'updated_at': updated_at,
                'chunk_hash': digest,
                'priority_score': priority_score(status),
                'text': chunk,
            })
    return grouped


def embed_texts(texts: Iterable[str]) -> list[list[float]]:
    model = TextEmbedding(model_name=MODEL_NAME)
    return [list(vec) for vec in model.embed(list(texts))]


def bootstrap() -> dict:
    grouped = build_records()
    db = connect_db()
    total_chunks = 0
    manifest = {
        'built_at': utc_now(),
        'root': str(ROOT),
        'model': MODEL_NAME,
        'collections': {},
        'total_chunks': 0,
    }
    for collection in COLLECTIONS:
        rows = grouped.get(collection, [])
        if rows:
            vectors = embed_texts(row['text'] for row in rows)
            for row, vector in zip(rows, vectors):
                row['vector'] = vector
            db.create_table(collection, data=rows, mode='overwrite')
        elif collection in db.table_names():
            db.drop_table(collection)
        manifest['collections'][collection] = {'count': len(rows)}
        total_chunks += len(rows)
    manifest['total_chunks'] = total_chunks
    VECTOR_ROOT.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return manifest


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {'built_at': None, 'collections': {}, 'total_chunks': 0, 'model': MODEL_NAME}
    return json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))


def tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r'[a-z0-9_+.-]+', text.lower()) if len(token) > 2}


def open_table(collection: str):
    db = connect_db()
    if collection not in db.table_names():
        return None
    return db.open_table(collection)


def semantic_search(query: str, top_k: int = 8, collections: list[str] | None = None, include_archive: bool = False, include_invalidated: bool = False) -> list[dict]:
    collections = collections or COLLECTIONS
    query_vector = embed_texts([query])[0]
    query_tokens = tokenize(query)
    results: list[dict] = []
    for collection in collections:
        table = open_table(collection)
        if table is None:
            continue
        frame = table.search(query_vector).limit(max(top_k * 4, 20)).to_pandas()
        for _, row in frame.iterrows():
            status = row.get('status', 'authoritative')
            if status == 'archive' and not include_archive:
                continue
            if status == 'invalidated' and not include_invalidated:
                continue
            text = str(row.get('text', ''))
            lexical = len(query_tokens & tokenize(text + ' ' + str(row.get('path', ''))))
            distance = float(row.get('_distance', 999.0))
            score = (-distance * 4.0) + lexical + float(row.get('priority_score', 0.0))
            results.append({
                'collection': collection,
                'chunk_id': row.get('chunk_id'),
                'path': row.get('path'),
                'status': status,
                'kind': row.get('kind'),
                'ea_name': row.get('ea_name'),
                'run_id': row.get('run_id'),
                'symbol': row.get('symbol'),
                'timeframe': row.get('timeframe'),
                'updated_at': row.get('updated_at'),
                'score': round(score, 6),
                'distance': round(distance, 6),
                'snippet': text[:400],
                'text': text,
            })
    results.sort(key=lambda item: item['score'], reverse=True)
    return results[:top_k]


def get_chunk(chunk_id: str, collection: str | None = None) -> dict | None:
    collections = [collection] if collection else COLLECTIONS
    for candidate in collections:
        table = open_table(candidate)
        if table is None:
            continue
        frame = table.to_pandas()
        match = frame[frame['chunk_id'] == chunk_id]
        if not match.empty:
            row = match.iloc[0]
            return {key: row.get(key) for key in match.columns}
    return None


def find_related_runs(query: str, top_k: int = 5, ea_name: str = '') -> list[dict]:
    hits = semantic_search(query, top_k=top_k * 2, collections=['run_artifacts'])
    if ea_name:
        hits = [hit for hit in hits if hit.get('ea_name') == ea_name]
    bundled = []
    seen = set()
    for hit in hits:
        key = (hit.get('ea_name'), hit.get('run_id'))
        if key in seen:
            continue
        seen.add(key)
        bundled.append(hit)
        if len(bundled) >= top_k:
            break
    return bundled


def find_similar_failures(query: str, top_k: int = 5) -> list[dict]:
    hits = semantic_search(query, top_k=top_k * 3, collections=['run_artifacts', 'lessons_memory'], include_archive=True)
    failure_terms = ('fail', 'losing', 'invalidated', 'reject', 'drawdown', 'no edge', 'zero edge')
    filtered = [hit for hit in hits if any(term in hit['text'].lower() for term in failure_terms)]
    return filtered[:top_k]


def get_lessons_for_topic(topic: str, top_k: int = 5) -> list[dict]:
    return semantic_search(topic, top_k=top_k, collections=['lessons_memory'], include_archive=True)


def build_source_bundle(query: str, top_k: int = 6) -> list[dict]:
    hits = semantic_search(query, top_k=top_k * 2)
    bundle = []
    seen_paths = set()
    for hit in hits:
        if hit['path'] in seen_paths:
            continue
        seen_paths.add(hit['path'])
        bundle.append({key: hit[key] for key in ('path', 'chunk_id', 'collection', 'status', 'updated_at', 'snippet')})
        if len(bundle) >= top_k:
            break
    return bundle


def print_status(as_json: bool = False) -> None:
    manifest = load_manifest()
    payload = {
        'built_at': manifest.get('built_at'),
        'model': manifest.get('model', MODEL_NAME),
        'total_chunks': manifest.get('total_chunks', 0),
        'collections': manifest.get('collections', {}),
        'db_root': str(DB_ROOT),
        'manifest_path': str(MANIFEST_PATH),
    }
    if as_json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"built_at: {payload['built_at']}")
        print(f"model: {payload['model']}")
        print(f"total_chunks: {payload['total_chunks']}")
        for name, meta in payload['collections'].items():
            print(f"- {name}: {meta.get('count', 0)}")


def main() -> None:
    parser = argparse.ArgumentParser(description='Local vector memory for AlphaFactory workspace.')
    sub = parser.add_subparsers(dest='command', required=True)

    sub.add_parser('bootstrap')
    sub.add_parser('refresh')
    status_parser = sub.add_parser('status')
    status_parser.add_argument('--json', action='store_true')

    query_parser = sub.add_parser('query')
    query_parser.add_argument('--query', required=True)
    query_parser.add_argument('--top-k', type=int, default=8)
    query_parser.add_argument('--collection', action='append')
    query_parser.add_argument('--include-archive', action='store_true')
    query_parser.add_argument('--include-invalidated', action='store_true')

    chunk_parser = sub.add_parser('get-chunk')
    chunk_parser.add_argument('--chunk-id', required=True)
    chunk_parser.add_argument('--collection')

    args = parser.parse_args()
    if args.command in {'bootstrap', 'refresh'}:
        print(json.dumps(bootstrap(), indent=2))
    elif args.command == 'status':
        print_status(as_json=args.json)
    elif args.command == 'query':
        results = semantic_search(
            args.query,
            top_k=args.top_k,
            collections=args.collection,
            include_archive=args.include_archive,
            include_invalidated=args.include_invalidated,
        )
        print(json.dumps(results, indent=2))
    elif args.command == 'get-chunk':
        print(json.dumps(get_chunk(args.chunk_id, args.collection), indent=2))


if __name__ == '__main__':
    main()
