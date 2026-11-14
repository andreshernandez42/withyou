from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

EVENT_TYPES = "^(EARTHQUAKE|LANDSLIDE|FLOOD|FIRE|VOLCANIC_EVENT|OTHER)$"
SAFETY_STATES = "^(SAFE|HELP_REQUIRED|UNABLE_TO_EXIT)$"
COMMUNITY_RESULTS = "^(LOCATED_SAFE|LOCATED_HELP_REQUIRED|NOT_FOUND|CANNOT_VERIFY)$"


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=10, max_length=200)
    is_minor: bool = False
    locale: str = Field(default="es-CO", max_length=10)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=20)


class DeviceIn(BaseModel):
    device_uid: str = Field(min_length=4, max_length=160)
    platform: str = Field(default="android", pattern="^(android|ios|web|other)$")
    device_name: str = Field(default="mobile", max_length=120)
    push_token: str | None = None


class ProfileUpdateIn(BaseModel):
    community_opt_in: bool | None = None
    locale: str | None = Field(default=None, max_length=10)


class ContactCreate(BaseModel):
    contact_name: str = Field(min_length=2, max_length=160)
    contact_email: EmailStr
    can_receive_sos: bool = True
    can_view_checkpoint: bool = False
    can_request_welfare: bool = True
    quorum_weight: int = Field(default=1, ge=1, le=5)


class ContactAccept(BaseModel):
    accept: bool = True


class ContactUpdate(BaseModel):
    can_receive_sos: bool | None = None
    can_view_checkpoint: bool | None = None
    can_request_welfare: bool | None = None
    quorum_weight: int | None = Field(default=None, ge=1, le=5)


class PolicyIn(BaseModel):
    name: str = Field(default="Política principal", max_length=120)
    event_type: str = Field(default="GENERAL", max_length=60)
    requires_official_event: bool = False
    quorum_required: int = Field(default=2, ge=1, le=10)
    allow_coarse_location: bool = True
    allow_exact_location: bool = True
    allow_recent_route: bool = False
    allow_community_check: bool = False
    release_on_official_event_no_response: bool = True
    release_after_quorum: bool = True
    access_ttl_minutes: int = Field(default=60, ge=5, le=1440)
    active: bool = True


class CheckpointIn(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_m: float | None = Field(default=None, ge=0)
    battery_pct: float | None = Field(default=None, ge=0, le=100)
    network_type: str | None = Field(default=None, max_length=40)
    movement_state: str | None = Field(default=None, max_length=40)
    device_id: str | None = None
    created_at: datetime | None = None


class TestEventIn(BaseModel):
    type: str = Field(default="EARTHQUAKE", pattern=EVENT_TYPES)
    source: str = Field(default="TEST", max_length=80)
    severity: str = Field(default="SEVERE", max_length=30)
    certainty: str = Field(default="OBSERVED", max_length=30)
    urgency: str = Field(default="IMMEDIATE", max_length=30)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    radius_km: float = Field(default=80, gt=0, le=1000)
    magnitude: float | None = Field(default=None, ge=0, le=10)
    depth_km: float | None = Field(default=None, ge=0, le=1000)
    external_id: str | None = Field(default=None, max_length=160)
    starts_at: datetime | None = None


class SafetyResponseIn(BaseModel):
    status: str = Field(pattern=SAFETY_STATES)
    event_id: str | None = None
    welfare_check_id: str | None = None
    message: str | None = Field(default=None, max_length=500)


class WelfareRequestIn(BaseModel):
    subject_user_id: str
    reason: str = Field(default="No he podido comunicarme con esta persona", max_length=500)


class WelfareConfirmIn(BaseModel):
    response: str = Field(pattern="^(ALSO_CONCERNED|NOT_CONCERNED|CANNOT_CONFIRM)$")


class WelfareCloseIn(BaseModel):
    outcome: str = Field(pattern="^(LOCATED_SAFE|LOCATED_HELP_REQUIRED|CLOSED_OTHER)$")


class CommunityVerificationIn(BaseModel):
    result: str = Field(pattern=COMMUNITY_RESULTS)
    approximate_distance_m: int | None = Field(default=None, ge=0)


class CommunityNearbyQuery(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    radius_km: float = Field(default=5, gt=0, le=50)


class CaseCreateIn(BaseModel):
    subject_user_id: str
    welfare_check_id: str | None = None
    notes: str | None = Field(default=None, max_length=2000)


class CaseUpdateIn(BaseModel):
    status: str = Field(pattern="^(OPEN|VERIFICATION_IN_PROGRESS|INSTITUTIONAL_REFERENCE_ADDED|LOCATED_SAFE|LOCATED_HELP_REQUIRED|CLOSED)$")
    notes: str | None = Field(default=None, max_length=2000)


class InstitutionalReferenceIn(BaseModel):
    source: str = Field(max_length=80)
    reference_number: str = Field(max_length=160)
    status: str = Field(default="REGISTERED", max_length=80)
    external_url: str | None = None


class SafetyModeIn(BaseModel):
    notify_contact_ids: list[str] = Field(default_factory=list, max_length=20)
    boost_minutes: int = Field(default=30, ge=1, le=360)
    silent: bool = False


class SOSIn(BaseModel):
    message: str | None = Field(default=None, max_length=500)
    personal_safety_session_id: str | None = None


class ExperimentRunIn(BaseModel):
    experiment_type: str = Field(max_length=60)
    scenario: str = Field(max_length=120)
    parameters: dict = Field(default_factory=dict)
    metrics: dict = Field(default_factory=dict)
    notes: str | None = Field(default=None, max_length=2000)
