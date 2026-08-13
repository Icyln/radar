import argparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import engine
from app.models.user import User


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Grant or revoke Radar administrator access")
    parser.add_argument("--email", required=True)
    parser.add_argument("--revoke", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    email = args.email.strip().casefold()
    with Session(engine, expire_on_commit=False) as session:
        user = session.scalar(select(User).where(User.email == email))
        if user is None:
            raise SystemExit(f"No Radar user exists with email: {email}")
        user.is_admin = not args.revoke
        session.commit()
        print(f"{user.email}: is_admin={user.is_admin}")


if __name__ == "__main__":
    main()
