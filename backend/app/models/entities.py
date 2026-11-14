from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import (
    String, DateTime, Boolean, Integer, Float, Text, ForeignKey,
    UniqueConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.services.timeutils import utcnow


def uuid4s() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4s)
    full_name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default="USER", index=True)
    is_minor: Mapped[bool] = mapped_column(Boolean, default=False)
    community_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)
    locale: Mapped[str] = mapped_column(String(10), default="es-CO")
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class RefreshSession(Base):
    __tablename__ = "refresh_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4s)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (UniqueConstraint("user_id", "device_uid", name="uq_device_user_uid"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4s)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    device_uid: Mapped[str] = mapped_column(String(160), index=True)
    platform: Mapped[str] = mapped_column(String(30), default="android")
    device_name: Mapped[str] = mapped_column(String(120), default="mobile")
    push_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TrustedContact(Base):
    __tablename__ = "trusted_contacts"
    __table_args__ = (UniqueConstraint("owner_user_id", "contact_email", name="uq_owner_contact_email"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4s)
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    contact_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    contact_name: Mapped[str] = mapped_column(String(160))
    contact_email: Mapped[str] = mapped_column(String(254))
    status: Mapped[str] = mapped_column(String(30), default="PENDING", index=True)
    can_receive_sos: Mapped[bool] = mapped_column(Boolean, default=True)
    can_view_checkpoint: Mapped[bool] = mapped_column(Boolean, default=False)
    can_request_welfare: Mapped[bool] = mapped_column(Boolean, default=True)
    quorum_weight: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ConsentPolicy(Base):
    __tablename__ = "consent_policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4s)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120), default="Política principal")
    event_type: Mapped[str] = mapped_column(String(60), default="GENERAL")
    requires_official_event: Mapped[bool] = mapped_column(Boolean, default=False)
    quorum_required: Mapped[int] = mapped_column(Integer, default=2)
    allow_coarse_location: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_exact_location: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_recent_route: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_community_check: Mapped[bool] = mapped_column(Boolean, default=False)
    release_on_official_event_no_response: Mapped[bool] = mapped_column(Boolean, default=True)
    release_after_quorum: Mapped[bool] = mapped_column(Boolean, default=True)
    access_ttl_minutes: Mapped[int] = mapped_column(Integer, default=60)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Checkpoint(Base):
    __tablename__ = "checkpoints"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4s)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    device_id: Mapped[str | None] = mapped_column(ForeignKey("devices.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    encrypted_location: Mapped[str] = mapped_column(Text)
    coarse_lat: Mapped[float] = mapped_column(Float)
    coarse_lon: Mapped[float] = mapped_column(Float)
    accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    battery_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    network_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    movement_state: Mapped[str | None] = mapped_column(String(40), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    incident_hold: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    hold_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    hold_actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    hold_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EmergencyEvent(Base):
    __tablename__ = "emergency_events"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_event_source_external"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4s)
    external_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(80), index=True)
    type: Mapped[str] = mapped_column(String(60), index=True)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", index=True)
    severity: Mapped[str] = mapped_column(String(30), default="UNKNOWN")
    certainty: Mapped[str] = mapped_column(String(30), default="UNKNOWN")
    urgency: Mapped[str] = mapped_column(String(30), default="UNKNOWN")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    radius_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    magnitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    depth_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    area_geojson: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_test: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WelfareCheck(Base):
    __tablename__ = "welfare_checks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4s)
    subject_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    requester_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    event_id: Mapped[str | None] = mapped_column(ForeignKey("emergency_events.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="CHECK_REQUESTED", index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    quorum_required: Mapped[int] = mapped_column(Integer, default=1)
    quorum_count: Mapped[int] = mapped_column(Integer, default=0)
    last_checkpoint_id: Mapped[str | None] = mapped_column(ForeignKey("checkpoints.id"), nullable=True)
    community_active: Mapped[bool] = mapped_column(Boolean, default=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WelfareConfirmation(Base):
    __tablename__ = "welfare_confirmations"
    __table_args__ = (UniqueConstraint("welfare_check_id", "contact_user_id", name="uq_welfare_contact"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4s)
    welfare_check_id: Mapped[str] = mapped_column(ForeignKey("welfare_checks.id"), index=True)
    contact_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    response: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LocationAccessGrant(Base):
    __tablename__ = "location_access_grants"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4s)
    subject_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    grantee_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    level: Mapped[str] = mapped_column(String(20), default="COARSE")
    reason: Mapped[str] = mapped_column(String(160))
    source_type: Mapped[str] = mapped_column(String(40))
    source_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (Index("ix_location_grant_active", "subject_user_id", "grantee_user_id", "expires_at"),)


class SafetyStatus(Base):
    __tablename__ = "safety_statuses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4s)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    event_id: Mapped[str | None] = mapped_column(ForeignKey("emergency_events.id"), nullable=True, index=True)
    welfare_check_id: Mapped[str | None] = mapped_column(ForeignKey("welfare_checks.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DisappearanceCase(Base):
    __tablename__ = "disappearance_cases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4s)
    subject_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    opened_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    welfare_check_id: Mapped[str | None] = mapped_column(ForeignKey("welfare_checks.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="OPEN", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class InstitutionalReference(Base):
    __tablename__ = "institutional_references"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4s)
    case_id: Mapped[str] = mapped_column(ForeignKey("disappearance_cases.id"), index=True)
    source: Mapped[str] = mapped_column(String(80))
    reference_number: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(80), default="REGISTERED")
    external_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CommunityVerification(Base):
    __tablename__ = "community_verifications"
    __table_args__ = (UniqueConstraint("welfare_check_id", "verifier_user_id", name="uq_community_check_verifier"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4s)
    welfare_check_id: Mapped[str] = mapped_column(ForeignKey("welfare_checks.id"), index=True)
    verifier_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    result: Mapped[str] = mapped_column(String(60))
    approximate_distance_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4s)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(60), index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(30), default="IN_APP")
    status: Mapped[str] = mapped_column(String(30), default="PENDING", index=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4s)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    resource_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    result: Mapped[str] = mapped_column(String(30), default="SUCCESS")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class PersonalSafetySession(Base):
    __tablename__ = "personal_safety_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4s)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="ACTIVE", index=True)
    silent: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sampling_boost_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notify_contacts_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class SOSSession(Base):
    __tablename__ = "sos_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4s)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    personal_safety_session_id: Mapped[str | None] = mapped_column(ForeignKey("personal_safety_sessions.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", index=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    checkpoint_id: Mapped[str | None] = mapped_column(ForeignKey("checkpoints.id"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OfficialSourceSync(Base):
    __tablename__ = "official_source_syncs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4s)
    source: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(40), default="UNKNOWN")
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_cutoff_date: Mapped[str | None] = mapped_column(String(120), nullable=True)
    records_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)


class ExperimentRun(Base):
    __tablename__ = "experiment_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4s)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    experiment_type: Mapped[str] = mapped_column(String(60), index=True)
    scenario: Mapped[str] = mapped_column(String(120))
    parameters_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    metrics_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
