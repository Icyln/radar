import argparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import engine
from app.models.company import Company
from app.models.enums import ATSProvider, MonitoringPriority


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed/update an ATS company")
    parser.add_argument("--name", required=True)
    parser.add_argument("--ats-identifier", required=True)
    parser.add_argument("--career-url", required=True)
    parser.add_argument("--website", default=None)
    parser.add_argument(
        "--provider",
        choices=[item.value.lower() for item in ATSProvider],
        default="greenhouse",
    )
    parser.add_argument(
        "--priority",
        choices=[item.value.lower() for item in MonitoringPriority],
        default="normal",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    identifier = args.ats_identifier.strip()
    provider = ATSProvider(args.provider.upper())
    priority = MonitoringPriority(args.priority.upper())
    with Session(engine, expire_on_commit=False) as session:
        company = session.scalar(
            select(Company).where(
                Company.ats_provider == provider,
                Company.ats_identifier == identifier,
            )
        )
        if company is None:
            company = Company(
                name=args.name.strip(),
                website=args.website,
                career_url=args.career_url,
                ats_provider=provider,
                ats_identifier=identifier,
                monitoring_priority=priority,
                active=True,
            )
            session.add(company)
        else:
            company.name = args.name.strip()
            company.website = args.website
            company.career_url = args.career_url
            company.monitoring_priority = priority
            company.active = True
        session.commit()
        print(f"{company.id} {company.name} ({company.ats_provider.value}:{company.ats_identifier})")


if __name__ == "__main__":
    main()
