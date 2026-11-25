"""
Eval de calidad del retrieve (sin LLM).

Uso (con API/Postgres + ingest hechos):
  cd backend
  python -m app.eval.run_retrieve_eval
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import yaml
from sqlalchemy.ext.asyncio import create_async_engine

from app.adapters.embeddings.factory import build_embeddings
from app.adapters.vector_store.pgvector_store import PgVectorStore
from app.config import get_settings
from app.eval.retrieve_metrics import aggregate_scores, score_retrieve_case
from app.use_cases.search_documents import SearchDocuments

DEFAULT_EVAL = Path(__file__).resolve().parents[2] / "data" / "evals" / "retrieve_eval.yaml"


async def _run(eval_path: Path, min_source_rate: float) -> int:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    store = PgVectorStore(engine)
    embeddings = build_embeddings(settings)
    search = SearchDocuments(
        embeddings=embeddings,
        vector_store=store,
        default_top_k=settings.retrieve_top_k,
        default_min_score=settings.retrieve_min_score,
    )

    payload = yaml.safe_load(eval_path.read_text(encoding="utf-8")) or {}
    cases = payload.get("cases") or []
    scores = []
    for case in cases:
        result = await search.execute(case["query"])
        score = score_retrieve_case(
            case_id=case["id"],
            hits=result.hits,
            expected_source_ids=list(case.get("expected_source_ids") or []),
            expected_keywords=list(case.get("expected_keywords") or []),
        )
        scores.append(score)
        status = "OK" if score.source_hit and score.keyword_hit else "FAIL"
        print(
            f"[{status}] {score.case_id} source_hit={score.source_hit} "
            f"keyword_hit={score.keyword_hit} best={score.best_score} "
            f"matched={score.matched_source_ids}"
        )

    summary = aggregate_scores(scores)
    print(json.dumps(summary, indent=2))
    await engine.dispose()

    if summary["source_hit_rate"] < min_source_rate:
        print(
            f"FAIL threshold: source_hit_rate {summary['source_hit_rate']} "
            f"< {min_source_rate}"
        )
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate retrieve quality")
    parser.add_argument("--eval-file", type=Path, default=DEFAULT_EVAL)
    parser.add_argument("--min-source-rate", type=float, default=0.8)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args.eval_file, args.min_source_rate)))


if __name__ == "__main__":
    main()
