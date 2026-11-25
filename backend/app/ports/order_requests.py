from __future__ import annotations

from typing import Protocol

from app.domain.orders import OrderRequest


class OrderRequestPort(Protocol):
    """Persistencia de solicitudes de pedido (draft → submitted)."""

    async def ensure_schema(self) -> None: ...

    async def get_or_create_draft(self, session_id: str) -> OrderRequest: ...

    async def save(self, order: OrderRequest) -> OrderRequest: ...

    async def get(self, order_id: str) -> OrderRequest | None: ...
