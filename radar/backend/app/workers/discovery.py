import argparse
import asyncio
import json

from app.core.config import get_settings
from app.db.session import create_db_engine
from app.services.discovery import DiscoveryService


def parser() -> argparse.ArgumentParser:
    item = argparse.ArgumentParser(description="Discover, validate, and promote ATS sources")
    item.add_argument("--target-batch-size", type=int, default=None)
    item.add_argument("--candidate-batch-size", type=int, default=None)
    item.add_argument("--max-concurrency", type=int, default=None)
    item.add_argument("--auto-promote", action=argparse.BooleanOptionalAction, default=True)
    item.add_argument(
        "--ingest-system-feeds",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Ingest bundled and configured system discovery feeds before scanning targets",
    )
    item.add_argument(
        "--ingest-hiring-signals",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Use enabled Wide profiles to seed discovery from fresh public hiring signals",
    )
    item.add_argument(
        "--revalidate-promoted",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Periodically revalidate promoted ATS sources without disabling on one failure",
    )
    item.add_argument("--revalidate-batch-size", type=int, default=None)
    return item


async def async_main() -> None:
    args = parser().parse_args()
    settings = get_settings()
    engine = create_db_engine(settings.database_url)
    try:
        service = DiscoveryService(engine=engine, settings=settings)
        summary = await service.run(
            target_batch_size=args.target_batch_size or settings.discovery_target_batch_size,
            candidate_batch_size=args.candidate_batch_size or settings.discovery_candidate_batch_size,
            max_concurrency=args.max_concurrency or settings.discovery_max_concurrency,
            auto_promote=args.auto_promote,
            ingest_system_feeds=args.ingest_system_feeds,
            ingest_hiring_signals=args.ingest_hiring_signals,
            revalidate_promoted=args.revalidate_promoted,
            revalidate_batch_size=(
                args.revalidate_batch_size or settings.discovery_revalidate_batch_size
            ),
        )
        print(json.dumps(summary, sort_keys=True))
    finally:
        engine.dispose()


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
