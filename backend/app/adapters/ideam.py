from __future__ import annotations
import httpx
from app.core.config import settings

class IdeamAdapter:
    """Configurable adapter for an IDEAM/FEWS JSON endpoint.

    No stable machine endpoint is hard-coded here because the anteproyecto explicitly avoids
    claiming an API where only a portal/visor is confirmed. Set IDEAM_JSON_URL when the exact
    public endpoint is verified for the chosen hazard layer. Until then, use /test/emergency-events.
    """
    async def fetch(self) -> dict:
        if not settings.ideam_json_url:
            return {"configured": False, "reason": "IDEAM_JSON_URL no configurada; usar simulador o registrar endpoint oficial validado."}
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(settings.ideam_json_url)
            r.raise_for_status()
            return {"configured": True, "payload": r.json()}
