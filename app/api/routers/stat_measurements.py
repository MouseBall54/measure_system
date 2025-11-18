"""Routes for statistical measurement data."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.db import get_session
from ...models import StatMeasurement, StatMeasurementValue
from ...schemas import (
    StatMeasurementCreate,
    StatMeasurementRead,
    StatMeasurementValueRead,
)


router = APIRouter(prefix="/stat-measurements", tags=["stat-measurements"])


def _to_schema(record: StatMeasurement) -> StatMeasurementRead:
    values = [
        StatMeasurementValueRead(value_type_id=val.value_type_id, value=val.value)
        for val in sorted(record.values, key=lambda v: v.value_type_id)
    ]
    return StatMeasurementRead(
        id=record.id,
        file_id=record.file_id,
        item_id=record.item_id,
        extra_json=record.extra_json,
        values=values,
    )


@router.get("/", response_model=list[StatMeasurementRead])
async def list_stat_measurements(
    session: AsyncSession = Depends(get_session),
) -> list[StatMeasurementRead]:
    stmt = select(StatMeasurement).options(selectinload(StatMeasurement.values))
    result = await session.execute(stmt)
    records = result.scalars().all()
    return [_to_schema(rec) for rec in records]


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=StatMeasurementRead,
)
async def create_stat_measurement(
    payload: StatMeasurementCreate,
    session: AsyncSession = Depends(get_session),
) -> StatMeasurementRead:
    measurement = StatMeasurement(
        file_id=payload.file_id,
        item_id=payload.item_id,
        extra_json=payload.extra_json,
    )
    session.add(measurement)
    await session.flush()

    values = [
        StatMeasurementValue(
            stat_measurement_id=measurement.id,
            value_type_id=item.value_type_id,
            value=item.value,
        )
        for item in payload.values
    ]
    session.add_all(values)

    await session.commit()
    await session.refresh(measurement)
    await session.refresh(measurement, attribute_names=["values"])
    return _to_schema(measurement)
