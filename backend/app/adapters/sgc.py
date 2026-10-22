from __future__ import annotations
from datetime import datetime, timezone
import httpx
from app.core.config import settings

CANDIDATES = {
    "magnitude": ["magnitud", "MAGNITUD", "magnitude", "Magnitude", "MAG"],
    "depth": ["profundidad", "PROFUNDIDAD", "depth", "Depth"],
    "external_id": ["OBJECTID", "objectid", "id", "ID", "evento"],
    "time": ["fecha", "FECHA", "timestamp", "time", "fecha_hora"],
}

def _first(attrs: dict, names: list[str]):
    for name in names:
        if name in attrs and attrs[name] not in (None, ""):
            return attrs[name]
    return None

class SgcEarthquakeAdapter:
    async def fetch_recent(self, limit: int = 50) -> list[dict]:
        params = {
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "true",
            "f": "json",
            "resultRecordCount": max(1, min(limit, 200)),
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(settings.sgc_query_url, params=params)
            response.raise_for_status()
            payload = response.json()
        return self.normalize_arcgis(payload)

    def normalize_arcgis(self, payload: dict) -> list[dict]:
        rows = []
        for feature in payload.get("features", []):
            attrs = feature.get("attributes") or {}
            geom = feature.get("geometry") or {}
            x = geom.get("x")
            y = geom.get("y")
            # ArcGIS commonly uses x=lon, y=lat for geographic point layers.
            if x is None or y is None:
                continue
            mag = _first(attrs, CANDIDATES["magnitude"])
            depth = _first(attrs, CANDIDATES["depth"])
            ext = _first(attrs, CANDIDATES["external_id"])
            rows.append({
                "external_id": str(ext) if ext is not None else None,
                "source": "SGC",
                "type": "EARTHQUAKE",
                "latitude": float(y),
                "longitude": float(x),
                "magnitude": float(mag) if mag not in (None, "") else None,
                "depth_km": float(depth) if depth not in (None, "") else None,
                "raw": attrs,
            })
        return rows
