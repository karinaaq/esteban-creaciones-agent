from app.domain.models import DocumentChunk, SearchHit
from app.eval.retrieve_metrics import aggregate_scores, score_retrieve_case


def _hit(source_id: str, content: str, score: float = 0.8) -> SearchHit:
    return SearchHit(
        chunk=DocumentChunk(
            chunk_id="x",
            source_id=source_id,
            title=source_id,
            content=content,
            chunk_index=0,
        ),
        score=score,
    )


def test_score_retrieve_case_success():
    score = score_retrieve_case(
        case_id="c1",
        hits=[_hit("plazos", "Los centros de mesa tardan 10 dias")],
        expected_source_ids=["plazos"],
        expected_keywords=["10", "centro"],
    )
    assert score.source_hit is True
    assert score.keyword_hit is True


def test_aggregate_scores():
    s1 = score_retrieve_case(
        case_id="a",
        hits=[_hit("plazos", "10 dias centro")],
        expected_source_ids=["plazos"],
        expected_keywords=["10"],
    )
    s2 = score_retrieve_case(
        case_id="b",
        hits=[_hit("otros", "nada")],
        expected_source_ids=["plazos"],
        expected_keywords=["10"],
    )
    summary = aggregate_scores([s1, s2])
    assert summary["cases"] == 2
    assert summary["source_hit_rate"] == 0.5
