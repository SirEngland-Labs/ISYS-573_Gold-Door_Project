"""Pydantic models for request/response validation."""

from pydantic import BaseModel, Field
from datetime import datetime, date, time
from typing import Optional
from enum import Enum


class ReservationStatus(str, Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class Table(BaseModel):
    id: int
    name: str  # e.g., "Table 1", "Patio 3"
    capacity: int  # max guests
    location: str  # "indoor" or "outdoor"


class Reservation(BaseModel):
    id: Optional[int] = None
    customer_name: str
    customer_phone: str
    party_size: int = Field(ge=1, le=10)
    date: date
    time: time
    table_id: Optional[int] = None
    status: ReservationStatus = ReservationStatus.CONFIRMED
    special_requests: Optional[str] = None
    created_at: Optional[datetime] = None


class ReservationRequest(BaseModel):
    """What the agent collects from the customer."""
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    party_size: Optional[int] = None
    date: Optional[date] = None
    time: Optional[time] = None
    special_requests: Optional[str] = None


class AvailabilityQuery(BaseModel):
    date: date
    time: Optional[time] = None
    party_size: int = 2
