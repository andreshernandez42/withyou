from __future__ import annotations
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Boolean, Integer, Float, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def uuid4s() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4s)
    full_name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    is_minor: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Device(Base):
    __tablename__ = "devices"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4s)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    platform: Mapped[str] = mapped_column(String(30), default="android")
    device_name: Mapped[str] = mapped_column(String(120), default="mobile")
    push_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class TrustedContact(Base):
    __tablename__ = "trusted_contacts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4s)
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    contact_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    contact_name: Mapped[str] = mapped_column(String(160))
    contact_email: Mapped[str] = mapped_column(String(254))
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    can_receive_sos: Mapped[bool] = mapped_column(Boolean, default=True)
    can_view_checkpoint: Mapped[bool] = mapped_column(Boolean, default=False)
    can_request_welfare: Mapped[bool] = mapped_column(Boolean, default=True)
    quorum_weight: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class ConsentPolicy(Base):
    __tablename__ = "consent_policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4s)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120), default="Política principal")
    event_type: Mapped[str] = mapped_column(String(60), default="GENERAL")
    requires_official_event: Mapped[bool] = mapped_column(Boolean, default=False)
    quorum_required: Mapped[int] = mapped_column(Integer, default=2)
    allow_exact_location: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_recent_route: Mapped[bool] = mapped_column(Boolean, default=False)
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
    hold_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class EmergencyEvent(Base):
    __tablename__ = "emergency_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4s)
    external_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(80), index=True)
    type: Mapped[str] = mapped_column(String(60), index=True)
    severity: Mapped[str] = mapped_column(String(30), default="UNKNOWN")
    certainty: Mapped[str] = mapped_column(String(30), default="UNKNOWN")
    urgency: Mapped[str] = mapped_column(String(30), default="UNKNOWN")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    radius_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    magnitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    depth_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_test: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class WelfareCheck(Base):
    __tablename__ = "welfare_checks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4s)
    subject_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    requester_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    event_id: Mapped[str | None] = mapped_column(ForeignKey("emergency_events.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="CHECK_REQUESTED", index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    quorum_required: Mapped[int] = mapped_column(Integer, default=1)
    quorum_count: Mapped[int] = mapped_column(Integer, default=0)
    last_checkpoint_id: Mapped[str | None] = mapped_column(ForeignKey("checkpoints.id"), nullable=True)

class WelfareConfirmation(Base):
    __tablename__ = "welfare_confirmations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4s)
    welfare_check_id: Mapped[str] = mapped_column(ForeignKey("welfare_checks.id"), index=True)
    contact_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    response: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class SafetyStatus(Base):
    __tablename__ = "safety_statuses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4s)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    event_id: Mapped[str | None] = mapped_column(ForeignKey("emergency_events.id"), nullable=True)
    welfare_check_id: Mapped[str | None] = mapped_column(ForeignKey("welfare_checks.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class DisappearanceCase(Base):
    __tablename__ = "disappearance_cases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4s)
    subject_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    opened_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(50), default="OPEN")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class PersonalSafetySession(Base):
    __tablename__ = "personal_safety_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4s)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="ACTIVE")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sampling_boost_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notify_contacts_json: Mapped[str | None] = mapped_column(Text, nullable=True)

class OfficialSourceSync(Base):
    __tablename__ = "official_source_syncs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4s)
    source: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(40), default="UNKNOWN")
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_cutoff_date: Mapped[str | None] = mapped_column(String(120), nullable=True)
    records_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
