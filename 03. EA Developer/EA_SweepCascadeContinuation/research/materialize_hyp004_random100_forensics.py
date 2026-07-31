#!/usr/bin/env python3
"""Materialize the accepted Grok synthesis and a browsable 100-trade gallery."""

from __future__ import annotations

import csv
import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def binding(workspace: Path, path: Path) -> dict[str, object]:
    return {
        "path": path.relative_to(workspace).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def main() -> int:
    workspace = Path(__file__).resolve().parents[3]
    evidence = (
        workspace
        / "03. EA Developer"
        / "EA_SweepCascadeContinuation"
        / "research"
        / "evidence"
        / "HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_PAIR_ANALYSIS"
    )
    random_root = evidence / "random100_forensics"
    review_root = random_root / "grok_review"
    context_root = workspace / ".context" / "scc-hyp004-random100-gfi"
    aggregate_root = context_root / "aggregate"
    aggregate_run = aggregate_root / "run2"

    sample_csv = random_root / "random100_cases.csv"
    sample_manifest = random_root / "random100_sample_manifest.json"
    casebook_qc = random_root / "random100_casebook_qc.json"
    batch_qc = review_root / "random100_grok_batch_qc.json"
    stats_path = review_root / "random100_grok_descriptive_stats.json"
    reviews_path = review_root / "random100_grok_case_reviews.jsonl"
    decision_manifest_path = random_root / "decision_asof" / "cases_manifest.json"
    anatomy_manifest_path = random_root / "anatomy" / "cases_manifest.json"
    aggregate_request = aggregate_root / "grok-request.json"
    aggregate_response = aggregate_run / "grok-response.json"
    aggregate_summary = aggregate_run / "summary.json"

    summary = json.loads(aggregate_summary.read_text(encoding="utf-8-sig"))
    if (
        summary.get("success") is not True
        or summary.get("response_useful") is not True
        or "EndTurn" not in str(summary.get("stop_reason"))
        or (summary.get("structured_output_validation") or {}).get("passed") is not True
    ):
        raise SystemExit("Aggregate Grok response did not pass runner gates")
    response = json.loads(aggregate_response.read_text(encoding="utf-8-sig"))
    payload = json.loads(response["output_text"])
    expected_coverage = {
        "reviewed_cases": 100,
        "decision_images_opened_by_batches": 100,
        "anatomy_images_opened_by_batches": 100,
        "total_images_opened_by_batches": 200,
    }
    if payload.get("coverage") != expected_coverage:
        raise SystemExit("Aggregate coverage does not match 100/100/200")
    if (
        payload.get("validity_verdict") != "VALID_RANDOM100_VISUAL_FORENSIC_SAMPLE"
        or payload.get("economic_verdict")
        != "CONFIRMS_TERMINAL_KILL_NO_POSITIVE_EXPECTANCY"
        or payload.get("same_id_tuning_authorized") is not False
    ):
        raise SystemExit("Aggregate verdict contract mismatch")

    readout_path = random_root / "HYP004_RANDOM100_GROK_FORENSIC_READOUT.md"
    provenance = (
        "<!--\n"
        "Grok synthesis provenance:\n"
        f"- aggregate_request_sha256: {sha256(aggregate_request)}\n"
        f"- aggregate_response_sha256: {sha256(aggregate_response)}\n"
        f"- aggregate_summary_sha256: {sha256(aggregate_summary)}\n"
        f"- batch_qc_sha256: {sha256(batch_qc)}\n"
        "- coverage: 100 frozen random trades; 100 decision + 100 anatomy images\n"
        "- batch04 transport note: one substantive Grok EndTurn response emitted the\n"
        "  same schema-valid JSON twice; caller normalized one exact instance without\n"
        "  editing content and hash-bound the source candidate.\n"
        "-->\n\n"
    )
    readout_path.write_text(
        provenance + payload["report_markdown"].rstrip() + "\n", encoding="utf-8"
    )

    with sample_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        samples = list(csv.DictReader(handle))
    reviews = [
        json.loads(line)
        for line in reviews_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    reviews_by_id = {row["case_id"]: row for row in reviews}
    decision_manifest = json.loads(
        decision_manifest_path.read_text(encoding="utf-8-sig")
    )
    anatomy_manifest = json.loads(anatomy_manifest_path.read_text(encoding="utf-8-sig"))
    decision_by_id = {row["case_id"]: row for row in decision_manifest["results"]}
    anatomy_by_id = {row["case_id"]: row for row in anatomy_manifest["results"]}
    if (
        len(samples) != 100
        or len(reviews_by_id) != 100
        or set(reviews_by_id) != {row["case_id"] for row in samples}
    ):
        raise SystemExit("Gallery sample/review coverage mismatch")

    cards: list[str] = []
    referenced_images: list[Path] = []
    for sample in samples:
        case_id = sample["case_id"]
        review = reviews_by_id[case_id]
        decision_png = Path("decision_asof") / decision_by_id[case_id]["png"]
        anatomy_png = Path("anatomy") / anatomy_by_id[case_id]["png"]
        decision_abs = random_root / decision_png
        anatomy_abs = random_root / anatomy_png
        if not decision_abs.is_file() or not anatomy_abs.is_file():
            raise SystemExit(f"Gallery image missing: {case_id}")
        referenced_images.extend([decision_abs, anatomy_abs])
        decision_text = " ".join(review["decision_observations"])
        anatomy_text = " ".join(review["anatomy_observations"])
        cards.append(
            f"""
<article class="trade-card" data-outcome="{html.escape(review['outcome'])}"
 data-mechanism="{html.escape(review['mechanism'])}"
 data-direction="{html.escape(review['direction'])}">
  <header>
    <div>
      <span class="rank">#{int(review['sample_rank']):03d}</span>
      <h2>{html.escape(case_id)}</h2>
    </div>
    <div class="badges">
      <span class="badge {review['outcome'].lower()}">{html.escape(review['outcome'])}</span>
      <span class="badge">{html.escape(review['direction'])}</span>
      <span class="badge">R {float(review['net_R']):+.3f}</span>
      <span class="badge">{html.escape(review['mechanism'])}</span>
    </div>
  </header>
  <div class="images">
    <figure>
      <figcaption>Decision as-of — outcome hidden</figcaption>
      <a href="{html.escape(decision_png.as_posix())}">
        <img loading="lazy" src="{html.escape(decision_png.as_posix())}"
             alt="{html.escape(case_id)} decision as-of chart">
      </a>
    </figure>
    <figure>
      <figcaption>Anatomy — entry / SL / TP / exit</figcaption>
      <a href="{html.escape(anatomy_png.as_posix())}">
        <img loading="lazy" src="{html.escape(anatomy_png.as_posix())}"
             alt="{html.escape(case_id)} anatomy chart">
      </a>
    </figure>
  </div>
  <details>
    <summary>Grok case notes and numeric truth</summary>
    <dl>
      <dt>Entry → exit</dt><dd>{html.escape(review['entry_time_utc'])} → {html.escape(review['exit_time_utc'])}</dd>
      <dt>Position / exit class</dt><dd>{review['position_id']} / {html.escape(review['exit_class'])}</dd>
      <dt>Net / hold / risk</dt><dd>{float(review['net_account']):+.2f} account · {float(review['hold_minutes']):.1f} min · {float(review['risk_points']):.1f} pts</dd>
      <dt>Decision notes</dt><dd>{html.escape(decision_text)}</dd>
      <dt>Anatomy notes</dt><dd>{html.escape(anatomy_text)}</dd>
      <dt>Evidence class</dt><dd>{html.escape(review['evidence_class'])}</dd>
    </dl>
  </details>
</article>"""
        )

    gallery_path = random_root / "random100_gallery.html"
    gallery = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>HYP-004 Random-100 Grok Trade Forensics</title>
  <style>
    :root {{ color-scheme: dark; --bg:#0b0f14; --panel:#121923; --line:#253244;
      --text:#e7edf6; --muted:#9fb0c5; --accent:#65b3ff; --win:#1aa66a; --loss:#d65454; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--bg); color:var(--text);
      font:14px/1.5 Inter,Segoe UI,Arial,sans-serif; }}
    .shell {{ width:min(1880px,96vw); margin:0 auto; padding:28px 0 80px; }}
    .hero {{ position:sticky; top:0; z-index:5; background:rgba(11,15,20,.94);
      backdrop-filter:blur(12px); border-bottom:1px solid var(--line); padding:16px 0; }}
    h1 {{ margin:0 0 8px; font-size:28px; }}
    .hero p {{ margin:4px 0; color:var(--muted); }}
    .filters {{ display:flex; flex-wrap:wrap; gap:10px; margin-top:14px; }}
    select,input {{ background:var(--panel); color:var(--text); border:1px solid var(--line);
      border-radius:8px; padding:9px 12px; }}
    .count {{ margin-left:auto; color:var(--accent); align-self:center; font-weight:700; }}
    .grid {{ display:grid; gap:20px; margin-top:24px; }}
    .trade-card {{ background:var(--panel); border:1px solid var(--line); border-radius:14px;
      padding:16px; box-shadow:0 12px 30px rgba(0,0,0,.22); }}
    .trade-card header {{ display:flex; gap:18px; justify-content:space-between;
      align-items:center; margin-bottom:12px; }}
    .trade-card h2 {{ display:inline; font-size:16px; margin:0 0 0 8px; }}
    .rank {{ color:var(--accent); font-weight:800; }}
    .badges {{ display:flex; flex-wrap:wrap; gap:7px; justify-content:flex-end; }}
    .badge {{ border:1px solid var(--line); border-radius:999px; padding:4px 9px;
      color:var(--muted); }}
    .badge.win {{ border-color:var(--win); color:#73e6b3; }}
    .badge.loss {{ border-color:var(--loss); color:#ff9898; }}
    .images {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }}
    figure {{ margin:0; min-width:0; }}
    figcaption {{ color:var(--muted); margin:0 0 7px; font-weight:650; }}
    img {{ display:block; width:100%; height:auto; border:1px solid var(--line);
      border-radius:9px; background:#fff; }}
    details {{ margin-top:12px; border-top:1px solid var(--line); padding-top:10px; }}
    summary {{ cursor:pointer; color:var(--accent); }}
    dl {{ display:grid; grid-template-columns:170px 1fr; gap:6px 12px; }}
    dt {{ color:var(--muted); }} dd {{ margin:0; }}
    .notice {{ border-left:3px solid #f0b84b; padding:9px 12px; background:#1b1810;
      margin-top:12px; color:#f4dca9; }}
    @media(max-width:900px) {{ .images {{ grid-template-columns:1fr; }}
      .trade-card header {{ align-items:flex-start; flex-direction:column; }}
      .badges {{ justify-content:flex-start; }} dl {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
<div class="hero"><div class="shell" style="padding-top:0;padding-bottom:0">
  <h1>HYP-004 Random-100 Grok Trade Forensics</h1>
  <p>Seed 20260725 · 100 of 261 challenger trades · 28 wins / 72 losses · 200 hash-checked PNGs.</p>
  <p class="notice">Decision images are outcome-blind. Anatomy images disclose outcomes.
  Grok mechanism labels are descriptive and noisy; numeric lifecycle truth has priority.</p>
  <div class="filters">
    <select id="outcome"><option value="">All outcomes</option><option>WIN</option><option>LOSS</option></select>
    <select id="direction"><option value="">All directions</option><option>BUY</option><option>SELL</option></select>
    <select id="mechanism"><option value="">All mechanisms</option>
      <option>IMMEDIATE_CONTINUATION_EXPANSION</option>
      <option>TIGHT_STOP_MICROSTRUCTURE_FAILURE</option>
      <option>NO_FOLLOWTHROUGH_TIMEOUT</option>
      <option>MIXED_OR_OTHER</option></select>
    <input id="search" placeholder="case ID or position">
    <span class="count" id="count">100 visible</span>
  </div>
</div></div>
<main class="shell"><section class="grid">{''.join(cards)}</section></main>
<script>
const cards=[...document.querySelectorAll('.trade-card')];
const controls=['outcome','direction','mechanism','search'].map(id=>document.getElementById(id));
function apply(){{
  const outcome=controls[0].value, direction=controls[1].value,
        mechanism=controls[2].value, search=controls[3].value.toLowerCase();
  let visible=0;
  cards.forEach(card=>{{
    const ok=(!outcome||card.dataset.outcome===outcome)&&
      (!direction||card.dataset.direction===direction)&&
      (!mechanism||card.dataset.mechanism===mechanism)&&
      (!search||card.textContent.toLowerCase().includes(search));
    card.hidden=!ok; if(ok) visible++;
  }});
  document.getElementById('count').textContent=visible+' visible';
}}
controls.forEach(control=>control.addEventListener(control.tagName==='INPUT'?'input':'change',apply));
</script>
</body></html>"""
    gallery_path.write_text(gallery, encoding="utf-8")

    if len(referenced_images) != 200 or len(set(referenced_images)) != 200:
        raise SystemExit("Gallery does not reference exactly 200 unique images")
    receipt = {
        "schema_version": "scc_random100_forensics_receipt.v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_id": "HYP-SCC-MT5-REPLICATION-EURUSD-M5-004",
        "run_id": "20260725_210811",
        "status": "PASS",
        "coverage": expected_coverage,
        "validity_verdict": payload["validity_verdict"],
        "economic_verdict": payload["economic_verdict"],
        "same_id_tuning_authorized": payload["same_id_tuning_authorized"],
        "batch_transport": {
            "runner_accepted_structured_batches": 19,
            "caller_normalized_exact_duplicate_batches": 1,
            "normalized_batch": "batch04",
            "content_edited": False,
        },
        "bindings": {
            "sample_manifest": binding(workspace, sample_manifest),
            "casebook_qc": binding(workspace, casebook_qc),
            "batch_qc": binding(workspace, batch_qc),
            "descriptive_stats": binding(workspace, stats_path),
            "case_reviews": binding(workspace, reviews_path),
            "aggregate_request": binding(workspace, aggregate_request),
            "aggregate_response": binding(workspace, aggregate_response),
            "aggregate_summary": binding(workspace, aggregate_summary),
            "readout": binding(workspace, readout_path),
            "gallery": binding(workspace, gallery_path),
        },
        "gallery": {
            "cards": 100,
            "referenced_images": 200,
            "decision_images": 100,
            "anatomy_images": 100,
        },
    }
    receipt_path = random_root / "random100_forensics_receipt.json"
    receipt_path.write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        "SCC_RANDOM100_FORENSICS_OK "
        f"cases=100 images=200 readout_sha256={sha256(readout_path)} "
        f"gallery_sha256={sha256(gallery_path)} receipt_sha256={sha256(receipt_path)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
