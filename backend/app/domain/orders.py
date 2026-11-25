from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Literal

OrderStatus = Literal["draft", "submitted"]


@dataclass(frozen=True, slots=True)
class OrderRequest:
    """Solicitud de pedido (borrador o enviada)."""

    id: str
    session_id: str
    item_description: str | None
    desired_when: str | None
    contact_phone: str | None
    status: OrderStatus
    requested_at: datetime | None = None
    submitted_at: datetime | None = None

    def with_updates(
        self,
        *,
        item_description: str | None = None,
        desired_when: str | None = None,
        contact_phone: str | None = None,
        status: OrderStatus | None = None,
        submitted_at: datetime | None = None,
    ) -> OrderRequest:
        return replace(
            self,
            item_description=(
                item_description
                if item_description is not None
                else self.item_description
            ),
            desired_when=(
                desired_when if desired_when is not None else self.desired_when
            ),
            contact_phone=(
                contact_phone if contact_phone is not None else self.contact_phone
            ),
            status=status if status is not None else self.status,
            submitted_at=(
                submitted_at if submitted_at is not None else self.submitted_at
            ),
        )

    @property
    def is_complete(self) -> bool:
        return bool(
            (self.item_description or "").strip()
            and (self.desired_when or "").strip()
            and (self.contact_phone or "").strip()
        )

    def missing_fields(self) -> tuple[str, ...]:
        missing: list[str] = []
        if not (self.item_description or "").strip():
            missing.append("item_description")
        if not (self.desired_when or "").strip():
            missing.append("desired_when")
        if not (self.contact_phone or "").strip():
            missing.append("contact_phone")
        return tuple(missing)
