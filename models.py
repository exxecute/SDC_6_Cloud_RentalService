from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date


class RentalCreate(BaseModel):
    user_id: int
    item_id: int
    start_date: date
    end_date: date
    status: str
    total_price: float


class RentalUpdate(BaseModel):
    user_id: Optional[int] = None
    item_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    total_price: Optional[float] = None


class RentalResponse(BaseModel):
    id: int
    user_id: int
    item_id: int
    start_date: date
    end_date: date
    status: str
    total_price: float
    created_at: datetime
