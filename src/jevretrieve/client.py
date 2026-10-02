"""Small TypeSafe Jev API client."""

from __future__ import annotations

import os
from typing import Any

import requests


class JevAPIError(RuntimeError):
    """Raised when the Jev API cannot produce a judgment."""


class JevClient:
    """Client for the TypeSafe Jev System One endpoint."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        model: str = "jev-latest",
        endpoint: str = "https://api.typesafe.ai/v1/systemone",
        timeout: float = 60.0,
        session: requests.Session | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("TYPESAFE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "A Jev API key is required. Pass jev_api_key=... "
                "or set TYPESAFE_API_KEY."
            )
        self.model = model
        self.endpoint = endpoint
        self.timeout = timeout
        self.session = session or requests.Session()

    def judge(
        self,
        *,
        state: dict[str, Any],
        questions: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "state": state,
            "questions": questions,
        }

        response = self.session.post(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.timeout,
        )

        if not response.ok:
            raise JevAPIError(
                f"Jev API returned HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise JevAPIError("Jev API returned invalid JSON.") from exc
