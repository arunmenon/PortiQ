"""Pydantic schemas for vessel module request/response validation."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from src.models.enums import (
    AisProvider,
    NavigationStatus,
    PortCallStatus,
    VesselStatus,
    VesselType,
)

# ---------------------------------------------------------------------------
# Vessel
# ---------------------------------------------------------------------------


class VesselCreate(BaseModel):
    imo_number: str = Field(..., min_length=7, max_length=7)
    name: str = Field(..., min_length=1, max_length=255)
    vessel_type: VesselType = VesselType.OTHER
    mmsi: str | None = Field(None, max_length=9)
    flag_state: str | None = Field(None, max_length=3)
    gross_tonnage: Decimal | None = None
    deadweight_tonnage: Decimal | None = None
    length_overall_m: Decimal | None = None
    beam_m: Decimal | None = None
    year_built: int | None = None
    crew_size: int | None = None
    owner_organization_id: uuid.UUID | None = None
    manager_organization_id: uuid.UUID | None = None
    metadata_extra: dict = Field(default_factory=dict)


class VesselUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    vessel_type: VesselType | None = None
    mmsi: str | None = Field(None, max_length=9)
    flag_state: str | None = Field(None, max_length=3)
    gross_tonnage: Decimal | None = None
    deadweight_tonnage: Decimal | None = None
    length_overall_m: Decimal | None = None
    beam_m: Decimal | None = None
    year_built: int | None = None
    crew_size: int | None = None
    owner_organization_id: uuid.UUID | None = None
    manager_organization_id: uuid.UUID | None = None
    last_known_port: str | None = Field(None, max_length=10)
    last_supply_date: datetime | None = None
    metadata_extra: dict | None = None


class VesselResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    imo_number: str
    mmsi: str | None
    name: str
    vessel_type: VesselType
    status: VesselStatus
    flag_state: str | None
    gross_tonnage: Decimal | None
    deadweight_tonnage: Decimal | None
    length_overall_m: Decimal | None
    beam_m: Decimal | None
    year_built: int | None
    crew_size: int | None
    owner_organization_id: uuid.UUID | None
    manager_organization_id: uuid.UUID | None
    last_known_port: str | None
    last_supply_date: datetime | None
    metadata_extra: dict
    created_at: datetime
    updated_at: datetime


class VesselListResponse(BaseModel):
    items: list[VesselResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Position
# ---------------------------------------------------------------------------


class PositionRecord(BaseModel):
    latitude: Decimal
    longitude: Decimal
    speed_knots: Decimal | None = None
    course: Decimal | None = None
    heading: Decimal | None = None
    navigation_status: NavigationStatus | None = None
    source: AisProvider | None = None
    signal_confidence: Decimal | None = None
    recorded_at: datetime
    raw_data: dict | None = None


class PositionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vessel_id: uuid.UUID
    latitude: Decimal
    longitude: Decimal
    speed_knots: Decimal | None
    course: Decimal | None
    heading: Decimal | None
    navigation_status: NavigationStatus | None
    source: AisProvider | None
    signal_confidence: Decimal | None
    recorded_at: datetime
    raw_data: dict | None
    created_at: datetime


# ---------------------------------------------------------------------------
# Port Call
# ---------------------------------------------------------------------------


class PortCallCreate(BaseModel):
    port_code: str = Field(..., max_length=10)
    port_name: str | None = Field(None, max_length=255)
    status: PortCallStatus = PortCallStatus.APPROACHING
    eta: datetime | None = None
    ata: datetime | None = None
    atd: datetime | None = None
    berth: str | None = Field(None, max_length=100)
    pilot_time: datetime | None = None
    distance_nm: Decimal | None = None
    eta_confidence: Decimal | None = None
    source: AisProvider | None = None


class ManualPortCallCreate(BaseModel):
    """Schema for manual port call creation via the API."""

    vessel_id: uuid.UUID
    port_code: str = Field(..., max_length=10)
    port_name: str | None = Field(None, max_length=255)
    eta: datetime
    berth: str | None = Field(None, max_length=100)
    previous_port_code: str | None = Field(None, max_length=10)
    next_port_code: str | None = Field(None, max_length=10)


class PortCallUpdate(BaseModel):
    """Schema for updating a port call."""

    vessel_id: uuid.UUID | None = None
    port_code: str | None = Field(None, max_length=10)
    port_name: str | None = Field(None, max_length=255)
    eta: datetime | None = None
    berth: str | None = Field(None, max_length=100)
    previous_port_code: str | None = Field(None, max_length=10)
    next_port_code: str | None = Field(None, max_length=10)
    status: PortCallStatus | None = None


class PortCallResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vessel_id: uuid.UUID
    port_code: str
    port_name: str | None
    status: PortCallStatus
    eta: datetime | None
    ata: datetime | None
    atd: datetime | None
    berth: str | None
    pilot_time: datetime | None
    distance_nm: Decimal | None
    eta_confidence: Decimal | None
    source: AisProvider | None
    raw_data: dict | None
    created_at: datetime
    updated_at: datetime


class PortCallListResponse(BaseModel):
    items: list[PortCallResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Bulk import
# ---------------------------------------------------------------------------


class BulkImportRequest(BaseModel):
    vessels: list[VesselCreate]


class BulkImportResponse(BaseModel):
    created: int
    skipped: int
    errors: list[str]


# ---------------------------------------------------------------------------
# Provider health
# ---------------------------------------------------------------------------


class ProviderHealthResponse(BaseModel):
    provider: str
    healthy: bool
    message: str


# ---------------------------------------------------------------------------
# Task enqueue
# ---------------------------------------------------------------------------


class TaskEnqueuedResponse(BaseModel):
    message: str
    vessel_id: str
    days: int | None = None
