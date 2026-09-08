import argparse
import json
import os
import sys

from .gateway import Gateway, GatewayError, SQLiteState, DirectTelegramTransport, doctor
from .adapters import LocalHandoffAdapter, OfflineReportAdapter
from .report import ReportGateway, ReportStore


def main() -> int:
    parser = argparse.ArgumentParser(description="AlphaMind notification gateway")
    parser.add_argument("command", choices=(
        "doctor", "health", "worker", "submit", "reconcile",
        "report-submit", "report-worker",
    ))
    parser.add_argument("--event", help="path to a JSON event fixture")
    parser.add_argument("--event-id")
    parser.add_argument("--evidence", action="append", default=[])
    parser.add_argument("--decision", choices=("delivered", "not_delivered", "dead"))
    parser.add_argument("--operator-id")
    parser.add_argument("--scope-key")
    parser.add_argument("--report-id")
    parser.add_argument("--revision", type=int)
    parser.add_argument("--offline-test-double", action="store_true")
    args = parser.parse_args()
    if args.command == "doctor":
        result = doctor()
        print(json.dumps(result, sort_keys=True))
        return 0 if all(result.values()) else 2
    path = os.getenv("ALPHAMIND_NOTIFICATION_STATE")
    if not path:
        print("ALPHAMIND_NOTIFICATION_STATE is required", file=sys.stderr)
        return 2
    state = SQLiteState(path)
    if args.command == "health":
        ready = bool(os.getenv("ALPHAMIND_TELEGRAM_BOT_TOKEN")) and bool(
            os.getenv("ALPHAMIND_TELEGRAM_CHAT_ID")
        )
        result = state.health(provider_ready=ready)
        print(json.dumps(result, sort_keys=True))
        if result["state"] == "BLOCKED":
            state.close()
            return 2
    elif args.command == "submit":
        if not args.event:
            print("--event is required", file=sys.stderr)
            return 2
        with open(args.event, encoding="utf-8") as stream:
            producer_auth = os.getenv("ALPHAMIND_PRODUCER_AUTH")
            allowed_repos = set(filter(None, os.getenv("ALPHAMIND_ALLOWED_REPOS", "").split(",")))
            if not producer_auth or not allowed_repos:
                print("producer authentication and repository binding are required", file=sys.stderr)
                return 2
            print(Gateway(state, {"dashboard": producer_auth}, allowed_repos=allowed_repos).submit(
                json.load(stream), auth=producer_auth
            ))
    elif args.command == "reconcile":
        if not (args.scope_key or args.event_id) or not args.decision or not args.operator_id:
            print("--scope-key, --decision, and --operator-id are required", file=sys.stderr)
            return 2
        print(state.reconcile(args.scope_key or args.event_id, args.evidence, args.decision, args.operator_id))
    elif args.command == "report-submit":
        if not args.event:
            print("--event is required", file=sys.stderr)
            return 2
        with open(args.event, encoding="utf-8") as stream:
            print(ReportGateway(
                ReportStore(state),
                {"chatgpt": LocalHandoffAdapter(), "telegram": LocalHandoffAdapter()},
            ).ingest(json.load(stream)))
    elif args.command == "report-worker":
        if not args.report_id or not args.revision:
            print("--report-id and --revision are required", file=sys.stderr)
            return 2
        if args.offline_test_double:
            adapters = {
                "chatgpt": OfflineReportAdapter("chatgpt"),
                "telegram": OfflineReportAdapter("telegram"),
            }
        else:
            adapters = {"chatgpt": LocalHandoffAdapter(), "telegram": LocalHandoffAdapter()}
        print(ReportGateway(ReportStore(state), adapters).deliver_one(args.report_id, args.revision))
    else:
        transport = None
        if os.getenv("ALPHAMIND_TELEGRAM_BOT_TOKEN") and os.getenv("ALPHAMIND_TELEGRAM_CHAT_ID"):
            transport = DirectTelegramTransport(
                os.environ["ALPHAMIND_TELEGRAM_BOT_TOKEN"],
                os.environ["ALPHAMIND_TELEGRAM_CHAT_ID"],
            )
        print(Gateway(state, {"dashboard"}, transport).process_one())
    state.close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (GatewayError, OSError, ValueError):
        print("notification gateway command failed", file=sys.stderr)
        raise SystemExit(2)
