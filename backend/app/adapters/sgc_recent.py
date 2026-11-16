"""Catálogo público de sismos recientes del Servicio Geológico Colombiano."""
import asyncio
from datetime import datetime, timedelta, timezone
import math

import httpx

from app.core.config import settings
from app.services.timeutils import as_utc, utcnow

URL = "https://api.sgc.gov.co/biweekly/biweekly_earthquakes"
BOGOTA = timezone(timedelta(hours=-5))


def normalize(payload):
    if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
        raise ValueError("Respuesta del SGC sin una colección de sismos válida")
    features = payload.get("features")
    if not isinstance(features, list) or len(features) > 5000:
        raise ValueError("Resultado inválido del SGC")
    metadata = payload.get("metadata")
    if isinstance(metadata, dict) and metadata.get("count", len(features)) != len(features):
        raise ValueError("Resultado incompleto del SGC")
    records = []
    invalid = 0
    for item in features:
        if not isinstance(item, dict) or not isinstance(item.get("properties"), dict):
            invalid += 1
            continue
        props = item["properties"]
        if props.get("agency") != "SGC" or props.get("type") != "earthquake":
            continue
        try:
            geometry = item["geometry"]
            if geometry["type"] != "Point":
                raise ValueError("Geometría inválida")
            lon, lat, *_ = geometry["coordinates"]
            magnitude = props["mag"]
            if not all(type(v) in (float, int) and math.isfinite(v) for v in (lon, lat, magnitude)):
                raise ValueError("Valores inválidos")
            if not (-180 <= lon <= 180 and -90 <= lat <= 90 and -10 <= magnitude <= 10):
                raise ValueError("Valores fuera de rango")
            event_id = item["id"]
            if not isinstance(event_id, str) or not event_id.strip() or len(event_id) > 160:
                raise ValueError("Identificador inválido")
            occurred = as_utc(datetime.fromisoformat(props["utcTime"].replace("Z", "+00:00")))
            depth = props.get("depth")
        except (TypeError, ValueError, KeyError, AttributeError, OverflowError):
            invalid += 1
            continue
        records.append({
            "external_id": event_id, "source": "SGC", "type": "EARTHQUAKE",
            "latitude": lat, "longitude": lon, "magnitude": magnitude,
            "depth_km": depth if type(depth) in (int, float) and math.isfinite(depth) else None,
            "starts_at": occurred, "raw": item,
        })
    if invalid and not records:
        raise ValueError("El SGC devolvió registros que no se pudieron interpretar")
    return sorted(records, key=lambda item: item["starts_at"], reverse=True)


async def fetch_window(client, start, end):
    params = {
        "startdate": start.astimezone(BOGOTA).strftime("%Y-%m-%dT%H:%M:%S"),
        "enddate": end.astimezone(BOGOTA).strftime("%Y-%m-%dT%H:%M:%S"),
    }
    for attempt in range(3):
        try:
            response = await client.get(URL, params=params)
            response.raise_for_status()
            return normalize(response.json())
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in (408, 429, 500, 502, 503, 504) or attempt == 2:
                raise
        except (httpx.TransportError, ValueError):
            if attempt == 2:
                raise
        await asyncio.sleep(0.5 * 2**attempt)


class SgcRecentAdapter:
    async def fetch_recent(self, limit=100):
        end = utcnow()
        start = end - timedelta(minutes=settings.earthquake_max_age_minutes + 5)
        async with httpx.AsyncClient(timeout=httpx.Timeout(8, connect=4)) as client:
            return await asyncio.wait_for(fetch_window(client, start, end), timeout=28)
