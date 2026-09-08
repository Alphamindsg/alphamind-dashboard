import argparse
import json
import os
import sys

from .gateway import Gateway, GatewayError, SQLiteState, DirectTelegramTransport, doctor


def main() -> int:
    parser = argparse.ArgumentParser(description="AlphaMind notification gateway")
    parser.add_argument("command", choices=("doctor", "health", "worker", "submit", "reconcile"))
    parser.add_argument("--event", help="path to a JSON event fixture")
    parser.add_argument("--event-id")
    parser.add_argument("--evidence", action="append", default=[])
    parser.add_argument("--decision", choices=("delivered", "not_delivered", "dead"))
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
        print(json.dumps(state.health(provider_ready=ready), sort_keys=True))
    elif args.command == "submit":
        if not args.event:
            print("--event is required", file=sys.stderr)
            return 2
        with open(args.event, encoding="utf-8") as stream:
            print(Gateway(state, {"dashboard"}).submit(json.load(stream)))
    elif args.command == "reconcile":
        if not args.event_id or not args.decision:
            print("--event-id and --decision are required", file=sys.stderr)
            return 2
        print(state.reconcile(args.event_id, args.evidence, args.decision))
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
