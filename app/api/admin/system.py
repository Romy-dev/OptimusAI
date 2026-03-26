"""Admin system — logs, queue, websockets, storage."""

from fastapi import APIRouter, Depends

from app.core.admin_auth import require_superadmin
from app.models.user import User

router = APIRouter(prefix="/system")


@router.get("/websockets")
async def active_websockets(
    user: User = Depends(require_superadmin),
):
    """List active WebSocket connections."""
    from app.core.websocket import ws_manager

    connections = {}
    for tenant_id, users in ws_manager._connections.items():
        for user_id, sockets in users.items():
            connections.setdefault(tenant_id, []).append({
                "user_id": user_id,
                "active_sockets": len(sockets),
            })

    return {
        "total_connections": sum(
            len(s) for u in ws_manager._connections.values() for s in u.values()
        ),
        "by_tenant": connections,
    }


@router.get("/queue")
async def queue_status(
    user: User = Depends(require_superadmin),
):
    """Get ARQ queue status."""
    from app.core.redis import get_redis

    redis = await get_redis()

    # ARQ stores jobs in redis with prefix arq:
    keys = []
    async for key in redis.scan_iter("arq:job:*"):
        keys.append(key)

    pending = len(keys)

    # Get results
    result_keys = []
    async for key in redis.scan_iter("arq:result:*"):
        result_keys.append(key)

    return {
        "pending_jobs": pending,
        "completed_results": len(result_keys),
    }


@router.get("/storage")
async def storage_stats(
    user: User = Depends(require_superadmin),
):
    """Get MinIO/S3 storage statistics."""
    from app.core.storage import storage_service

    try:
        client = storage_service.client
        paginator = client.get_paginator("list_objects_v2")
        total_size = 0
        total_objects = 0

        for page in paginator.paginate(Bucket=storage_service.bucket):
            for obj in page.get("Contents", []):
                total_size += obj["Size"]
                total_objects += 1

        return {
            "bucket": storage_service.bucket,
            "total_objects": total_objects,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "status": "ok",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}
