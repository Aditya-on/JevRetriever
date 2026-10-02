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
        """Create a Jev API client.

        Args:
            api_key: TypeSafe API key. If omitted, ``TYPESAFE_API_KEY``
                is read from the environment.
            model: Jev model to use.
            endpoint: TypeSafe System One endpoint.
            timeout: HTTP request timeout in seconds.
            session: Optional requests session, useful for testing.
        """

        self.api_key = api_key or os.getenv(
            "TYPESAFE_API_KEY"
        )

        if not self.api_key:
            raise ValueError(
                "A Jev API key is required. Pass jev_api_key=... "
                "or set TYPESAFE_API_KEY."
            )

        if not model or not model.strip():
            raise ValueError(
                "model must not be empty."
            )

        if not endpoint or not endpoint.strip():
            raise ValueError(
                "endpoint must not be empty."
            )

        if timeout <= 0:
            raise ValueError(
                "timeout must be greater than 0."
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
        """Send an evidence judgment request to TypeSafe Jev."""

        payload = {
            "model": self.model,
            "state": state,
            "questions": questions,
        }

        try:
            response = self.session.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout,
            )
        except requests.Timeout as exc:
            raise JevAPIError(
                f"Jev API request timed out after "
                f"{self.timeout:g} seconds."
            ) from exc
        except requests.RequestException as exc:
            raise JevAPIError(
                f"Jev API request failed: {exc}"
            ) from exc

        if not response.ok:
            raise JevAPIError(
                self._format_http_error(response)
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise JevAPIError(
                "Jev API returned invalid JSON."
            ) from exc

        if not isinstance(data, dict):
            raise JevAPIError(
                "Jev API returned an unexpected response format."
            )

        return data

    @staticmethod
    def _format_http_error(
        response: requests.Response,
    ) -> str:
        """Build a useful API error without exposing credentials."""

        status = response.status_code

        try:
            payload = response.json()
        except ValueError:
            payload = None

        if isinstance(payload, dict):
            error = payload.get("error")

            if isinstance(error, dict):
                message = (
                    error.get("message")
                    or error.get("detail")
                    or error.get("type")
                )

                if message:
                    return (
                        f"Jev API returned HTTP {status}: "
                        f"{message}"
                    )

            message = (
                payload.get("message")
                or payload.get("detail")
            )

            if message:
                return (
                    f"Jev API returned HTTP {status}: "
                    f"{message}"
                )

        text = response.text.strip()

        if text:
            return (
                f"Jev API returned HTTP {status}: "
                f"{text[:500]}"
            )

        return f"Jev API returned HTTP {status}."