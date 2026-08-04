from __future__ import annotations

import os
from typing import Any

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def resolve_api_key(streamlit_secrets: Any = None) -> str | None:
    """Resolve the key without logging or returning it to the UI."""
    env_key = os.getenv("VNSTOCK_API_KEY", "").strip()
    if env_key:
        return env_key
    if streamlit_secrets is not None:
        try:
            value = streamlit_secrets.get("VNSTOCK_API_KEY", "")
            return str(value).strip() or None
        except Exception:
            return None
    return None


def _field(status: Any, *names: str):
    for name in names:
        if isinstance(status, dict) and name in status:
            return status[name]
        if hasattr(status, name):
            return getattr(status, name)
    return None


def _flatten_status(value: Any, prefix: str = "") -> dict[str, Any]:
    """Flatten public status metadata while excluding anything secret-like."""
    out: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, item in value.items():
            name = f"{prefix}.{key}" if prefix else str(key)
            lowered = name.lower()
            if any(word in lowered for word in ("api_key", "apikey", "token", "secret", "credential")):
                continue
            out.update(_flatten_status(item, name))
    elif isinstance(value, (list, tuple)):
        for idx, item in enumerate(value):
            out.update(_flatten_status(item, f"{prefix}.{idx}"))
    elif value is None or isinstance(value, (str, int, float, bool)):
        out[prefix or "status"] = value
    return out


def _identity_metadata(status: Any) -> tuple[str | None, str | None, Any]:
    flat = _flatten_status(status)
    plan = None
    membership = None
    limit = None
    preferred_membership_terms = ("sponsor", "bronze", "silver", "gold", "platinum", "insider")
    for key, value in flat.items():
        key_l = key.lower(); value_s = str(value).strip()
        if not value_s or value_s.lower() in {"none", "null"}: continue
        if limit is None and any(term in key_l for term in ("rate_limit", "request_limit", "requests_per_minute", "limit")):
            limit = value
        if plan is None and any(term in key_l for term in ("tier", "plan", "package")):
            plan = value_s
        if any(term in key_l for term in ("membership", "member", "sponsor", "badge", "level")):
            membership = value_s
        if any(term in value_s.lower() for term in preferred_membership_terms):
            membership = value_s
    return membership, plan, limit


def configure_vnstock_auth(api_key: str | None = None) -> dict:
    """Register a supplied key or detect an existing local registration.

    No secret value is included in the returned object.
    """
    result = {"available": False, "authenticated": False, "tier": "Unknown", "membership": None, "reported_plan": None, "limit": None, "message": "Vnstock is not available"}
    try:
        from vnstock.core.utils.auth import change_api_key, check_status
        result["available"] = True
        if api_key:
            change_api_key(api_key)
        status = check_status()
        membership, plan, limit = _identity_metadata(status)
        display_tier = membership or plan or ("Registered" if api_key else "Guest")
        result.update({
            "authenticated": bool(api_key),
            "tier": str(display_tier),
            "membership": membership,
            "reported_plan": plan,
            "limit": limit,
            "message": "API key accepted and status checked" if api_key else "No API key supplied to this runtime",
        })
    except ImportError:
        result["message"] = "Install vnstock>=3.5.1 to enable authentication"
    except Exception as exc:
        # Keep the message useful without ever including the key.
        result.update({"available": True, "message": f"Authentication check failed: {type(exc).__name__}"})
    return result
