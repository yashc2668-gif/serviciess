"""Labour attendance schemas."""

from datetime import date as dt_date
from datetime import datetime
from typing import Optional

from pydantic import AliasChoices, BaseModel, Field


class LabourAttendanceItemCreate(BaseModel):
    labour_id: int = Field(..., ge=1)
    attendance_status: str = Field(default="present", max_length=20)
    present_days: Optional[float] = Field(default=None, ge=0)
    overtime_hours: float = Field(default=0, ge=0)
    wage_rate: Optional[float] = Field(default=None, ge=0)
    remarks: Optional[str] = None


class LabourAttendanceItemUpdate(BaseModel):
    id: int = Field(..., ge=1)
    attendance_status: Optional[str] = Field(default=None, max_length=20)
    present_days: Optional[float] = Field(default=None, ge=0)
    overtime_hours: Optional[float] = Field(default=None, ge=0)
    wage_rate: Optional[float] = Field(default=None, ge=0)
    remarks: Optional[str] = None


class LabourAttendanceCreate(BaseModel):
    muster_no: Optional[str] = Field(default=None, min_length=1, max_length=100)
    project_id: int = Field(..., ge=1)
    contractor_id: Optional[int] = Field(default=None, ge=1)
    date: dt_date = Field(..., validation_alias=AliasChoices("date", "attendance_date"))
    created_by: Optional[int] = Field(
        default=None,
        ge=1,
        validation_alias=AliasChoices("created_by", "marked_by"),
    )
    status: str = Field(default="draft", max_length=30)
    remarks: Optional[str] = None
    items: list[LabourAttendanceItemCreate] = Field(..., min_length=1)


class LabourAttendanceUpdate(BaseModel):
    muster_no: Optional[str] = Field(default=None, min_length=1, max_length=100)
    contractor_id: Optional[int] = Field(default=None, ge=1)
    date: Optional[dt_date] = Field(
        default=None,
        validation_alias=AliasChoices("date", "attendance_date"),
    )
    created_by: Optional[int] = Field(
        default=None,
        ge=1,
        validation_alias=AliasChoices("created_by", "marked_by"),
    )
    status: Optional[str] = Field(default=None, max_length=30)
    remarks: Optional[str] = None
    items: Optional[list[LabourAttendanceItemUpdate]] = None


class LabourAttendanceTransitionRequest(BaseModel):
    remarks: Optional[str] = Field(default=None, max_length=1000)


class LabourAttendanceItemOut(BaseModel):
    id: int
    labour_id: int
    attendance_status: str
    present_days: float
    overtime_hours: float
    wage_rate: float
    line_amount: float
    remarks: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class LabourAttendanceOut(BaseModel):
    id: int
    muster_no: str
    project_id: int
    contractor_id: Optional[int]
    date: Optional[dt_date]
    # Backward-compatible output fields.
    attendance_date: dt_date
    created_by: Optional[int]
    marked_by: int
    status: str
    remarks: Optional[str]
    total_wage: float
    created_at: datetime
    updated_at: Optional[datetime]
    items: list[LabourAttendanceItemOut]

    model_config = {"from_attributes": True}
