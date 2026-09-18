from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class StockEntry(BaseModel):
    branch: str
    city: Optional[str] = None
    quantity: Optional[int] = None
    available: Optional[bool] = None


class Product(BaseModel):
    pharmacy: str
    name: str
    price: float = Field(ge=0)
    url: str
    regular_price: Optional[float] = None
    active_ingredient: Optional[str] = None
    concentration: Optional[str] = None
    presentation: Optional[str] = None
    quantity: Optional[int] = None
    available: Optional[bool] = None
    stock: Optional[int] = None
    branch: Optional[str] = None
    city: Optional[str] = None
    unit_price: Optional[float] = None
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    stocks: list[StockEntry] = Field(default_factory=list)

    @property
    def savings(self) -> Optional[float]:
        if self.regular_price is None or self.regular_price <= self.price:
            return None
        return round(self.regular_price - self.price, 2)
