import os
import logging
from urllib.parse import urlparse

import httpx


logger = logging.getLogger("albassir_api.password_reset")

LOCAL_HOSTNAMES = {"localhost", "127.0.0.1", "0.0.0.0"}


def _validate_redirect_to(redirect_to: str) -> str:
    normalized_redirect = (redirect_to or "").strip()
    parsed = urlparse(normalized_redirect)

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError(f"Invalid redirect_to URL: {normalized_redirect}")

    is_production = os.getenv("ENVIRONMENT", "").strip().lower() == "production"
    if is_production and parsed.hostname in LOCAL_HOSTNAMES:
        raise RuntimeError(
            f"Invalid redirect_to URL for production (local host not allowed): {normalized_redirect}"
        )

    return normalized_redirect


def send_password_recovery_email(email: str, redirect_to: str) -> None:
    """Send a Supabase recovery email with an explicit redirect target."""
    supabase_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    anon_key = os.getenv("SUPABASE_KEY", "").strip()
    api_key = anon_key or service_role_key
    key_source = "anon" if anon_key else "service_role"

    if not supabase_url:
        raise RuntimeError("SUPABASE_URL is not configured")
    if not api_key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY is not configured")

    safe_redirect_to = _validate_redirect_to(redirect_to)

    logger.info("Sending recovery email to %s using %s key with redirect_to=%s", email, key_source, safe_redirect_to)

    response = httpx.post(
        f"{supabase_url}/auth/v1/recover",
        headers={
            "apikey": api_key,
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        params={"redirect_to": safe_redirect_to},
        json={"email": email, "redirect_to": safe_redirect_to},
        timeout=20.0,
    )

    if response.status_code >= 400:
        message = response.text
        logger.error(
            "Supabase recover failed status=%s email=%s body=%s",
            response.status_code,
            email,
            message,
        )
        response.raise_for_status()
