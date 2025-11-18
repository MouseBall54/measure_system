"""Routes for managing measurement file metadata."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db import get_session
from ...models import FileStatus, MeasurementFile
from ...schemas import MeasurementFileCreate, MeasurementFileRead


router = APIRouter(prefix="/files", tags=["files"])


@router.get("/", response_model=list[MeasurementFileRead])
async def list_files(
    session: AsyncSession = Depends(get_session),
) -> list[MeasurementFileRead]:
    result = await session.execute(select(MeasurementFile))
    records = result.scalars().all()
    return [MeasurementFileRead.model_validate(rec) for rec in records]


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=MeasurementFileRead)
async def create_file(
    payload: MeasurementFileCreate,
    session: AsyncSession = Depends(get_session),
) -> MeasurementFileRead:
    file_rec = MeasurementFile(
        post_time=payload.post_time,
        file_path=payload.file_path,
        parent_dir_0=payload.parent_dir_0,
        parent_dir_1=payload.parent_dir_1,
        parent_dir_2=payload.parent_dir_2,
        file_name=payload.file_name,
        file_hash=payload.file_hash,
        processing_ms=payload.processing_ms,
        status=FileStatus(payload.status),
    )
    session.add(file_rec)
    await session.commit()
    await session.refresh(file_rec)
    return MeasurementFileRead.model_validate(file_rec)
