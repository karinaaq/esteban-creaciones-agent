from datetime import datetime, timezone

from app.domain.orders import OrderRequest


def test_missing_and_complete():
    order = OrderRequest(
        id="1",
        session_id="s",
        item_description="carpeta",
        desired_when=None,
        contact_phone=None,
        status="draft",
        requested_at=datetime.now(timezone.utc),
    )
    assert order.missing_fields() == ("desired_when", "contact_phone")
    assert not order.is_complete

    full = order.with_updates(desired_when="mañana", contact_phone="099")
    assert full.is_complete
    assert full.missing_fields() == ()
