"""Alzheimer backend adapter for xiaogpt.

This adapter forwards text and intent data from xiaogpt to the Alzheimer backend
via its /api/voice/webhook endpoint.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import aiohttp
from aiohttp import ClientSession, ClientTimeout

logger = logging.getLogger(__name__)


class AlzheimerAdapter:
    """Adapter for forwarding xiaogpt data to Alzheimer backend."""

    def __init__(
        self,
        base_url: str | None = None,
        api_token: str | None = None,
        session: ClientSession | None = None,
    ):
        """Initialize the Alzheimer adapter.

        Args:
            base_url: Base URL for the Alzheimer backend API.
                     Defaults to ALZ_BASE_URL environment variable.
            api_token: Optional API token for authentication.
                      Defaults to ALZ_API_TOKEN environment variable.
            session: Optional aiohttp ClientSession to reuse.
                    If not provided, a new session will be created per request.
        """
        self.base_url = base_url or os.getenv("ALZ_BASE_URL", "")
        self.api_token = api_token or os.getenv("ALZ_API_TOKEN", "")
        self.enabled = bool(self.base_url)
        self._session = session
        
        if self.enabled:
            logger.info(f"Alzheimer adapter enabled with base_url: {self.base_url}")
        else:
            logger.debug("Alzheimer adapter disabled (no base_url configured)")

    async def forward_text_as_intent(
        self,
        text: str,
        device_id: str,
        user_id: str | None = None,
        intent: str | None = None,
        slots: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Forward text as intent to the Alzheimer backend.

        Args:
            text: The text content to forward
            device_id: The device ID (e.g., from xiaomi speaker)
            user_id: Optional user ID
            intent: Optional intent type
            slots: Optional intent slots/parameters

        Returns:
            Response from the Alzheimer backend as a dict, or None if disabled/failed
        """
        if not self.enabled:
            logger.debug("Alzheimer adapter not enabled, skipping forward")
            return None

        webhook_url = f"{self.base_url.rstrip('/')}/api/voice/webhook"
        
        payload = {
            "text": text,
            "device_id": device_id,
        }
        
        if user_id:
            payload["user_id"] = user_id
        if intent:
            payload["intent"] = intent
        if slots:
            payload["slots"] = slots

        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        try:
            timeout = ClientTimeout(total=10)
            # Use provided session or create a new one
            if self._session:
                async with self._session.post(
                    webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=timeout,
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    logger.info(
                        f"Successfully forwarded to Alzheimer backend: {text[:50]}..."
                    )
                    return result
            else:
                async with ClientSession() as session:
                    async with session.post(
                        webhook_url,
                        json=payload,
                        headers=headers,
                        timeout=timeout,
                    ) as response:
                        response.raise_for_status()
                        result = await response.json()
                        logger.info(
                            f"Successfully forwarded to Alzheimer backend: {text[:50]}..."
                        )
                        return result
        except aiohttp.ClientError as e:
            logger.warning(
                f"Failed to forward to Alzheimer backend (client error): {str(e)}"
            )
            return None
        except Exception as e:
            logger.warning(
                f"Failed to forward to Alzheimer backend (unexpected error): {str(e)}",
                exc_info=True
            )
            return None
