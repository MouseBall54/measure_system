"""Integrated ingestion endpoint for measurement data."""

from __future__ import annotations

from hashlib import sha256

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ...core import get_session
from ...models import (
    DetectionClass,
    FileClassCount,
    FileStatus,
    MeasurementDirectory,
    MeasurementFile,
    MeasurementItem,
    MeasurementMetricType,
    MeasurementModule,
    MeasurementNode,
    MeasurementVersion,
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


router = APIRouter(prefix="/measurement-results", tags=["measurement-results"])


def _compute_file_hash(file_payload: MeasurementFileCreate) -> str:
    parts = [
        file_payload.parent_dir_0 or "",
        file_payload.parent_dir_1 or "",
        file_payload.parent_dir_2 or "",
        file_payload.file_name,
    ]
    material = "|".join(parts)
    return sha256(material.encode("utf-8")).hexdigest()


def _build_lock_key(file_hash: str) -> str:
    prefix = "file_ing:"
    allowable = 64 - len(prefix)
    return prefix + file_hash[:allowable]


async def _get_or_create_node(
    session: AsyncSession,
    name: str | None,
    cache: dict[str, MeasurementNode],
) -> MeasurementNode | None:
    if not name:
        return None
    if name in cache:
        return cache[name]
    stmt = select(MeasurementNode).where(MeasurementNode.name == name)
    result = await session.execute(stmt)
    node = result.scalar_one_or_none()
    if node is None:
        node = MeasurementNode(name=name)
        session.add(node)
        await session.flush()
    cache[name] = node
    return node


async def _get_or_create_module(
    session: AsyncSession,
    name: str | None,
    cache: dict[str, MeasurementModule],
) -> MeasurementModule | None:
    if not name:
        return None
    if name in cache:
        return cache[name]
    stmt = select(MeasurementModule).where(MeasurementModule.name == name)
    result = await session.execute(stmt)
    module = result.scalar_one_or_none()
    if module is None:
        module = MeasurementModule(name=name)
        session.add(module)
        await session.flush()
    cache[name] = module
    return module


async def _get_or_create_version(
    session: AsyncSession,
    name: str | None,
    cache: dict[str, MeasurementVersion],
) -> MeasurementVersion | None:
    if not name:
        return None
    if name in cache:
        return cache[name]
    stmt = select(MeasurementVersion).where(MeasurementVersion.name == name)
    result = await session.execute(stmt)
    version = result.scalar_one_or_none()
    if version is None:
        version = MeasurementVersion(name=name)
        session.add(version)
        await session.flush()
    cache[name] = version
    return version


async def _get_or_create_directory_path(
    session: AsyncSession,
    segments: list[str | None],
    cache: dict[tuple[str, ...], MeasurementDirectory],
) -> MeasurementDirectory | None:
    path: list[str] = []
    parent: MeasurementDirectory | None = None
    for name in segments:
        if not name:
            continue
        path.append(name)
        key = tuple(path)
        if key in cache:
            parent = cache[key]
            continue
        stmt = select(MeasurementDirectory).where(
            MeasurementDirectory.parent_id == (parent.id if parent else None),
            MeasurementDirectory.name == name,
        )
        result = await session.execute(stmt)
        directory = result.scalar_one_or_none()
        if directory is None:
            directory = MeasurementDirectory(parent_id=parent.id if parent else None, name=name)
            session.add(directory)
            await session.flush()
        cache[key] = directory
        parent = directory
    return parent


async def _clear_existing_measurement_data(
    session: AsyncSession,
    file_id: int,
) -> None:
    await session.execute(delete(RawMeasurementRecord).where(RawMeasurementRecord.file_id == file_id))
    await session.execute(delete(StatMeasurement).where(StatMeasurement.file_id == file_id))
    await session.execute(delete(FileClassCount).where(FileClassCount.file_id == file_id))
    await session.flush()


async def _acquire_file_lock(session: AsyncSession, lock_key: str, timeout: int = 30) -> None:
    result = await session.execute(text("SELECT GET_LOCK(:lock_key, :timeout)"), {"lock_key": lock_key, "timeout": timeout})
    acquired = result.scalar_one()
    if acquired != 1:
        raise HTTPException(status_code=503, detail="Could not obtain lock for file ingestion")
    await session.commit()


async def _release_file_lock(session: AsyncSession, lock_key: str) -> None:
    await session.execute(text("SELECT RELEASE_LOCK(:lock_key)"), {"lock_key": lock_key})
    await session.commit()


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
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=MeasurementPipelineResult,
)
async def ingest_measurement_results(
    payload: MeasurementPipelineCreate,
    session: AsyncSession = Depends(get_session),
) -> MeasurementPipelineResult:
    raw_count = 0
    stat_count = 0

    file_hash = _compute_file_hash(payload.file)
    lock_key = _build_lock_key(file_hash)
    await _acquire_file_lock(session, lock_key)
    try:
        async with session.begin():
            node_cache: dict[str, MeasurementNode] = {}
            module_cache: dict[str, MeasurementModule] = {}
            version_cache: dict[str, MeasurementVersion] = {}
            directory_cache: dict[tuple[str, ...], MeasurementDirectory] = {}

            existing_stmt = (
                select(MeasurementFile)
                .where(MeasurementFile.file_hash == file_hash)
                .with_for_update(nowait=False)
            )
            result = await session.execute(existing_stmt)
            file_data = result.scalar_one_or_none()

            node = await _get_or_create_node(session, payload.file.node_name, node_cache)
            module = await _get_or_create_module(session, payload.file.module_name, module_cache)
            version = await _get_or_create_version(
                session, payload.file.version_name, version_cache
            )
            directory = await _get_or_create_directory_path(
                session,
                [payload.file.parent_dir_0, payload.file.parent_dir_1, payload.file.parent_dir_2],
                directory_cache,
            )

            if file_data is None:
                file_data = MeasurementFile(
                    post_time=payload.file.post_time,
                    file_path=payload.file.file_path,
                    file_name=payload.file.file_name,
                    file_hash=file_hash,
                    processing_ms=payload.file.processing_ms,
                    status=FileStatus(payload.file.status),
                )
                session.add(file_data)
                await session.flush()
                await session.refresh(file_data)
            else:
                file_data.post_time = payload.file.post_time
                file_data.file_path = payload.file.file_path
                file_data.file_name = payload.file.file_name
                file_data.processing_ms = payload.file.processing_ms
                file_data.status = FileStatus(payload.file.status)
                await _clear_existing_measurement_data(session, file_data.id)

            file_data.file_hash = file_hash
            file_data.node_id = node.id if node else None
            file_data.module_id = module.id if module else None
            file_data.version_id = version.id if version else None
            file_data.directory_id = directory.id if directory else None

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
            )
            session.add(measurement)
            await session.flush()

            values = []
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

        for class_name, count in payload.class_counts.items():
            class_stmt = select(DetectionClass).where(DetectionClass.name == class_name)
            class_result = await session.execute(class_stmt)
            det_class = class_result.scalar_one_or_none()
            if det_class is None:
                det_class = DetectionClass(name=class_name)
                session.add(det_class)
                await session.flush()

            stmt = select(FileClassCount).where(
                FileClassCount.file_id == file_data.id,
                FileClassCount.class_id == det_class.id,
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                existing.cnt = count
            else:
                session.add(
                    FileClassCount(
                        file_id=file_data.id,
                        class_id=det_class.id,
                        cnt=count,
                    )
                )

    finally:
        await _release_file_lock(session, lock_key)

    return MeasurementPipelineResult(
        file=MeasurementFileRead.model_validate(file_data),
        raw_records=raw_count,
        stat_measurements=stat_count,
    )
