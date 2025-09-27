from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Booking, Payment, PaymentProvider, PaymentStatus


class PaymentService:
    """Records mock payment transactions for demo flows."""

    def __init__(self, provider: PaymentProvider = PaymentProvider.MCP_SANDBOX) -> None:
        self.provider = provider

    async def record_payment(
        self,
        session: AsyncSession,
        booking: Booking,
        amount: Optional[Decimal] = None,
        currency: str = "USD",
        metadata: Optional[Dict[str, Any]] = None,
        status: PaymentStatus = PaymentStatus.SUCCEEDED,
    ) -> Payment:
        payment = Payment(
            booking=booking,
            provider=self.provider,
            status=status,
            amount=amount,
            currency=currency,
            extras=metadata or {},
        )
        session.add(payment)
        await session.flush()
        return payment


def get_payment_service() -> PaymentService:
    return PaymentService()
