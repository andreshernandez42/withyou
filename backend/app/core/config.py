from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _list(name: str, default: str) -> tuple[str, ...]:
    raw = os.getenv(name, default)
    return tuple(x.strip() for x in raw.split(",") if x.strip())


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "With You - Plataforma Resiliente")
    env: str = os.getenv("APP_ENV", "development")
    api_prefix: str = "/api/v1"
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./withyou.db")
    token_secret: str = os.getenv("TOKEN_SECRET", "CHANGE-ME-DEMO-ONLY")
    access_token_minutes: int = _int("ACCESS_TOKEN_MINUTES", 30)
    refresh_token_days: int = _int("REFRESH_TOKEN_DAYS", 14)
    field_encryption_key: str = os.getenv("FIELD_ENCRYPTION_KEY", "")
    allow_test_endpoints: bool = _bool("ALLOW_TEST_ENDPOINTS", True)
    auto_create_schema: bool = _bool("AUTO_CREATE_SCHEMA", True)
    allowed_origins: tuple[str, ...] = _list("ALLOWED_ORIGINS", "http://localhost,http://localhost:3000")
    trusted_hosts: tuple[str, ...] = _list("TRUSTED_HOSTS", "localhost,127.0.0.1,testserver")

    checkpoint_ttl_hours: int = _int("CHECKPOINT_TTL_HOURS", 24)
    incident_hold_hours: int = _int("INCIDENT_HOLD_HOURS", 72)
    location_grant_minutes: int = _int("LOCATION_GRANT_MINUTES", 60)
    safety_check_timeout_seconds: int = _int("SAFETY_CHECK_TIMEOUT_SECONDS", 300)
    welfare_check_ttl_hours: int = _int("WELFARE_CHECK_TTL_HOURS", 2)
    cleanup_interval_seconds: int = _int("CLEANUP_INTERVAL_SECONDS", 60)
    community_confirmation_threshold: int = _int("COMMUNITY_CONFIRMATION_THRESHOLD", 2)

    earthquake_min_magnitude: float = _float("EARTHQUAKE_MIN_MAGNITUDE", 4.5)
    earthquake_max_distance_km: float = _float("EARTHQUAKE_MAX_DISTANCE_KM", 150.0)
    earthquake_max_age_minutes: int = _int("EARTHQUAKE_MAX_AGE_MINUTES", 30)

    earthquake_checkpoint_max_age_minutes: int = _int("EARTHQUAKE_CHECKPOINT_MAX_AGE_MINUTES", 60)

    sgc_query_url: str = os.getenv(
        "SGC_QUERY_URL",
        "https://srvags.sgc.gov.co/arcgis/rest/services/catalogo_sismos/catalogo_de_sismos_2/MapServer/0/query",
    )
    # Fecha real del sismo en la capa ArcGIS (milisegundos o Date).
    sgc_time_field: str = os.getenv("SGC_TIME_FIELD", "ESP_FECHA_LONG")
    # Se puede encender tras verificar que la fuente oficial publica eventos recientes.
    sgc_poll_enabled: bool = _bool("SGC_POLL_ENABLED", False)
    sgc_poll_interval_seconds: int = _int("SGC_POLL_INTERVAL_SECONDS", 60)
    sirdec_soda_url: str = os.getenv("SIRDEC_SODA_URL", "https://www.datos.gov.co/resource/8hqm-7fdt.json")
    sirdec_public_portal_url: str = os.getenv(
        "SIRDEC_PUBLIC_PORTAL_URL",
        "https://siclico.medicinalegal.gov.co/consultasPublicas/Desaparecidos.xhtml",
    )
    sirdec_dataset_cutoff: str = os.getenv("SIRDEC_DATASET_CUTOFF", "junio de 2026")
    ideam_json_url: str = os.getenv("IDEAM_JSON_URL", "")
    ungrd_portal_url: str = os.getenv("UNGRD_PORTAL_URL", "https://portal.gestiondelriesgo.gov.co/")

    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    celery_enabled: bool = _bool("CELERY_ENABLED", False)
    fcm_enabled: bool = _bool("FCM_ENABLED", False)
    firebase_credentials_path: str = os.getenv("FIREBASE_CREDENTIALS_PATH", "")

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"


settings = Settings()


def validate_runtime_settings() -> None:
    if settings.is_production:
        if settings.token_secret.startswith("CHANGE-ME") or len(settings.token_secret) < 32:
            raise RuntimeError("TOKEN_SECRET inseguro para producción")
        if not settings.field_encryption_key:
            raise RuntimeError("FIELD_ENCRYPTION_KEY es obligatorio en producción")
        if settings.allow_test_endpoints:
            raise RuntimeError("ALLOW_TEST_ENDPOINTS debe estar deshabilitado en producción")
        if settings.auto_create_schema:
            raise RuntimeError("AUTO_CREATE_SCHEMA debe estar deshabilitado en producción; use Alembic")
