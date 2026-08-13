import argparse
import asyncio
import json
import uuid

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import engine
from app.models.enums import MonitoringPriority
from app.services.monitor import MonitorService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Radar ATS monitoring")
    parser.add_argument("--company-id", type=uuid.UUID, default=None)
    parser.add_argument("--ats-identifier", default=None)
    parser.add_argument(
        "--priority",
        choices=[item.value.lower() for item in MonitoringPriority],
        default=None,
    )
    return parser.parse_args()


async def async_main() -> int:
    args = parse_args()
    settings = get_settings()
    configure_logging(settings.log_level)
    priority = MonitoringPriority(args.priority.upper()) if args.priority else None
    service = MonitorService(engine=engine, settings=settings)
    summary = await service.run(
        company_id=args.company_id,
        ats_identifier=args.ats_identifier,
        priority=priority,
    )
    print(json.dumps(summary, sort_keys=True))
    return 1 if summary["failed"] else 0


def main() -> None:
    raise SystemExit(asyncio.run(async_main()))


if __name__ == "__main__":
    main()
