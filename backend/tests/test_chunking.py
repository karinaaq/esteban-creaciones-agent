from app.domain.chunking import chunk_documents, split_text
from app.domain.models import DocumentSource


def test_split_respects_size_and_overlap():
    text = ("palabra " * 80).strip()
    chunks = split_text(text, chunk_size=50, overlap=10)
    assert len(chunks) > 1
    assert all(len(c) <= 50 for c in chunks)
    # overlap: fin de uno aparece al inicio del siguiente (aprox)
    assert chunks[0][-5:] in chunks[1] or any(
        token in chunks[1] for token in chunks[0].split()[-2:]
    )


def test_chunk_documents_assigns_ids():
    docs = [
        DocumentSource(
            source_id="plazos",
            title="Plazos",
            text="A" * 30 + "\n\n" + "B" * 30 + "\n\n" + "C" * 30,
        )
    ]
    chunks = chunk_documents(docs, chunk_size=40, overlap=5)
    assert len(chunks) >= 2
    assert chunks[0].source_id == "plazos"
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1
