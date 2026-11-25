from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.domain.orders import OrderRequest


def _row_to_order(row) -> OrderRequest:
    return OrderRequest(
        id=str(row.id),
        session_id=str(row.session_id),
        item_description=row.item_description,
        desired_when=row.desired_when,
        contact_phone=row.contact_phone,
        status=row.status,  # type: ignore[arg-type]
        requested_at=row.requested_at,
        submitted_at=row.submitted_at,
    )


class PostgresOrderRequests:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine
        self._sessions = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

    async def ensure_schema(self) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS order_requests (
                        id UUID PRIMARY KEY,
                        session_id UUID NOT NULL
                            REFERENCES chat_sessions(id) ON DELETE CASCADE,
                        item_description TEXT NULL,
                        desired_when TEXT NULL,
                        contact_phone TEXT NULL,
                        status TEXT NOT NULL DEFAULT 'draft'
                            CHECK (status IN ('draft', 'submitted')),
                        requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        submitted_at TIMESTAMPTZ NULL,
                        metadata JSONB NOT NULL DEFAULT '{}'::jsonb
                    )
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS order_requests_session_idx
                    ON order_requests (session_id, status, requested_at DESC)
                    """
                )
            )

    async def get_or_create_draft(self, session_id: str) -> OrderRequest:
        async with self._sessions() as session:
            async with session.begin():
                result = await session.execute(
                    text(
                        """
                        SELECT id, session_id, item_description, desired_when,
                               contact_phone, status, requested_at, submitted_at
                        FROM order_requests
                        WHERE session_id = :session_id AND status = 'draft'
                        ORDER BY requested_at DESC
                        LIMIT 1
                        """
                    ),
                    {"session_id": session_id},
                )
                row = result.first()
                if row is not None:
                    return _row_to_order(row)

                order_id = str(uuid.uuid4())
                now = datetime.now(timezone.utc)
                await session.execute(
                    text(
                        """
                        INSERT INTO order_requests (
                            id, session_id, status, requested_at
                        ) VALUES (
                            :id, :session_id, 'draft', :requested_at
                        )
                        """
                    ),
                    {
                        "id": order_id,
                        "session_id": session_id,
                        "requested_at": now,
                    },
                )
                return OrderRequest(
                    id=order_id,
                    session_id=session_id,
                    item_description=None,
                    desired_when=None,
                    contact_phone=None,
                    status="draft",
                    requested_at=now,
                    submitted_at=None,
                )

    async def save(self, order: OrderRequest) -> OrderRequest:
        async with self._sessions() as session:
            async with session.begin():
                await session.execute(
                    text(
                        """
                        UPDATE order_requests SET
                            item_description = :item_description,
                            desired_when = :desired_when,
                            contact_phone = :contact_phone,
                            status = :status,
                            submitted_at = :submitted_at
                        WHERE id = :id
                        """
                    ),
                    {
                        "id": order.id,
                        "item_description": order.item_description,
                        "desired_when": order.desired_when,
                        "contact_phone": order.contact_phone,
                        "status": order.status,
                        "submitted_at": order.submitted_at,
                    },
                )
        return order

    async def get(self, order_id: str) -> OrderRequest | None:
        async with self._sessions() as session:
            result = await session.execute(
                text(
                    """
                    SELECT id, session_id, item_description, desired_when,
                           contact_phone, status, requested_at, submitted_at
                    FROM order_requests
                    WHERE id = :id
                    """
                ),
                {"id": order_id},
            )
            row = result.first()
            return _row_to_order(row) if row is not None else None
