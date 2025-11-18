"""Routes for raw measurement data."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db import get_session
from ...models import RawMeasurementRecord
from ...schemas import RawMeasurementCreate, RawMeasurementRead


router = APIRouter(prefix="/raw-measurements", tags=["raw-measurements"])


@router.get("/", response_model=list[RawMeasurementRead])
async def list_raw_measurements(
    session: AsyncSession = Depends(get_session),
) -> list[RawMeasurementRead]:
    result = await session.execute(select(RawMeasurementRecord))
    records = result.scalars().all()
    return [RawMeasurementRead.model_validate(rec) for rec in records]


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=RawMeasurementRead,
)
async def create_raw_measurement(
    payload: RawMeasurementCreate,
    session: AsyncSession = Depends(get_session),
) -> RawMeasurementRead:
    record = RawMeasurementRecord(
        file_id=payload.file_id,
        item_id=payload.item_id,
        measurable=payload.measurable,
        x_index=payload.x_index,
        y_index=payload.y_index,
        x_0=payload.x_0,
        y_0=payload.y_0,
        x_1=payload.x_1,
        y_1=payload.y_1,
        value=payload.value,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return RawMeasurementRead.model_validate(record)
