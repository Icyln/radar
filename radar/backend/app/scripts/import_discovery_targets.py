import argparse
import csv
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.session import create_db_engine
from app.models.discovery_target import DiscoveryTarget
from app.models.enums import DiscoveryTargetOrigin, DiscoveryTargetStatus


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bulk-import public company/career URLs for Phase 6 discovery"
    )
    parser.add_argument("--file", required=True, help="CSV containing url and optional company_name")
    args = parser.parse_args()

    path = Path(args.file)
    engine = create_db_engine()
    inserted = 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle, Session(engine) as session:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "url" not in reader.fieldnames:
            raise SystemExit("CSV must contain a 'url' column")
        for row in reader:
            url = (row.get("url") or "").strip()
            if not url:
                continue
            session.add(
                DiscoveryTarget(
                    url=url,
                    company_name_hint=(row.get("company_name") or "").strip() or None,
                    auto_watch=False,
                    origin=DiscoveryTargetOrigin.SYSTEM_FEED,
                    source_label=f"csv:{path.name}",
                    status=DiscoveryTargetStatus.PENDING,
                )
            )
            inserted += 1
        session.commit()
    engine.dispose()
    print(f"Imported {inserted} discovery targets")


if __name__ == "__main__":
    main()
