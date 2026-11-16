"""SGC earthquake catalogue ingestion; EPIS petroleum layers are not alerts."""
from __future__ import annotations
import asyncio
import math
from datetime import datetime, timedelta, timezone
import httpx
from app.core.config import settings

CANDIDATES = {
    'magnitude': ['ESP_MAGNITUD', 'magnitud', 'MAGNITUD', 'magnitude', 'Magnitude', 'MAG', 'mag'],
    'depth': ['ESP_PROFUNDIDAD', 'profundidad', 'PROFUNDIDAD', 'depth', 'Depth', 'prof'],
    'external_id': ['ESP_ID_EVENTO_TXT', 'event_id', 'evento', 'id', 'ID', 'OBJECTID', 'objectid'],
    'time': ['ESP_FECHA', 'ESP_FECHA_LONG', 'ESP_FECHA_TXT', 'fecha', 'FECHA', 'timestamp', 'time', 'fecha_hora', 'FECHA_HORA', 'date'],
}


def _first(attrs, names):
    return next((attrs[n] for n in names if attrs.get(n) not in (None, '')), None)


def _parse_time(value):
    if value in (None, ''):
        return None
    try:
        number = float(value)
        return datetime.fromtimestamp(number / 1000 if abs(number) > 10_000_000_000 else number, tz=timezone.utc)
    except (ValueError, TypeError, OverflowError, OSError):
        try:
            dt = datetime.fromisoformat(str(value).strip().replace('Z', '+00:00'))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None


def _number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


class ArcGISError(ValueError):
    """HTTP success is insufficient when ArcGIS reports a JSON error."""


async def arcgis_json(client, url, params):
    attempts = max(1, min(settings.sgc_retry_attempts, 5))
    for attempt in range(attempts):
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ArcGISError('ArcGIS devolvió una estructura inválida')
            if payload.get('error'):
                raise ArcGISError(f"ArcGIS: {payload['error']}")
            return payload
        except (httpx.HTTPError, ValueError):
            if attempt == attempts - 1:
                raise
            await asyncio.sleep(min(2 ** attempt, 4))


class SgcEarthquakeAdapter:
    async def fetch_recent(self, limit: int = 50) -> list[dict]:
        # limit controls the batch size, never silently drops events in the time window.
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            urls = [settings.sgc_query_url]
            if settings.sgc_fallback_query_url:
                urls.append(settings.sgc_fallback_query_url)
            for index, url in enumerate(urls):
                try:
                    return await self._fetch(client, url, max(1, min(limit, 200)))
                except (httpx.HTTPError, ValueError):
                    if index == len(urls) - 1:
                        raise
        return []

    async def _fetch(self, client, url, batch_size):
        if '/EPIS/' in url.upper():
            raise ArcGISError('EPIS contiene exploración petrolera, no un catálogo de terremotos')
        metadata = await arcgis_json(client, url.rsplit('/query', 1)[0], {'f': 'json'})
        fields = {f['name']: f.get('type') for f in metadata.get('fields', []) if isinstance(f, dict) and 'name' in f}
        date_field = next((n for n in CANDIDATES['time'] if fields.get(n) == 'esriFieldTypeDate'), None)
        mag_field = next((n for n in CANDIDATES['magnitude'] if n in fields), None)
        if metadata.get('geometryType') != 'esriGeometryPoint' or not date_field or not mag_field:
            raise ArcGISError('La capa no tiene geometría, fecha y magnitud de un catálogo sísmico')
        now = datetime.now(timezone.utc)
        since = now - timedelta(minutes=settings.earthquake_max_age_minutes)
        until = now + timedelta(minutes=5)
        where = (f"{date_field} >= TIMESTAMP '{since:%Y-%m-%d %H:%M:%S}' AND "
                 f"{date_field} <= TIMESTAMP '{until:%Y-%m-%d %H:%M:%S}' AND "
                 f"{mag_field} >= {settings.earthquake_min_magnitude}")
        # returnIdsOnly works on services that explicitly do not support pagination.
        payload = await arcgis_json(client, url, {'where': where, 'returnIdsOnly': 'true', 'f': 'json'})
        ids = payload.get('objectIds')
        if ids is None and payload.get('objectIdFieldName'):
            return []  # ArcGIS represents an empty matching set as null.
        if not isinstance(ids, list):
            raise ArcGISError('La capa no devolvió objectIds')
        if len(ids) > 5000:
            raise ArcGISError('Ventana excede 5000 eventos; revisar filtro temporal')
        rows = []
        for offset in range(0, len(ids), batch_size):
            data = await arcgis_json(client, url, {
                'objectIds': ','.join(str(int(i)) for i in ids[offset:offset + batch_size]),
                'outFields': '*', 'returnGeometry': 'true', 'outSR': '4326', 'f': 'json',
            })
            if not isinstance(data.get('features'), list) or data.get('exceededTransferLimit'):
                raise ArcGISError('Respuesta de eventos incompleta')
            rows.extend(self.normalize_arcgis(data))
        return sorted(rows, key=lambda r: r['starts_at'] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    def normalize_arcgis(self, payload: dict) -> list[dict]:
        rows = []
        sr = payload.get('spatialReference', {}).get('latestWkid', payload.get('spatialReference', {}).get('wkid', 4326))
        for feature in payload.get('features', []):
            if not isinstance(feature, dict):
                continue
            attrs = feature.get('attributes') or feature.get('properties') or {}
            geom = feature.get('geometry') or {}
            if not isinstance(attrs, dict) or not isinstance(geom, dict):
                continue
            if geom.get('type') == 'Point':
                coords = geom.get('coordinates', [])
                x, y = (coords[:2] if len(coords) >= 2 else (None, None))
            elif 'type' in geom:
                continue
            else:
                geom_sr = geom.get('spatialReference', {}).get('wkid', sr)
                if geom_sr != 4326:
                    continue  # fetch requests outSR=4326; never relabel projected coordinates.
                x, y = geom.get('x'), geom.get('y')
            x, y = _number(x), _number(y)
            if x is None or y is None or not (-180 <= x <= 180 and -90 <= y <= 90):
                continue
            ext = _first(attrs, CANDIDATES['external_id'])
            rows.append({'external_id': str(ext) if ext is not None else None,
                         'source': 'SGC', 'type': 'EARTHQUAKE', 'latitude': y, 'longitude': x,
                         'magnitude': _number(_first(attrs, CANDIDATES['magnitude'])),
                         'depth_km': _number(_first(attrs, CANDIDATES['depth'])),
                         'starts_at': _parse_time(_first(attrs, CANDIDATES['time'])), 'raw': attrs})
        return rows
