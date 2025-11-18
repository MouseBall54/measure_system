"""Integrated ingestion endpoint for measurement data."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core import get_session
from ...models import (
    FileStatus,
    MeasurementFile,
    MeasurementItem,
    RawMeasurementRecord,
    StatMeasurement,
    StatMeasurementValue,
)
from ...schemas import (
    MeasurementPipelineCreate,
    MeasurementPipelineResult,
    MeasurementFileRead,
    MeasurementItemLink,
)


router = APIRouter(prefix="/measurements", tags=["measurements"])


async def _get_or_create_item(
    session: AsyncSession,
    link: MeasurementItemLink,
    cache: dict[tuple[str, str, int], MeasurementItem],
) -> MeasurementItem:
    cache_key = (link.class_name, link.measure_item_key, link.metric_type_id)
    if cache_key in cache:
        return cache[cache_key]

    stmt = select(MeasurementItem).where(
        MeasurementItem.class_name == link.class_name,
        MeasurementItem.measure_item_key == link.measure_item_key,
        MeasurementItem.metric_type_id == link.metric_type_id,
    )
    result = await session.execute(stmt)
    item = result.scalar_one_or_none()
    if item is None:
        item = MeasurementItem(
            class_name=link.class_name,
            measure_item_key=link.measure_item_key,
            metric_type_id=link.metric_type_id,
        )
        session.add(item)
        await session.flush()
    cache[cache_key] = item
    return item


@router.post(
    "/integrated",
    status_code=status.HTTP_201_CREATED,
    response_model=MeasurementPipelineResult,
)
async def ingest_integrated_measurements(
    payload: MeasurementPipelineCreate,
    session: AsyncSession = Depends(get_session),
) -> MeasurementPipelineResult:
    raw_count = 0
    stat_count = 0

    async with session.begin():
        file_data = MeasurementFile(
            post_time=payload.file.post_time,
            file_path=payload.file.file_path,
            parent_dir_0=payload.file.parent_dir_0,
            parent_dir_1=payload.file.parent_dir_1,
            parent_dir_2=payload.file.parent_dir_2,
            file_name=payload.file.file_name,
            file_hash=payload.file.file_hash,
            processing_ms=payload.file.processing_ms,
            status=FileStatus(payload.file.status),
        )
        session.add(file_data)
        await session.flush()
        await session.refresh(file_data)

        item_cache: dict[tuple[str, str, int], MeasurementItem] = {}

        for raw_entry in payload.raw_measurements:
            item = await _get_or_create_item(session, raw_entry.item, item_cache)
            record = RawMeasurementRecord(
                file_id=file_data.id,
                item_id=item.id,
                measurable=raw_entry.measurable,
                x_index=raw_entry.x_index,
                y_index=raw_entry.y_index,
                x_0=raw_entry.x_0,
                y_0=raw_entry.y_0,
                x_1=raw_entry.x_1,
                y_1=raw_entry.y_1,
                value=raw_entry.value,
            )
            session.add(record)
            raw_count += 1

        for stat_entry in payload.stat_measurements:
            item = await _get_or_create_item(session, stat_entry.item, item_cache)
            measurement = StatMeasurement(
                file_id=file_data.id,
                item_id=item.id,
                extra_json=stat_entry.extra_json,
            )
            session.add(measurement)
            await session.flush()

            values = [
                StatMeasurementValue(
                    stat_measurement_id=measurement.id,
                    value_type_id=value_payload.value_type_id,
                    value=value_payload.value,
                )
                for value_payload in stat_entry.values
            ]
            session.add_all(values)
            stat_count += 1

    return MeasurementPipelineResult(
        file=MeasurementFileRead.model_validate(file_data),
        raw_records=raw_count,
        stat_measurements=stat_count,
    )
