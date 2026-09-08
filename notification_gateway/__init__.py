"""Server-side notification gateway; intentionally not imported by browser code."""

from .gateway import (
    DirectTelegramTransport,
    Gateway,
    GatewayError,
    NotificationEvent,
    SQLiteState,
    TransportOutcome,
    format_telegram_message,
)
from .adapters import DryRunTransport, LocalHandoffAdapter, LocalProducer, OfflineReportAdapter
from .report import DeliveryReceipt, DeliveryRetry, Report, ReportGateway, ReportStore

__all__ = [
    "DirectTelegramTransport",
    "Gateway",
    "GatewayError",
    "NotificationEvent",
    "SQLiteState",
    "TransportOutcome",
    "DryRunTransport",
    "LocalProducer",
    "DeliveryReceipt",
    "DeliveryRetry",
    "Report",
    "ReportGateway",
    "ReportStore",
    "OfflineReportAdapter",
    "LocalHandoffAdapter",
    "format_telegram_message",
]
