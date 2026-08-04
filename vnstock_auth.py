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


def configure_vnstock_auth(api_key: str | None = None) -> dict:
    """Register a supplied key or detect an existing local registration.

    No secret value is included in the returned object.
    """
    result = {"available": False, "authenticated": False, "tier": "Unknown", "limit": None, "message": "Vnstock is not available"}
    try:
        from vnstock.core.utils.auth import change_api_key, check_status
        result["available"] = True
        if api_key:
            change_api_key(api_key)
        status = check_status()
        tier = _field(status, "tier", "membership_tier", "plan")
        limit = _field(status, "limit", "rate_limit", "requests_per_minute")
        result.update({
            "authenticated": bool(api_key) or bool(tier),
            "tier": str(tier or ("Registered" if api_key else "Guest")),
            "limit": limit,
            "message": "API key configured" if api_key else "Using locally registered Vnstock identity",
        })
    except ImportError:
        result["message"] = "Install vnstock>=3.5.1 to enable authentication"
    except Exception as exc:
        # Keep the message useful without ever including the key.
        result.update({"available": True, "message": f"Authentication check failed: {type(exc).__name__}"})
    return result
