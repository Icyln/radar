import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import admin_user, current_user
from app.db.session import get_db
from app.models.company import Company
from app.models.job import Job
from app.models.user import User
from app.schemas.company import CompanyCreate, CompanyRead, CompanyUpdate

router = APIRouter(prefix="/api/v1/companies", tags=["companies"])


@router.get("", response_model=list[CompanyRead])
def list_companies(
    _: User = Depends(current_user), session: Session = Depends(get_db)
) -> list[Company]:
    return list(session.scalars(select(Company).order_by(Company.name.asc())))


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
