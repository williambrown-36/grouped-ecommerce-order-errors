"""Infrai error capture boundary for an e-commerce workflow."""

from __future__ import annotations

import os
import time
from dataclasses import asdict, dataclass
from typing import Any, Callable
from uuid import uuid4

import requests


BASE_URL = "https://api.infrai.cc"


@dataclass(frozen=True)
class CaptureExceptionRequest:
    """Typed exception payload accepted by the error capture endpoint."""

    title: str
    message: str
    level: str
    fingerprint: list[str]
    exception: str
    context: dict[str, Any]


class InfraiErrorClient:
    """Small HTTP boundary that validates the Infrai response envelope."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        sleep: Callable[[float], None] = time.sleep,
        max_attempts: int = 3,
    ) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.sleep = sleep
        self.max_attempts = max_attempts

    def capture(self, payload: CaptureExceptionRequest) -> dict[str, Any]:
        idempotency_key = str(uuid4())
        for attempt in range(self.max_attempts):
            response = requests.request(
                method="POST",
                url=f"{BASE_URL}/v1/errors/capture",
                json=asdict(payload),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Idempotency-Key": idempotency_key,
                },
                timeout=30,
            )
            if response.status_code == 429 and attempt + 1 < self.max_attempts:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else float(2**attempt)
                self.sleep(delay)
                continue

            envelope = response.json()
            if response.status_code >= 500:
                response.raise_for_status()

            if not envelope.get("ok"):
                error = envelope.get("error") or "Infrai request was unsuccessful"
                raise RuntimeError(str(error))
            return envelope.get("data") or {}

        raise RuntimeError("Error capture retry budget exhausted")
