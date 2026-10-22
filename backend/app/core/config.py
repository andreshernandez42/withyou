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


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "With You - Plataforma Resiliente")
    env: str = os.getenv("APP_ENV", "development")
    api_prefix: str = "/api/v1"
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./withyou.db")
    token_secret: str = os.getenv("TOKEN_SECRET", "CHANGE-ME-DEMO-ONLY")
    token_max_age_seconds: int = _int("TOKEN_MAX_AGE_SECONDS", 43200)
    field_encryption_key: str = os.getenv("FIELD_ENCRYPTION_KEY", "")
    allow_test_endpoints: bool = _bool("ALLOW_TEST_ENDPOINTS", True)
    checkpoint_ttl_hours: int = _int("CHECKPOINT_TTL_HOURS", 24)
    incident_hold_hours: int = _int("INCIDENT_HOLD_HOURS", 72)
    cleanup_interval_seconds: int = _int("CLEANUP_INTERVAL_SECONDS", 60)
    notification_poll_seconds: int = _int("NOTIFICATION_POLL_SECONDS", 5)

    earthquake_min_magnitude: float = _float("EARTHQUAKE_MIN_MAGNITUDE", 4.5)
    earthquake_max_distance_km: float = _float("EARTHQUAKE_MAX_DISTANCE_KM", 150.0)
    earthquake_max_age_minutes: int = _int("EARTHQUAKE_MAX_AGE_MINUTES", 30)

    sgc_query_url: str = os.getenv(
        "SGC_QUERY_URL",
        "https://srvags.sgc.gov.co/arcgis/rest/services/catalogo_sismos/catalogo_de_sismos_2/MapServer/0/query",
    )
    sirdec_soda_url: str = os.getenv(
        "SIRDEC_SODA_URL",
        "https://www.datos.gov.co/resource/8hqm-7fdt.json",
    )
    sirdec_public_portal_url: str = os.getenv(
        "SIRDEC_PUBLIC_PORTAL_URL",
        "https://siclico.medicinalegal.gov.co/consultasPublicas/Desaparecidos.xhtml",
    )
    sirdec_dataset_cutoff: str = os.getenv("SIRDEC_DATASET_CUTOFF", "junio de 2026")
    ideam_json_url: str = os.getenv("IDEAM_JSON_URL", "")
    ungrd_portal_url: str = os.getenv("UNGRD_PORTAL_URL", "https://portal.gestiondelriesgo.gov.co/")


settings = Settings()
