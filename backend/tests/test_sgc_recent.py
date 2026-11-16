import asyncio
from dataclasses import replace
from datetime import timedelta

import httpx
import pytest

from app.adapters.sgc_recent import fetch_window, normalize
from app.services import sgc_sync
from app.services.timeutils import utcnow
from conftest import auth, login, register


def test_recent_catalogue_assignment_recovery_and_deduplication(client, monkeypatch):
    now = utcnow()
    feature = {"id":"SGC-fixture", "properties":{"agency":"SGC", "type":"earthquake",
               "mag":5.6, "utcTime":now.isoformat(), "depth":17},
               "geometry":{"type":"Point", "coordinates":[-74.08, 4.71, 17]}}
    collection = {"type":"FeatureCollection", "metadata":{"count":1}, "features":[feature]}
    responses = [collection, collection]
    monkeypatch.setattr(sgc_sync, "settings", replace(sgc_sync.settings, sgc_source="biweekly", sgc_poll_enabled=True))
    def respond(request):
        assert "startdate" in request.url.params and "enddate" in request.url.params
        return httpx.Response(200, json=responses.pop(0))
    async def fetch(*args):
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
            return await fetch_window(http, now-timedelta(minutes=30), now)
    async def fail(*args):
        return normalize({"statusCode":503, "body":"fixture failure"})
    monkeypatch.setattr(sgc_sync.SgcRecentAdapter, "fetch_recent", fetch)
    register(client, "Cercana", "near-sgc@example.com")
    register(client, "Lejana", "far-sgc@example.com")
    near = auth(login(client,"near-sgc@example.com")["access_token"])
    far = auth(login(client,"far-sgc@example.com")["access_token"])
    for headers, lat, lon in [(near,4.71,-74.08),(far,10.39,-75.48)]:
        assert client.post("/api/v1/checkpoints",headers=headers,json={"latitude":lat,"longitude":lon}).status_code == 201
    status_url = "/api/v1/official/sgc/status"
    assert asyncio.run(sgc_sync.sync_sgc_once())["created"] == 1
    success = client.get(status_url,headers=near).json()
    assert success["state"] == "ACTIVE"
    assert client.get("/api/v1/safety/pending",headers=far).json() == []
    monkeypatch.setattr(sgc_sync.SgcRecentAdapter,"fetch_recent",fail)
    with pytest.raises(ValueError):
        asyncio.run(sgc_sync.sync_sgc_once())
    failure = client.get(status_url,headers=near).json()
    assert failure["state"] == "UNAVAILABLE" and failure["last_success_at"] == success["last_success_at"]
    monkeypatch.setattr(sgc_sync.SgcRecentAdapter,"fetch_recent",fetch)
    assert asyncio.run(sgc_sync.sync_sgc_once())["created"] == 0
    assert client.get(status_url,headers=near).json()["state"] == "ACTIVE"
    pending = client.get("/api/v1/safety/pending",headers=near).json()
    assert len(pending) == 1 and pending[0]["magnitude"] == 5.6
    response = client.post("/api/v1/safety/respond", headers=near,
                           json={"status":"SAFE", "event_id":pending[0]["event_id"]})
    assert response.status_code == 200
    assert client.get("/api/v1/safety/pending",headers=near).json() == []
