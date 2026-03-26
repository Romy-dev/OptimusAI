"""Pydantic schemas for commerce API."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# === Product schemas ===


class ProductCreate(BaseModel):
    brand_id: uuid.UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    price: float = Field(gt=0)
    currency: str = Field(default="XOF", max_length=10)
    category: str | None = Field(default=None, max_length=100)
    image_url: str | None = Field(default=None, max_length=500)
    in_stock: bool = True
    sku: str | None = Field(default=None, max_length=100)
    metadata_: dict = Field(default_factory=dict, alias="metadata")

    model_config = {"populate_by_name": True}


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    price: float | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, max_length=10)
    category: str | None = Field(default=None, max_length=100)
    image_url: str | None = Field(default=None, max_length=500)
    in_stock: bool | None = None
    sku: str | None = Field(default=None, max_length=100)
    metadata_: dict | None = Field(default=None, alias="metadata")

    model_config = {"populate_by_name": True}


class ProductResponse(BaseModel):
    id: uuid.UUID
    brand_id: uuid.UUID
    name: str
    description: str | None
    price: float
    currency: str
    category: str | None
    image_url: str | None
    in_stock: bool
    sku: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# === Promote schema ===


class PromoteRequest(BaseModel):
    channels: list[str] = Field(default=["facebook"])
    generate_story: bool = True
    generate_poster: bool = True
    language: str = "fr"


# === Order schemas ===


class OrderItem(BaseModel):
    product_id: uuid.UUID | None = None
    name: str
    qty: int = Field(ge=1)
    price: float = Field(ge=0)


class OrderResponse(BaseModel):
    id: uuid.UUID
    brand_id: uuid.UUID
    customer_phone: str
    customer_name: str | None
    items: list[dict]
    total_amount: float
    currency: str
    status: str
    payment_method: str | None
    payment_screenshot_url: str | None
    payment_verified: bool
    delivery_address: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderStatusUpdate(BaseModel):
    status: str = Field(
        pattern="^(pending|confirmed|paid|shipped|delivered|cancelled)$"
    )
    notes: str | None = None


class PaymentVerification(BaseModel):
    verified: bool
    notes: str | None = None


# === Stats schema ===


class CommerceStats(BaseModel):
    total_revenue: float
    orders_count: int
    avg_order_value: float
    orders_by_status: dict[str, int]
    top_products: list[dict]
    payment_methods_breakdown: dict[str, int]
