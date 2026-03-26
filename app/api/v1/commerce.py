"""Commerce API — products, orders, payment verification, and stats."""

import uuid
from collections import Counter
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_session
from app.core.exceptions import NotFoundError
from app.core.permissions import RequirePermission
from app.models.commerce import LoyaltyPoints, Order, OrderStatus, Product
from app.models.user import User
from app.schemas.commerce import (
    CommerceStats,
    OrderResponse,
    OrderStatusUpdate,
    PaymentVerification,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)

router = APIRouter(prefix="/commerce", tags=["commerce"])


# === Products ===


@router.get("/products", response_model=list[ProductResponse])
async def list_products(
    brand_id: uuid.UUID | None = None,
    category: str | None = None,
    search: str | None = None,
    in_stock: bool | None = None,
    user: User = Depends(RequirePermission("brands.read")),
    session: AsyncSession = Depends(get_session),
):
    """List products for a brand with optional search, category, and stock filters."""
    stmt = select(Product).where(Product.tenant_id == user.tenant_id)

    if brand_id:
        stmt = stmt.where(Product.brand_id == brand_id)
    if category:
        stmt = stmt.where(Product.category == category)
    if in_stock is not None:
        stmt = stmt.where(Product.in_stock == in_stock)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            Product.name.ilike(pattern) | Product.description.ilike(pattern)
        )

    stmt = stmt.order_by(Product.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.post("/products", response_model=ProductResponse, status_code=201)
async def create_product(
    body: ProductCreate,
    user: User = Depends(RequirePermission("brands.write")),
    session: AsyncSession = Depends(get_session),
):
    """Create a new product in the catalog."""
    product = Product(
        tenant_id=user.tenant_id,
        brand_id=body.brand_id,
        name=body.name,
        description=body.description,
        price=body.price,
        currency=body.currency,
        category=body.category,
        image_url=body.image_url,
        in_stock=body.in_stock,
        sku=body.sku,
        metadata_=body.metadata_,
    )
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return product


@router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: uuid.UUID,
    body: ProductUpdate,
    user: User = Depends(RequirePermission("brands.write")),
    session: AsyncSession = Depends(get_session),
):
    """Update an existing product."""
    stmt = select(Product).where(
        Product.id == product_id,
        Product.tenant_id == user.tenant_id,
    )
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()

    if not product:
        raise NotFoundError("Product not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    await session.commit()
    await session.refresh(product)
    return product


@router.delete("/products/{product_id}", status_code=204)
async def delete_product(
    product_id: uuid.UUID,
    user: User = Depends(RequirePermission("brands.write")),
    session: AsyncSession = Depends(get_session),
):
    """Delete a product from the catalog."""
    stmt = select(Product).where(
        Product.id == product_id,
        Product.tenant_id == user.tenant_id,
    )
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()

    if not product:
        raise NotFoundError("Product not found")

    await session.delete(product)
    await session.commit()


# === Orders ===


@router.get("/orders", response_model=list[OrderResponse])
async def list_orders(
    brand_id: uuid.UUID | None = None,
    status: str | None = None,
    customer_phone: str | None = None,
    limit: int = Query(default=50, le=200),
    user: User = Depends(RequirePermission("brands.read")),
    session: AsyncSession = Depends(get_session),
):
    """List orders with optional status and brand filters."""
    stmt = select(Order).where(Order.tenant_id == user.tenant_id)

    if brand_id:
        stmt = stmt.where(Order.brand_id == brand_id)
    if status:
        stmt = stmt.where(Order.status == status)
    if customer_phone:
        stmt = stmt.where(Order.customer_phone == customer_phone)

    stmt = stmt.order_by(Order.created_at.desc()).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.put("/orders/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: uuid.UUID,
    body: OrderStatusUpdate,
    user: User = Depends(RequirePermission("brands.write")),
    session: AsyncSession = Depends(get_session),
):
    """Update order status (e.g., confirm, ship, deliver, cancel)."""
    stmt = select(Order).where(
        Order.id == order_id,
        Order.tenant_id == user.tenant_id,
    )
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise NotFoundError("Order not found")

    order.status = body.status
    if body.notes:
        order.notes = body.notes

    # If marked as paid, update payment verification
    if body.status == OrderStatus.PAID.value:
        order.payment_verified = True

    await session.commit()
    await session.refresh(order)
    return order


@router.post("/orders/{order_id}/verify-payment", response_model=OrderResponse)
async def verify_payment(
    order_id: uuid.UUID,
    body: PaymentVerification,
    user: User = Depends(RequirePermission("brands.write")),
    session: AsyncSession = Depends(get_session),
):
    """Manually verify a payment for an order."""
    stmt = select(Order).where(
        Order.id == order_id,
        Order.tenant_id == user.tenant_id,
    )
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise NotFoundError("Order not found")

    order.payment_verified = body.verified
    if body.verified and order.status == OrderStatus.PENDING.value:
        order.status = OrderStatus.PAID.value
    if body.notes:
        order.notes = body.notes

    # Award loyalty points on verified payment
    if body.verified:
        await _award_loyalty_points(
            session,
            tenant_id=user.tenant_id,
            customer_phone=order.customer_phone,
            order_total=float(order.total_amount),
        )

    await session.commit()
    await session.refresh(order)
    return order


# === Stats ===


@router.get("/stats", response_model=CommerceStats)
async def commerce_stats(
    brand_id: uuid.UUID | None = None,
    user: User = Depends(RequirePermission("brands.read")),
    session: AsyncSession = Depends(get_session),
):
    """Get commerce statistics: revenue, order counts, averages, top products."""
    base_filter = [Order.tenant_id == user.tenant_id]
    if brand_id:
        base_filter.append(Order.brand_id == brand_id)

    # Total revenue (only paid/shipped/delivered orders)
    paid_statuses = [
        OrderStatus.PAID.value,
        OrderStatus.SHIPPED.value,
        OrderStatus.DELIVERED.value,
    ]
    revenue_stmt = select(
        func.coalesce(func.sum(Order.total_amount), 0),
        func.count(Order.id),
    ).where(*base_filter, Order.status.in_(paid_statuses))

    revenue_result = await session.execute(revenue_stmt)
    row = revenue_result.one()
    total_revenue = float(row[0])
    paid_count = row[1]

    # All orders count
    all_count_stmt = select(func.count(Order.id)).where(*base_filter)
    all_count_result = await session.execute(all_count_stmt)
    orders_count = all_count_result.scalar() or 0

    avg_order_value = total_revenue / paid_count if paid_count > 0 else 0.0

    # Orders by status
    status_stmt = (
        select(Order.status, func.count(Order.id))
        .where(*base_filter)
        .group_by(Order.status)
    )
    status_result = await session.execute(status_stmt)
    orders_by_status = {row[0]: row[1] for row in status_result.all()}

    # Top products (from order items JSONB)
    orders_stmt = select(Order.items).where(
        *base_filter, Order.status.in_(paid_statuses)
    )
    orders_result = await session.execute(orders_stmt)
    product_counter: Counter = Counter()
    for (items,) in orders_result.all():
        if isinstance(items, list):
            for item in items:
                name = item.get("name", "Unknown")
                qty = item.get("qty", 1)
                product_counter[name] += qty

    top_products = [
        {"name": name, "quantity_sold": qty}
        for name, qty in product_counter.most_common(10)
    ]

    # Payment methods breakdown
    pm_stmt = (
        select(Order.payment_method, func.count(Order.id))
        .where(*base_filter, Order.payment_method.isnot(None))
        .group_by(Order.payment_method)
    )
    pm_result = await session.execute(pm_stmt)
    payment_methods_breakdown = {row[0]: row[1] for row in pm_result.all()}

    return CommerceStats(
        total_revenue=total_revenue,
        orders_count=orders_count,
        avg_order_value=round(avg_order_value, 2),
        orders_by_status=orders_by_status,
        top_products=top_products,
        payment_methods_breakdown=payment_methods_breakdown,
    )


# === Helpers ===


async def _award_loyalty_points(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    customer_phone: str,
    order_total: float,
):
    """Award loyalty points: 1 point per 1000 XOF spent."""
    points_earned = int(order_total // 1000)
    if points_earned <= 0:
        return

    stmt = select(LoyaltyPoints).where(
        LoyaltyPoints.tenant_id == tenant_id,
        LoyaltyPoints.customer_phone == customer_phone,
    )
    result = await session.execute(stmt)
    loyalty = result.scalar_one_or_none()

    if loyalty:
        loyalty.points_balance += points_earned
        loyalty.total_earned += points_earned
        loyalty.last_purchase_at = datetime.now(timezone.utc)
    else:
        loyalty = LoyaltyPoints(
            tenant_id=tenant_id,
            customer_phone=customer_phone,
            points_balance=points_earned,
            total_earned=points_earned,
            last_purchase_at=datetime.now(timezone.utc),
        )
        session.add(loyalty)

    await session.flush()
