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
    parser.add_argument(
        "--scope",
        choices=["all", "watchlist", "registry"],
        default="all",
        help="all active sources, companies watched by any user, or non-watched registry sources",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="maximum number of eligible companies to process in this run",
    )
    parser.add_argument(
        "--min-age-minutes",
        type=int,
        default=None,
        help="only select sources never checked or not checked within this many minutes",
    )
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=None,
        help="maximum companies fetched concurrently; defaults to MONITOR_MAX_CONCURRENCY",
    )
    parser.add_argument(
        "--allow-partial-failures",
        action="store_true",
        help="exit successfully when individual companies fail after the rest of the batch is processed",
    )
    return parser.parse_args()


async def async_main() -> int:
    args = parse_args()
    settings = get_settings()
    configure_logging(settings.log_level)
    priority = MonitoringPriority(args.priority.upper()) if args.priority else None
    max_concurrency = args.max_concurrency or settings.monitor_max_concurrency
    service = MonitorService(engine=engine, settings=settings)
    summary = await service.run(
        company_id=args.company_id,
        ats_identifier=args.ats_identifier,
        priority=priority,
        source_scope=args.scope,
        shard_index=args.shard_index,
        shard_count=args.shard_count,
        batch_size=args.batch_size,
        min_age_minutes=args.min_age_minutes,
        max_concurrency=max_concurrency,
    )
    print(json.dumps(summary, sort_keys=True))
    if args.allow_partial_failures:
        return 0
    return 1 if int(summary["failed"]) else 0


def main() -> None:
    raise SystemExit(asyncio.run(async_main()))


if __name__ == "__main__":
    main()
