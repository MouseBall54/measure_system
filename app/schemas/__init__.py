"""Pydantic schemas for request/response bodies."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class MetricTypeLink(BaseModel):
    name: str
    unit: str | None = None


class StatMeasurementValuePayload(BaseModel):
    value_type_name: str
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


class MeasurementItemLink(BaseModel):
    class_name: str
    measure_item_key: str
    metric_type: MetricTypeLink


class PipelineRawMeasurement(BaseModel):
    item: MeasurementItemLink
    measurable: bool = True
    x_index: int
    y_index: int
    x_0: float
    y_0: float
    x_1: float
    y_1: float
    value: float


class PipelineStatMeasurement(BaseModel):
    item: MeasurementItemLink
    values: list[StatMeasurementValuePayload] = Field(default_factory=list)


class FileClassCountPayload(BaseModel):
    class_name: str
    count: int


class MeasurementPipelineCreate(BaseModel):
    file: MeasurementFileCreate
    raw_measurements: list[PipelineRawMeasurement] = Field(default_factory=list)
    stat_measurements: list[PipelineStatMeasurement] = Field(default_factory=list)
    class_counts: dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def normalize_class_counts(cls, values: dict[str, Any]) -> dict[str, Any]:
        counts = values.get("class_counts")
        if counts is None:
            values["class_counts"] = {}
            return values
        if isinstance(counts, dict):
            return values
        if isinstance(counts, list):
            normalized: dict[str, int] = {}
            for entry in counts:
                payload = entry
                if not isinstance(entry, FileClassCountPayload):
                    payload = FileClassCountPayload(**entry)
                normalized[payload.class_name] = payload.count
            values["class_counts"] = normalized
            return values
        raise ValueError("class_counts must be a dict or list of objects")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file": {
                    "post_time": "2024-05-20T08:00:00Z",
                    "file_path": "/data/line_a/20240520/img/wafer123/run1.csv",
                    "parent_dir_0": "img",
                    "parent_dir_1": "wafer123",
                    "parent_dir_2": "line_a",
                    "file_name": "run1.csv",
                    "processing_ms": 1520,
                    "status": "OK"
                },
                "raw_measurements": [
                    {
                        "item": {
                            "class_name": "P1",
                            "measure_item_key": "VERTICAL_CD",
                            "metric_type": {
                                "name": "CD",
                                "unit": "nm"
                            }
                        },
                        "measurable": True,
                        "x_index": 3,
                        "y_index": 5,
                        "x_0": 12.5,
                        "y_0": 8.0,
                        "x_1": 13.0,
                        "y_1": 8.6,
                        "value": 31.27
                    }
                ],
                "stat_measurements": [
                    {
                        "item": {
                            "class_name": "P1",
                            "measure_item_key": "VERTICAL_CD",
                            "metric_type": {
                                "name": "CD",
                                "unit": "nm"
                            }
                        },
                        "values": [
                            {"value_type_name": "AVG", "value": 31.27},
                            {"value_type_name": "STD", "value": 0.42}
                        ]
                    }
                ],
                "class_counts": {
                    "P1": 500,
                    "P2": 170
                }
            }
        }
    )


class MeasurementPipelineResult(BaseModel):
    file: MeasurementFileRead
    raw_records: int
    stat_measurements: int


__all__ = [
    "MeasurementFileCreate",
    "MeasurementFileRead",
    "RawMeasurementCreate",
    "RawMeasurementRead",
    "StatMeasurementCreate",
    "StatMeasurementRead",
    "StatMeasurementValueRead",
    "MetricTypeLink",
    "MeasurementItemLink",
    "PipelineRawMeasurement",
    "PipelineStatMeasurement",
    "FileClassCountPayload",
    "MeasurementPipelineCreate",
    "MeasurementPipelineResult",
]
