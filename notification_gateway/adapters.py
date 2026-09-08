"""Local authenticated producer and non-sending fixture adapters."""

from __future__ import annotations

from typing import Any, Mapping

from .gateway import Gateway, TransportOutcome
from .report import DeliveryReceipt


class LocalProducer:
    """A bounded local adapter; deployment wiring supplies its auth separately."""

    def __init__(self, gateway: Gateway, name: str = "dashboard", auth: str | None = None):
        self.gateway, self.name, self.auth = gateway, name, auth

    def submit(self, event: Mapping[str, Any]) -> str:
        if event.get("producer") != self.name:
            raise ValueError("producer does not match adapter")
        if not self.auth:
            raise ValueError("producer authentication is not configured")
        return self.gateway.submit(event, auth=self.auth)


class DryRunTransport:
    """Records no network side effect and returns an explicit non-delivery result."""

    def __init__(self):
        self.messages: list[str] = []

    def send(self, text: str) -> TransportOutcome:
        self.messages.append(text)
        return TransportOutcome("rejected")


class OfflineReportAdapter:
    """Deterministic test double that returns a receipt bound to exact content."""

    def __init__(self, destination: str, available: bool = True):
        self.destination = destination
        self.available = available
        self.calls: list[tuple[str, int, int, str]] = []

    def send(self, report_id: str, revision: int, part: int, body: str, content_hash: str):
        if not self.available:
            raise RuntimeError("destination unavailable")
        self.calls.append((report_id, revision, part, body))
        return DeliveryReceipt(
            self.destination, report_id, revision, part, content_hash,
            f"{self.destination}-{report_id}-{revision}-{part}",
        )


class LocalHandoffAdapter:
    """Explicitly unconfirmed handoff; it never fabricates a platform receipt."""

    def send(self, *_args: Any, **_kwargs: Any):
        raise RuntimeError("operator/platform confirmation is required")
