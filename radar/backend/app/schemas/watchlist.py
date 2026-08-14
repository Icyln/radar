import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CompanyWatchlistRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    company_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
