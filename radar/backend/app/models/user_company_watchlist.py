import uuid

from sqlalchemy import ForeignKey, Index, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class UserCompanyWatchlist(TimestampMixin, Base):
    __tablename__ = "user_company_watchlists"
    __table_args__ = (
        UniqueConstraint("user_id", "company_id", name="uq_user_company_watchlist_user_company"),
        Index("ix_user_company_watchlists_user_company", "user_id", "company_id"),
        Index("ix_user_company_watchlists_company_id", "company_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )

    user = relationship("User", back_populates="company_watchlist")
    company = relationship("Company", back_populates="watchers")
