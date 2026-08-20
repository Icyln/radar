import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import admin_user, current_user
from app.matching.service import (
    backfill_watchlist_profiles_for_company,
    prune_watchlist_company_matches,
)
from app.db.session import get_db
from app.models.company import Company
from app.models.job import Job
from app.models.user import User
from app.models.user_company_watchlist import UserCompanyWatchlist
from app.schemas.company import CompanyCreate, CompanyRead, CompanyUpdate
from app.schemas.watchlist import CompanyWatchlistRead

router = APIRouter(prefix="/api/v1/companies", tags=["companies"])


@router.get("", response_model=list[CompanyRead])
def list_companies(
    q: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(current_user),
    session: Session = Depends(get_db),
) -> list[Company]:
    statement = select(Company)
    search = (q or "").strip()
    if search:
        statement = statement.where(Company.name.ilike(f"%{search}%"))
    return list(
        session.scalars(
            statement.order_by(Company.name.asc()).limit(limit).offset(offset)
        )
    )



@router.get("/watchlist", response_model=list[CompanyWatchlistRead])
def list_watchlist(
    user: User = Depends(current_user), session: Session = Depends(get_db)
) -> list[UserCompanyWatchlist]:
    return list(
        session.scalars(
            select(UserCompanyWatchlist)
            .where(UserCompanyWatchlist.user_id == user.id)
            .order_by(UserCompanyWatchlist.created_at.asc())
        )
    )


@router.put("/{company_id}/watchlist", response_model=CompanyWatchlistRead)
def add_to_watchlist(
    company_id: uuid.UUID,
    user: User = Depends(current_user),
    session: Session = Depends(get_db),
) -> UserCompanyWatchlist:
    company = session.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")
    existing = session.scalar(
        select(UserCompanyWatchlist).where(
            UserCompanyWatchlist.user_id == user.id,
            UserCompanyWatchlist.company_id == company_id,
        )
    )
    if existing is not None:
        return existing

    item = UserCompanyWatchlist(user_id=user.id, company_id=company_id)
    session.add(item)
    session.flush()
    backfill_watchlist_profiles_for_company(session, user_id=user.id, company_id=company_id)
    session.commit()
    session.refresh(item)
    return item


@router.delete("/{company_id}/watchlist", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_watchlist(
    company_id: uuid.UUID,
    user: User = Depends(current_user),
    session: Session = Depends(get_db),
) -> None:
    item = session.scalar(
        select(UserCompanyWatchlist).where(
            UserCompanyWatchlist.user_id == user.id,
            UserCompanyWatchlist.company_id == company_id,
        )
    )
    if item is None:
        return
    session.delete(item)
    session.flush()
    prune_watchlist_company_matches(session, user_id=user.id, company_id=company_id)
    session.commit()


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
def create_company(
    payload: CompanyCreate,
    _: User = Depends(admin_user),
    session: Session = Depends(get_db),
) -> Company:
    company = Company(**payload.model_dump())
    session.add(company)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="ATS provider/identifier already exists") from exc
    session.refresh(company)
    return company


@router.patch("/{company_id}", response_model=CompanyRead)
def update_company(
    company_id: uuid.UUID,
    payload: CompanyUpdate,
    _: User = Depends(admin_user),
    session: Session = Depends(get_db),
) -> Company:
    company = session.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")
    updates = payload.model_dump(exclude_unset=True)
    identity_changes = (
        ("ats_provider" in updates and updates["ats_provider"] != company.ats_provider)
        or ("ats_identifier" in updates and updates["ats_identifier"] != company.ats_identifier)
    )
    if identity_changes and session.scalar(select(Job.id).where(Job.company_id == company.id).limit(1)):
        raise HTTPException(
            status_code=409,
            detail="cannot change ATS identity after jobs exist; disable this company and create a new source",
        )
    for field, value in updates.items():
        setattr(company, field, value)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="ATS provider/identifier already exists") from exc
    session.refresh(company)
    return company
