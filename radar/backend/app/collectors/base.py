from abc import ABC, abstractmethod

from app.schemas.company import CompanyTarget
from app.schemas.job import NormalizedJob


class CollectorError(Exception):
    def __init__(self, message: str, *, category: str) -> None:
        super().__init__(message)
        self.category = category


class BaseCollector(ABC):
    @abstractmethod
    async def fetch_jobs(self, company: CompanyTarget) -> list[NormalizedJob]:
        """Return a complete successful source snapshot or raise CollectorError."""

    async def close(self) -> None:
        return None
