"""Stable response envelope helpers for incident API endpoints."""
from datetime import datetime, timezone

def success(data=None, message=None, meta=None):
    payload = {"ok": True, "data": data if data is not None else {},
               "generated_at": datetime.now(timezone.utc).isoformat()}
    if message:
        payload["message"] = message
    if meta:
        payload["meta"] = meta
    return payload

def failure(message, code="invalid_request", details=None):
    payload = {"ok": False, "error": {"code": code, "message": str(message)}}
    if details:
        payload["error"]["details"] = details
    return payload

def pagination_meta(page, per_page, total):
    pages = (total + per_page - 1) // per_page if per_page else 0
    return {"page": page, "per_page": per_page, "total": total, "pages": pages,
            "has_previous": page > 1, "has_next": page < pages}

def safe_integer(value, default=0, minimum=0, maximum=1000000):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))
