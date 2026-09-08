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
from .adapters import (
    DirectTelegramReportAdapter,
    DryRunTransport,
    LocalHandoffAdapter,
    LocalProducer,
    OfflineReportAdapter,
)
from .report import DeliveryBlocked, DeliveryReceipt, DeliveryRetry, Report, ReportGateway, ReportStore

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
    "DeliveryBlocked",
    "DeliveryRetry",
    "Report",
    "ReportGateway",
    "ReportStore",
    "OfflineReportAdapter",
    "LocalHandoffAdapter",
    "DirectTelegramReportAdapter",
    "format_telegram_message",
]
