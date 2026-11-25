import uuid

from app.api.schemas import ChatRequest


def test_session_id_empty_default():
    body = ChatRequest(message="hola")
    assert body.session_id == ""


def test_session_id_blank_normalized():
    body = ChatRequest(message="hola", session_id="   ")
    assert body.session_id == ""


def test_session_id_null_normalized():
    body = ChatRequest.model_validate({"message": "hola", "session_id": None})
    assert body.session_id == ""


def test_session_id_uuid_accepted():
    sid = str(uuid.uuid4())
    body = ChatRequest(message="hola", session_id=sid)
    assert body.session_id == sid
