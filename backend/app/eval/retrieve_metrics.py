from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import SearchHit


@dataclass(frozen=True, slots=True)
class RetrieveCaseScore:
    case_id: str
    source_hit: bool
    keyword_hit: bool
    best_score: float | None
    matched_source_ids: list[str]


def score_retrieve_case(
    *,
    case_id: str,
    hits: list[SearchHit],
    expected_source_ids: list[str],
    expected_keywords: list[str],
) -> RetrieveCaseScore:
    source_ids = [h.chunk.source_id for h in hits]
    expected = {s.lower() for s in expected_source_ids}
    matched = [s for s in source_ids if s.lower() in expected]
    source_hit = bool(matched)

    blob = " ".join(h.chunk.content.lower() for h in hits)
    keyword_hit = all(kw.lower() in blob for kw in expected_keywords) if expected_keywords else True

    best = max((h.score for h in hits), default=None)
    return RetrieveCaseScore(
        case_id=case_id,
        source_hit=source_hit,
        keyword_hit=keyword_hit,
        best_score=best,
        matched_source_ids=matched,
    )


def aggregate_scores(scores: list[RetrieveCaseScore]) -> dict:
    n = len(scores) or 1
    source_rate = sum(1 for s in scores if s.source_hit) / n
    keyword_rate = sum(1 for s in scores if s.keyword_hit) / n
    both = sum(1 for s in scores if s.source_hit and s.keyword_hit) / n
    return {
        "cases": len(scores),
        "source_hit_rate": round(source_rate, 4),
        "keyword_hit_rate": round(keyword_rate, 4),
        "both_rate": round(both, 4),
    }
