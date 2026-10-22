from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    is_minor: bool = False

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class ContactCreate(BaseModel):
    contact_name: str
    contact_email: EmailStr
    can_receive_sos: bool = True
    can_view_checkpoint: bool = False
    can_request_welfare: bool = True
    quorum_weight: int = 1

class ContactAccept(BaseModel):
    accept: bool = True

class PolicyIn(BaseModel):
    name: str = "Política principal"
    event_type: str = "GENERAL"
    requires_official_event: bool = False
    quorum_required: int = Field(default=2, ge=1, le=10)
    allow_exact_location: bool = True
    allow_recent_route: bool = False

class CheckpointIn(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_m: float | None = Field(default=None, ge=0)
    battery_pct: float | None = Field(default=None, ge=0, le=100)
    network_type: str | None = None
    movement_state: str | None = None
    created_at: datetime | None = None

class TestEventIn(BaseModel):
    type: str = "EARTHQUAKE"
    source: str = "TEST"
    severity: str = "SEVERE"
    certainty: str = "OBSERVED"
    urgency: str = "IMMEDIATE"
    latitude: float
    longitude: float
    radius_km: float = Field(default=80, gt=0, le=1000)
    magnitude: float | None = Field(default=None, ge=0, le=10)
    depth_km: float | None = Field(default=None, ge=0)
    external_id: str | None = None

class SafetyResponseIn(BaseModel):
    status: str = Field(pattern="^(SAFE|HELP_REQUIRED|UNABLE_TO_EXIT)$")
    event_id: str | None = None
    welfare_check_id: str | None = None
    message: str | None = None

class WelfareRequestIn(BaseModel):
    subject_user_id: str
    reason: str = "No he podido comunicarme con esta persona"

class WelfareConfirmIn(BaseModel):
    response: str = Field(pattern="^(ALSO_CONCERNED|NOT_CONCERNED|CANNOT_CONFIRM)$")

class CommunityVerificationIn(BaseModel):
    result: str = Field(pattern="^(LOCATED_SAFE|LOCATED_HELP_REQUIRED|NOT_FOUND|CANNOT_VERIFY)$")
    approximate_distance_m: int | None = Field(default=None, ge=0)

class CaseCreateIn(BaseModel):
    subject_user_id: str
    notes: str | None = None

class InstitutionalReferenceIn(BaseModel):
    source: str
    reference_number: str
    status: str = "REGISTERED"
    external_url: str | None = None

class SafetyModeIn(BaseModel):
    notify_contact_ids: list[str] = []
    boost_minutes: int = Field(default=30, ge=1, le=360)
