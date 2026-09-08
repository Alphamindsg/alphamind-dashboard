import argparse
import json
import os

from .gateway import Gateway, SQLiteState, DirectTelegramTransport, doctor


def main() -> int:
    parser = argparse.ArgumentParser(description="AlphaMind notification gateway")
    parser.add_argument("command", choices=("doctor", "health", "worker"))
    args = parser.parse_args()
    state = SQLiteState(os.getenv("ALPHAMIND_NOTIFICATION_STATE", "notification-gateway.sqlite3"))
    if args.command == "doctor":
        print(json.dumps(doctor(), sort_keys=True))
    elif args.command == "health":
        print(json.dumps(state.health(), sort_keys=True))
    else:
        transport = None
        if os.getenv("ALPHAMIND_TELEGRAM_BOT_TOKEN") and os.getenv("ALPHAMIND_TELEGRAM_CHAT_ID"):
            transport = DirectTelegramTransport(
                os.environ["ALPHAMIND_TELEGRAM_BOT_TOKEN"],
                os.environ["ALPHAMIND_TELEGRAM_CHAT_ID"],
            )
        print(Gateway(state, {"dashboard"}, transport).process_one())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
