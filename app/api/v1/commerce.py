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
    PromoteRequest,
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


# === Promote product (product → poster + post + story) ===


@router.post("/products/{product_id}/promote")
async def promote_product(
    product_id: uuid.UUID,
    body: PromoteRequest,
    user: User = Depends(RequirePermission("brands.write")),
    session: AsyncSession = Depends(get_session),
):
    """Generate poster + post + story for a product in one call.

    Runs CopywriterAgent, PosterAgent, and StoryAgent in parallel,
    creates a Post in DB, attaches the poster image, and auto-generates
    a product FAQ knowledge document.
    """
    import asyncio

    from app.agents.registry import get_orchestrator
    from app.core.exceptions import InvalidInputError
    from app.core.queue import enqueue
    from app.models.post import Post, PostAsset, PostStatus
    from app.services.brand_service import BrandService
    from app.services.knowledge_service import KnowledgeService

    # 1. Load product
    stmt = select(Product).where(
        Product.id == product_id,
        Product.tenant_id == user.tenant_id,
    )
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundError("Product not found")

    # 2. Build brief from product
    price_str = f"{product.price:,.0f}".replace(",", " ")
    brief = f"Promotion {product.name} a {price_str} {product.currency}."
    if product.description:
        brief += f" {product.description}"

    # 3. Get brand context
    brand_service = BrandService(session, tenant_id=user.tenant_id)
    try:
        brand_context = await brand_service.get_brand_with_profile(product.brand_id)
    except Exception:
        brand_context = {}

    # 4. Run agents in parallel
    orchestrator = get_orchestrator()
    tasks = {}

    # CopywriterAgent — generate post text
    tasks["copy"] = orchestrator.execute({
        "task_type": "generate_post",
        "brief": brief,
        "channel": body.channels[0] if body.channels else "facebook",
        "objective": "conversion",
        "brand_context": brand_context,
    })

    # PosterAgent — generate poster image
    if body.generate_poster:
        tasks["poster"] = orchestrator.execute({
            "task_type": "generate_poster",
            "brief": brief,
            "brand_context": brand_context,
            "aspect_ratio": "1:1",
        })

    # StoryAgent — plan story slides
    if body.generate_story:
        tasks["story"] = orchestrator.execute({
            "task_type": "generate_story",
            "brief": brief,
            "platform": "instagram",
            "brand_context": brand_context,
            "brand_id": str(product.brand_id),
            "tenant_id": str(user.tenant_id),
            "user_id": str(user.id),
        })

    results = await asyncio.gather(
        *tasks.values(),
        return_exceptions=True,
    )
    task_results = dict(zip(tasks.keys(), results))

    # 5. Extract copywriter result
    copy_result = task_results.get("copy")
    content_text = ""
    hashtags = []
    if not isinstance(copy_result, Exception) and copy_result.success:
        content_text = copy_result.output.get("content", brief)
        hashtags = copy_result.output.get("hashtags", [])
    else:
        content_text = brief  # Fallback to brief

    # 6. Create Post in DB
    target_channels = [{"channel": ch} for ch in body.channels]
    post = Post(
        tenant_id=user.tenant_id,
        brand_id=product.brand_id,
        created_by=user.id,
        content_text=content_text,
        hashtags=hashtags,
        target_channels=target_channels,
        status=PostStatus.DRAFT,
        ai_generated=True,
        generation_prompt=brief,
        metadata_={"product_id": str(product_id), "promotion": True},
    )
    session.add(post)
    await session.flush()

    # 7. Attach poster image if generated
    poster_url = None
    poster_result = task_results.get("poster")
    if poster_result and not isinstance(poster_result, Exception) and poster_result.success:
        poster_url = poster_result.output.get("image_url")
        if poster_url:
            asset = PostAsset(
                tenant_id=user.tenant_id,
                post_id=post.id,
                asset_type="image",
                file_url=poster_url,
                mime_type="image/png",
                ai_generated=True,
                generation_prompt=brief,
                metadata_={
                    "s3_key": poster_result.output.get("s3_key", ""),
                    "poster_plan": poster_result.output.get("poster_plan", {}),
                },
            )
            session.add(asset)

    # 8. Extract story plan
    story_plan = None
    story_result = task_results.get("story")
    if story_result and not isinstance(story_result, Exception) and story_result.success:
        story_plan = story_result.output.get("story_plan")

    # 9. Auto-generate product FAQ knowledge document
    faq_doc_id = await _create_product_faq(
        session=session,
        tenant_id=user.tenant_id,
        brand_id=product.brand_id,
        uploaded_by=user.id,
        product=product,
    )

    await session.commit()
    await session.refresh(post)

    # Enqueue FAQ ingestion
    if faq_doc_id:
        await enqueue("ingest_document", str(faq_doc_id), str(user.tenant_id))

    return {
        "post": {
            "id": str(post.id),
            "content_text": post.content_text,
            "hashtags": post.hashtags,
            "status": post.status.value if hasattr(post.status, "value") else post.status,
        },
        "poster_url": poster_url,
        "story_plan": story_plan,
        "product_faq_doc_id": str(faq_doc_id) if faq_doc_id else None,
    }


async def _create_product_faq(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    brand_id: uuid.UUID,
    uploaded_by: uuid.UUID,
    product: Product,
) -> uuid.UUID | None:
    """Auto-generate a FAQ knowledge document from a product."""
    from app.models.knowledge import KnowledgeDoc

    price_str = f"{product.price:,.0f}".replace(",", " ")
    stock_status = "en stock" if product.in_stock else "temporairement en rupture"
    available_text = "Oui" if product.in_stock else "Non"

    faq_content = (
        f"Q: Combien coute {product.name} ?\n"
        f"R: {product.name} coute {price_str} {product.currency}."
    )
    if product.description:
        faq_content += f" {product.description}"

    faq_content += (
        f"\n\nQ: Est-ce que {product.name} est disponible ?\n"
        f"R: {available_text}, {product.name} est {stock_status}."
    )

    if product.category:
        faq_content += (
            f"\n\nQ: Quelle est la categorie de {product.name} ?\n"
            f"R: {product.name} fait partie de la categorie {product.category}."
        )

    doc = KnowledgeDoc(
        tenant_id=tenant_id,
        brand_id=brand_id,
        title=f"FAQ - {product.name}",
        doc_type="product_faq",
        uploaded_by=uploaded_by,
        raw_content=faq_content,
        source_url=None,
        status="pending",
        language="fr",
        metadata_={"product_id": str(product.id), "auto_generated": True},
    )
    session.add(doc)
    await session.flush()
    return doc.id


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
