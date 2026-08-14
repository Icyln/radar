import argparse
from sqlalchemy.engine import make_url

from app.core.config import get_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Radar scheduled-worker configuration")
    parser.add_argument("--require-telegram", action="store_true")
    parser.add_argument("--require-remote-database", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    problems: list[str] = []

    url = make_url(settings.database_url)
    if args.require_remote_database and url.host in {None, "localhost", "127.0.0.1", "::1"}:
        problems.append("DATABASE_URL must point to a remote PostgreSQL database for GitHub Actions")
    if args.require_telegram and not settings.telegram_bot_token:
        problems.append("TELEGRAM_BOT_TOKEN is required for production notification delivery")

    if problems:
        raise SystemExit("Worker configuration invalid:\n- " + "\n- ".join(problems))

    print(
        "Worker configuration OK: "
        f"database_host={url.host or 'unknown'} telegram={'configured' if settings.telegram_bot_token else 'disabled'}"
    )


if __name__ == "__main__":
    main()
