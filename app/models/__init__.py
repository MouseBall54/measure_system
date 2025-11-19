"""SQLAlchemy ORM models for measurement raw/stat data."""

from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Computed,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.mysql import BIGINT, DATETIME, DOUBLE
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base class."""


class FileStatus(str, enum.Enum):
    OK = "OK"
    FAIL = "FAIL"


class MeasurementNode(Base):
    __tablename__ = "measurement_nodes"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)

    files: Mapped[list[MeasurementFile]] = relationship("MeasurementFile", back_populates="node")


class MeasurementModule(Base):
    __tablename__ = "measurement_modules"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)

    files: Mapped[list[MeasurementFile]] = relationship("MeasurementFile", back_populates="module")


class MeasurementVersion(Base):
    __tablename__ = "measurement_versions"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)

    files: Mapped[list[MeasurementFile]] = relationship("MeasurementFile", back_populates="version")


class MeasurementDirectory(Base):
    __tablename__ = "measurement_directories"
    __table_args__ = (
        UniqueConstraint("parent_id", "name", name="uk_directories_parent_name"),
    )

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("measurement_directories.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    parent: Mapped[MeasurementDirectory | None] = relationship(
        "MeasurementDirectory", remote_side="MeasurementDirectory.id", back_populates="children"
    )
    children: Mapped[list[MeasurementDirectory]] = relationship(
        "MeasurementDirectory", back_populates="parent"
    )
    files: Mapped[list[MeasurementFile]] = relationship(
        "MeasurementFile", back_populates="directory"
    )


class MeasurementFile(Base):
    __tablename__ = "measurement_files"
    __table_args__ = (
        UniqueConstraint("file_hash", name="uk_measurement_files_hash"),
    )

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    post_time: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)
    post_date: Mapped[date | None] = mapped_column(
        Date,
        Computed("DATE(post_time)", persisted=True),
    )
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    node_id: Mapped[int | None] = mapped_column(
        ForeignKey("measurement_nodes.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
    )
    module_id: Mapped[int | None] = mapped_column(
        ForeignKey("measurement_modules.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
    )
    version_id: Mapped[int | None] = mapped_column(
        ForeignKey("measurement_versions.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
    )
    directory_id: Mapped[int | None] = mapped_column(
        ForeignKey("measurement_directories.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
    )
    file_hash: Mapped[str | None] = mapped_column(String(64))
    processing_ms: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[FileStatus] = mapped_column(Enum(FileStatus), default=FileStatus.OK)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    node: Mapped[MeasurementNode | None] = relationship("MeasurementNode", back_populates="files")
    module: Mapped[MeasurementModule | None] = relationship("MeasurementModule", back_populates="files")
    version: Mapped[MeasurementVersion | None] = relationship("MeasurementVersion", back_populates="files")
    directory: Mapped[MeasurementDirectory | None] = relationship(
        "MeasurementDirectory", back_populates="files"
    )
    raw_records: Mapped[list[RawMeasurementRecord]] = relationship(
        "RawMeasurementRecord", back_populates="file", cascade="all, delete-orphan"
    )
    stat_measurements: Mapped[list[StatMeasurement]] = relationship(
        "StatMeasurement", back_populates="file", cascade="all, delete-orphan"
    )
    class_counts: Mapped[list[FileClassCount]] = relationship(
        "FileClassCount", back_populates="file", cascade="all, delete-orphan"
    )

    def _directory_segments(self) -> list[str]:
        segments: list[str] = []
        current = self.directory
        while current is not None:
            segments.append(current.name)
            current = current.parent
        return list(reversed(segments))

    @property
    def parent_dir_0(self) -> str | None:
        segments = self._directory_segments()
        return segments[0] if len(segments) > 0 else None

    @property
    def parent_dir_1(self) -> str | None:
        segments = self._directory_segments()
        return segments[1] if len(segments) > 1 else None

    @property
    def parent_dir_2(self) -> str | None:
        segments = self._directory_segments()
        return segments[2] if len(segments) > 2 else None


class MeasurementMetricType(Base):
    __tablename__ = "measurement_metric_types"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    unit: Mapped[str | None] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    items: Mapped[list[MeasurementItem]] = relationship(
        "MeasurementItem", back_populates="metric_type", cascade="all, delete-orphan"
    )


class MeasurementItem(Base):
    __tablename__ = "measurement_items"
    __table_args__ = (
        UniqueConstraint("class_name", "measure_item_key", "metric_type_id", name="uk_item_class_key"),
    )

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    class_name: Mapped[str] = mapped_column(String(64), nullable=False)
    measure_item_key: Mapped[str] = mapped_column(String(64), nullable=False)
    metric_type_id: Mapped[int] = mapped_column(
        ForeignKey("measurement_metric_types.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    metric_type: Mapped[MeasurementMetricType] = relationship(
        "MeasurementMetricType", back_populates="items"
    )
    raw_records: Mapped[list[RawMeasurementRecord]] = relationship(
        "RawMeasurementRecord", back_populates="item"
    )
    stat_measurements: Mapped[list[StatMeasurement]] = relationship(
        "StatMeasurement", back_populates="item"
    )


class RawMeasurementRecord(Base):
    __tablename__ = "raw_measurement_records"
    __table_args__ = (
        UniqueConstraint("file_id", "item_id", "x_index", "y_index", name="uk_raw_file_item_xy"),
    )

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    file_id: Mapped[int] = mapped_column(
        ForeignKey("measurement_files.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    item_id: Mapped[int] = mapped_column(
        ForeignKey("measurement_items.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
    )
    measurable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    x_index: Mapped[int] = mapped_column(Integer, nullable=False)
    y_index: Mapped[int] = mapped_column(Integer, nullable=False)
    x_0: Mapped[float] = mapped_column(DOUBLE, nullable=False)
    y_0: Mapped[float] = mapped_column(DOUBLE, nullable=False)
    x_1: Mapped[float] = mapped_column(DOUBLE, nullable=False)
    y_1: Mapped[float] = mapped_column(DOUBLE, nullable=False)
    value: Mapped[float] = mapped_column(DOUBLE, nullable=False)

    file: Mapped[MeasurementFile] = relationship("MeasurementFile", back_populates="raw_records")
    item: Mapped[MeasurementItem] = relationship("MeasurementItem", back_populates="raw_records")


class StatMeasurement(Base):
    __tablename__ = "stat_measurements"
    __table_args__ = (
        UniqueConstraint("file_id", "item_id", name="uk_stat_file_item"),
    )

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    file_id: Mapped[int] = mapped_column(
        ForeignKey("measurement_files.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False
    )
    item_id: Mapped[int] = mapped_column(
        ForeignKey("measurement_items.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
    )

    file: Mapped[MeasurementFile] = relationship("MeasurementFile", back_populates="stat_measurements")
    item: Mapped[MeasurementItem] = relationship("MeasurementItem", back_populates="stat_measurements")
    values: Mapped[list[StatMeasurementValue]] = relationship(
        "StatMeasurementValue", back_populates="stat_measurement", cascade="all, delete-orphan"
    )


class StatValueType(Base):
    __tablename__ = "stat_value_types"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    values: Mapped[list[StatMeasurementValue]] = relationship(
        "StatMeasurementValue", back_populates="value_type"
    )


class StatMeasurementValue(Base):
    __tablename__ = "stat_measurement_values"
    __table_args__ = (
        PrimaryKeyConstraint("stat_measurement_id", "value_type_id", name="pk_stat_values"),
    )

    stat_measurement_id: Mapped[int] = mapped_column(
        ForeignKey("stat_measurements.id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    value_type_id: Mapped[int] = mapped_column(
        ForeignKey("stat_value_types.id", ondelete="RESTRICT", onupdate="CASCADE"),
        primary_key=True,
    )
    value: Mapped[float] = mapped_column(DOUBLE, nullable=False)

    stat_measurement: Mapped[StatMeasurement] = relationship(
        "StatMeasurement", back_populates="values"
    )
    value_type: Mapped[StatValueType] = relationship("StatValueType", back_populates="values")


class DetectionClass(Base):
    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    file_counts: Mapped[list[FileClassCount]] = relationship(
        "FileClassCount", back_populates="det_class", cascade="all, delete-orphan"
    )


class FileClassCount(Base):
    __tablename__ = "file_class_counts"
    __table_args__ = (
        PrimaryKeyConstraint("file_id", "class_id", name="pk_file_class_counts"),
    )

    file_id: Mapped[int] = mapped_column(
        ForeignKey("measurement_files.id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True
    )
    class_id: Mapped[int] = mapped_column(
        ForeignKey("classes.id", ondelete="RESTRICT", onupdate="CASCADE"), primary_key=True
    )
    cnt: Mapped[int] = mapped_column(Integer, nullable=False)

    file: Mapped[MeasurementFile] = relationship("MeasurementFile", back_populates="class_counts")
    det_class: Mapped[DetectionClass] = relationship("DetectionClass", back_populates="file_counts")


__all__ = [
    "Base",
    "FileStatus",
    "MeasurementNode",
    "MeasurementModule",
    "MeasurementVersion",
    "MeasurementDirectory",
    "MeasurementFile",
    "MeasurementMetricType",
    "MeasurementItem",
    "RawMeasurementRecord",
    "StatMeasurement",
    "StatValueType",
    "StatMeasurementValue",
    "DetectionClass",
    "FileClassCount",
]
