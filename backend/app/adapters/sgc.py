"""Adaptador de lectura ArcGIS REST del SGC.

No supone que OBJECTID representa la fecha del sismo y nunca convierte un
catálogo histórico en una alerta reciente. La URL debe apuntar a una *capa*
ArcGIS de puntos con una columna de fecha validada en el servidor del SGC.
"""
from __future__ import annotations

import asyncio
import math
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

import httpx

from app.core.config import settings

CANDIDATES = {
    "magnitude": ["ESP_MAGNITUD", "magnitud", "MAGNITUD", "magnitude", "Magnitude", "MAG", "mag"],
    "depth": ["ESP_PROFUNDIDAD", "profundidad", "PROFUNDIDAD", "depth", "Depth", "prof"],
    "external_id": ["OBJECTID", "objectid", "ESP_ID_EVENTO_TXT", "id", "ID", "evento", "event_id"],
    "time": ["ESP_FECHA_LONG", "ESP_FECHA_TXT", "ESP_FECHA", "fecha", "FECHA", "timestamp", "time", "fecha_hora", "FECHA_HORA", "date"],
}


def _first(attrs: dict, names: list[str]):
    lower = {k.lower(): v for k, v in attrs.items()}
    for name in names:
        value = attrs.get(name, lower.get(name.lower()))
        if value is not None and value != "":
            return value
    return None


def _parse_time(value):
    if value is None or value == "":
        return None
    try:
        number = float(value)
        if not math.isfinite(number):
            return None
        # ArcGIS normalmente serializa fechas como epoch en milisegundos.
        seconds = number / 1000 if abs(number) > 10_000_000_000 else number
        return datetime.fromtimestamp(seconds, tz=timezone.utc)
    except (TypeError, ValueError, OverflowError, OSError):
        pass
    try:
        date = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        return date if date.tzinfo else date.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


class SgcEarthquakeAdapter:
    def __init__(self, query_url: str | None = None):
        self.query_url = query_url or settings.sgc_query_url
        parsed = urlsplit(self.query_url)
        if parsed.scheme != "https" or not parsed.netloc.endswith(".sgc.gov.co"):
            raise ValueError("La fuente configurada debe usar HTTPS y un dominio oficial del SGC")
        if not parsed.path.rstrip("/").endswith("/query"):
            raise ValueError("SGC_QUERY_URL debe terminar en /<id_capa>/query")

    async def _get_json(self, client: httpx.AsyncClient, url: str, params: dict) -> dict:
        for attempt in range(3):
            try:
                response = await client.get(url, params=params)
                if response.status_code in (429, 500, 502, 503, 504):
                    response.raise_for_status()
                response.raise_for_status()
                if "json" not in response.headers.get("content-type", "").lower():
                    raise ValueError("El SGC no devolvió JSON; no se procesaron eventos")
                payload = response.json()
                if not isinstance(payload, dict) or payload.get("error"):
                    raise ValueError(f"Respuesta ArcGIS no válida: {payload.get('error') if isinstance(payload, dict) else 'formato'}")
                return payload
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout, httpx.HTTPStatusError) as exc:
                retryable = not isinstance(exc, httpx.HTTPStatusError) or exc.response.status_code in (429, 500, 502, 503, 504)
                if attempt == 2 or not retryable:
                    raise
                await asyncio.sleep(0.3 * (attempt + 1))
        raise RuntimeError("No se pudo consultar la fuente")

    async def fetch_recent(self, limit: int = 100) -> list[dict]:
        """Consulta los últimos minutos por FECHA, nunca por OBJECTID.

        Si la capa no soporta filtros temporales, falla en cerrado y no genera
        alertas. El límite de IDs evita consultas masivas accidentales.
        """
        limit = max(1, min(limit, 200))
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.earthquake_max_age_minutes + 5)
        layer_url = self.query_url.rsplit("/query", 1)[0]
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            metadata = await self._get_json(client, layer_url, {"f": "json"})
            fields = {field.get("name"): field.get("type") for field in metadata.get("fields", [])}
            if not fields:
                raise ValueError("No se pudo validar el esquema de la capa ArcGIS")
            if metadata.get("geometryType") not in ("esriGeometryPoint", None):
                raise ValueError("La capa configurada no contiene geometrías puntuales")
            time_field = settings.sgc_time_field
            if time_field not in fields:
                raise ValueError(f"La fuente no contiene la columna temporal configurada: {time_field}")
            if fields[time_field] in ("esriFieldTypeDate", "esriFieldTypeTimestampOffset"):
                where = f"{time_field} >= TIMESTAMP '{cutoff.strftime('%Y-%m-%d %H:%M:%S')}'"
            elif fields[time_field] in ("esriFieldTypeDouble", "esriFieldTypeInteger", "esriFieldTypeSingle", "esriFieldTypeBigInteger"):
                where = f"{time_field} >= {int(cutoff.timestamp() * 1000)}"
            else:
                raise ValueError("La columna temporal de SGC no admite un filtro numérico/fecha seguro")
            ids_payload = await self._get_json(client, self.query_url, {"where": where, "returnIdsOnly": "true", "f": "json"})
            ids = ids_payload.get("objectIds")
            if not isinstance(ids, list):
                raise ValueError("El SGC no devolvió IDs para la consulta temporal")
            if len(ids) > 500:
                raise ValueError("Demasiados resultados recientes: revisar fuente/intervalo antes de notificar")
            rows = []
            for start in range(0, len(ids), 100):
                payload = await self._get_json(client, self.query_url, {
                    "objectIds": ",".join(str(value) for value in ids[start:start + 100]),
                    "outFields": "*", "returnGeometry": "true", "outSR": "4326", "f": "json",
                })
                rows.extend(self.normalize_arcgis(payload))
            rows.sort(key=lambda value: value["starts_at"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
            return rows[:limit]

    def normalize_arcgis(self, payload: dict) -> list[dict]:
        rows: list[dict] = []
        for feature in payload.get("features", []):
            attrs = feature.get("attributes") or feature.get("properties") or {}
            geom = feature.get("geometry") or {}
            x, y = geom.get("x"), geom.get("y")
            if (x is None or y is None) and isinstance(geom.get("coordinates"), list) and len(geom["coordinates"]) >= 2:
                x, y = geom["coordinates"][:2]
            try:
                lon, lat = float(x), float(y)
                if not all(map(math.isfinite, (lat, lon))) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
                    continue
            except (TypeError, ValueError):
                continue
            def numeric(field):
                try:
                    value = _first(attrs, CANDIDATES[field])
                    result = float(value) if value is not None else None
                    return result if result is not None and math.isfinite(result) else None
                except (TypeError, ValueError):
                    return None
            external_id = _first(attrs, CANDIDATES["external_id"])
            rows.append({
                "external_id": str(external_id) if external_id is not None else None,
                "source": "SGC", "type": "EARTHQUAKE", "latitude": lat, "longitude": lon,
                "magnitude": numeric("magnitude"), "depth_km": numeric("depth"),
                "starts_at": _parse_time(_first(attrs, [settings.sgc_time_field, *CANDIDATES["time"]])), "raw": attrs,
            })
        return rows
