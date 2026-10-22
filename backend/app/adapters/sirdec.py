from __future__ import annotations
import httpx
from app.core.config import settings

class SirdecOpenDataAdapter:
    """Read-only adapter to the official Datos Abiertos/Socrata dataset derived from SIRDEC.

    It is intentionally NOT an operational SIRDEC integration. Current nominal searches that
    require CAPTCHA remain on the official SICLICO portal.
    """
    async def preview(self, limit: int = 20, offset: int = 0) -> dict:
        limit = max(1, min(limit, 200))
        offset = max(0, offset)
        params = {"$limit": limit, "$offset": offset}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(settings.sirdec_soda_url, params=params)
            response.raise_for_status()
            rows = response.json()
        return {
            "source": "Instituto Nacional de Medicina Legal / Datos Abiertos Colombia",
            "dataset_url": settings.sirdec_soda_url,
            "cutoff": settings.sirdec_dataset_cutoff,
            "records": rows,
            "warning": "Datos históricos con fecha de corte; no equivalen al estado operacional actual de un caso.",
        }

    def public_portal(self) -> dict:
        return {
            "url": settings.sirdec_public_portal_url,
            "mode": "human_interaction",
            "captcha": True,
            "note": "La aplicación no automatiza ni elude CAPTCHA o controles institucionales.",
        }
