"""Local authenticated producer and non-sending fixture adapters."""

from __future__ import annotations

from typing import Any, Mapping

from .gateway import Gateway, TransportOutcome


class LocalProducer:
    """A bounded local adapter; deployment wiring supplies its auth separately."""

    def __init__(self, gateway: Gateway, name: str = "dashboard", auth: str = "local"):
        self.gateway, self.name, self.auth = gateway, name, auth

    def submit(self, event: Mapping[str, Any]) -> str:
        if event.get("producer") != self.name:
            raise ValueError("producer does not match adapter")
        return self.gateway.submit(event, auth=self.auth)


class DryRunTransport:
    """Records no network side effect and returns an explicit non-delivery result."""

    def __init__(self):
        self.messages: list[str] = []

    def send(self, text: str) -> TransportOutcome:
        self.messages.append(text)
        return TransportOutcome("rejected")
