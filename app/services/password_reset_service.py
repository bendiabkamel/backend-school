import os
import logging

import httpx


logger = logging.getLogger("albassir_api.password_reset")


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

    logger.info("Sending recovery email to %s using %s key with redirect_to=%s", email, key_source, redirect_to)

    response = httpx.post(
        f"{supabase_url}/auth/v1/recover",
        headers={
            "apikey": api_key,
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        params={"redirect_to": redirect_to},
        json={"email": email},
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
