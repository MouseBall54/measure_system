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
    MeasurementMetricType,
    RawMeasurementRecord,
    StatMeasurement,
    StatMeasurementValue,
    StatValueType,
)
from ...schemas import (
    MeasurementPipelineCreate,
    MeasurementPipelineResult,
    MeasurementFileRead,
    MeasurementItemLink,
    MetricTypeLink,
)


router = APIRouter(prefix="/measurements", tags=["measurements"])


async def _get_or_create_metric_type(
    session: AsyncSession,
    link: MetricTypeLink,
    cache: dict[tuple[str, str | None], MeasurementMetricType],
) -> MeasurementMetricType:
    cache_key = (link.name, link.unit)
    if cache_key in cache:
        return cache[cache_key]

    stmt = select(MeasurementMetricType).where(MeasurementMetricType.name == link.name)
    result = await session.execute(stmt)
    metric_type = result.scalar_one_or_none()
    if metric_type is None:
        metric_type = MeasurementMetricType(name=link.name, unit=link.unit)
        session.add(metric_type)
        await session.flush()
    cache[cache_key] = metric_type
    return metric_type


async def _get_or_create_item(
    session: AsyncSession,
    link: MeasurementItemLink,
    metric_type: MeasurementMetricType,
    cache: dict[tuple[str, str, int], MeasurementItem],
) -> MeasurementItem:
    cache_key = (link.class_name, link.measure_item_key, metric_type.id)
    if cache_key in cache:
        return cache[cache_key]

    stmt = select(MeasurementItem).where(
        MeasurementItem.class_name == link.class_name,
        MeasurementItem.measure_item_key == link.measure_item_key,
        MeasurementItem.metric_type_id == metric_type.id,
    )
    result = await session.execute(stmt)
    item = result.scalar_one_or_none()
    if item is None:
        item = MeasurementItem(
            class_name=link.class_name,
            measure_item_key=link.measure_item_key,
            metric_type_id=metric_type.id,
        )
        session.add(item)
        await session.flush()
    cache[cache_key] = item
    return item


async def _get_or_create_value_type(
    session: AsyncSession,
    name: str,
    cache: dict[str, StatValueType],
) -> StatValueType:
    if name in cache:
        return cache[name]

    stmt = select(StatValueType).where(StatValueType.name == name)
    result = await session.execute(stmt)
    value_type = result.scalar_one_or_none()
    if value_type is None:
        value_type = StatValueType(name=name)
        session.add(value_type)
        await session.flush()
    cache[name] = value_type
    return value_type


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

        metric_cache: dict[tuple[str, str | None], MeasurementMetricType] = {}
        item_cache: dict[tuple[str, str, int], MeasurementItem] = {}
        value_type_cache: dict[str, StatValueType] = {}

        for raw_entry in payload.raw_measurements:
            metric_type = await _get_or_create_metric_type(
                session, raw_entry.item.metric_type, metric_cache
            )
            item = await _get_or_create_item(session, raw_entry.item, metric_type, item_cache)
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
            metric_type = await _get_or_create_metric_type(
                session, stat_entry.item.metric_type, metric_cache
            )
            item = await _get_or_create_item(session, stat_entry.item, metric_type, item_cache)
            measurement = StatMeasurement(
                file_id=file_data.id,
                item_id=item.id,
                extra_json=stat_entry.extra_json,
            )
            session.add(measurement)
            await session.flush()

            values: list[StatMeasurementValue] = []
            for value_payload in stat_entry.values:
                value_type = await _get_or_create_value_type(
                    session, value_payload.value_type_name, value_type_cache
                )
                values.append(
                    StatMeasurementValue(
                        stat_measurement_id=measurement.id,
                        value_type_id=value_type.id,
                        value=value_payload.value,
                    )
                )
            session.add_all(values)
            stat_count += 1

    return MeasurementPipelineResult(
        file=MeasurementFileRead.model_validate(file_data),
        raw_records=raw_count,
        stat_measurements=stat_count,
    )
