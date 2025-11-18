"""Pydantic schemas for request/response bodies."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MeasurementFileBase(BaseModel):
    post_time: datetime
    file_path: str
    parent_dir_0: str
    parent_dir_1: str | None = None
    parent_dir_2: str | None = None
    file_name: str
    file_hash: str | None = None
    processing_ms: int | None = None
    status: str = "OK"


class MeasurementFileCreate(MeasurementFileBase):
    pass


class MeasurementFileRead(MeasurementFileBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class StatMeasurementValuePayload(BaseModel):
    value_type_id: int
    value: float


class StatMeasurementCreate(BaseModel):
    file_id: int
    item_id: int
    extra_json: dict[str, Any] | None = None
    values: list[StatMeasurementValuePayload] = Field(default_factory=list)


class StatMeasurementValueRead(BaseModel):
    value_type_id: int
    value: float


class StatMeasurementRead(BaseModel):
    id: int
    file_id: int
    item_id: int
    extra_json: dict[str, Any] | None
    values: list[StatMeasurementValueRead]

    class Config:
        from_attributes = True


class RawMeasurementBase(BaseModel):
    file_id: int
    item_id: int
    measurable: bool = True
    x_index: int
    y_index: int
    x_0: float
    y_0: float
    x_1: float
    y_1: float
    value: float


class RawMeasurementCreate(RawMeasurementBase):
    pass


class RawMeasurementRead(RawMeasurementBase):
    id: int

    class Config:
        from_attributes = True


__all__ = [
    "MeasurementFileCreate",
    "MeasurementFileRead",
    "RawMeasurementCreate",
    "RawMeasurementRead",
    "StatMeasurementCreate",
    "StatMeasurementRead",
    "StatMeasurementValueRead",
]
