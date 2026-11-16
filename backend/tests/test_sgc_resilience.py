import asyncio
from dataclasses import replace
from datetime import datetime, timezone
import httpx
import pytest
from app.adapters import sgc


def test_geojson_and_invalid_geometry_are_isolated():
    rows = sgc.SgcEarthquakeAdapter().normalize_arcgis({'features': [
        {'properties': {'id': 'sgc1', 'mag': 5.5, 'time': '2026-11-15T10:00:00Z'}, 'geometry': {'type': 'Point', 'coordinates': [-74, 4]}},
        {'attributes': {'OBJECTID': 2}, 'geometry': {'x': 'invalid', 'y': 4}},
        {'attributes': {'OBJECTID': 3}, 'geometry': {'x': float('nan'), 'y': 4}},
        {'attributes': {'OBJECTID': 4}, 'geometry': {'x': 200, 'y': 4}},
    ]})
    assert len(rows) == 1 and rows[0]['external_id'] == 'sgc1'
    assert rows[0]['raw']['mag'] == 5.5


def test_stable_event_id_and_official_date_preferred():
    row = sgc.SgcEarthquakeAdapter().normalize_arcgis({'features': [{
        'attributes': {'OBJECTID': 9, 'ESP_ID_EVENTO_TXT': 100, 'ESP_FECHA': 1794736800000, 'ESP_FECHA_TXT': 'bad'},
        'geometry': {'x': -74, 'y': 4}}]})[0]
    assert row['external_id'] == '100' and row['starts_at'].tzinfo == timezone.utc


def test_http_200_arcgis_error_retries_and_fails(monkeypatch):
    monkeypatch.setattr(sgc, 'settings', replace(sgc.settings, sgc_retry_attempts=2))
    calls = []
    async def no_wait(_): return None
    monkeypatch.setattr(sgc.asyncio, 'sleep', no_wait)
    def handle(request):
        calls.append(request)
        return httpx.Response(200, json={'error': {'code': 500, 'message': 'unavailable'}})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            with pytest.raises(sgc.ArcGISError):
                await sgc.arcgis_json(client, 'https://sgc.test/query', {'f': 'json'})
    asyncio.run(run())
    assert len(calls) == 2


def test_filtered_batches_work_without_pagination():
    calls = []
    def handle(request):
        p = request.url.params
        calls.append(p)
        if request.url.path.endswith('/0'):
            return httpx.Response(200, json={'geometryType': 'esriGeometryPoint', 'fields': [
                {'name': 'ESP_FECHA', 'type': 'esriFieldTypeDate'}, {'name': 'ESP_MAGNITUD', 'type': 'esriFieldTypeDouble'}]})
        if p.get('returnIdsOnly'):
            assert 'TIMESTAMP' in p['where'] and 'ESP_MAGNITUD >=' in p['where']
            return httpx.Response(200, json={'objectIds': [30, 2, 10]})
        assert 'resultRecordCount' not in p and p['outSR'] == '4326'
        return httpx.Response(200, json={'features': [
            {'attributes': {'OBJECTID': int(i), 'ESP_FECHA': 1794736800000, 'ESP_MAGNITUD': 5}, 'geometry': {'x': -74, 'y': 4}}
            for i in p['objectIds'].split(',')]})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await sgc.SgcEarthquakeAdapter()._fetch(client, 'https://sgc.test/MapServer/0/query', 2)
    assert len(asyncio.run(run())) == 3
    assert len(calls) == 4


def test_epis_is_not_earthquake_source():
    async def run():
        async with httpx.AsyncClient() as client:
            with pytest.raises(sgc.ArcGISError, match='petrolera'):
                await sgc.SgcEarthquakeAdapter()._fetch(client, 'https://sgc.test/EPIS/EPIS_V2/FeatureServer/0/query', 100)
    asyncio.run(run())


def test_projected_coordinates_not_relabelled():
    assert sgc.SgcEarthquakeAdapter().normalize_arcgis({'spatialReference': {'wkid': 3857}, 'features': [
        {'attributes': {'OBJECTID': 1}, 'geometry': {'x': 10, 'y': 10}}]}) == []


def test_arcgis_null_ids_is_successful_empty_window():
    def handle(request):
        if request.url.path.endswith('/0'):
            return httpx.Response(200, json={'geometryType': 'esriGeometryPoint', 'fields': [
                {'name': 'ESP_FECHA', 'type': 'esriFieldTypeDate'}, {'name': 'ESP_MAGNITUD', 'type': 'esriFieldTypeDouble'}]})
        return httpx.Response(200, json={'objectIdFieldName': 'OBJECTID', 'objectIds': None})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await sgc.SgcEarthquakeAdapter()._fetch(client, 'https://sgc.test/MapServer/0/query', 50)
    assert asyncio.run(run()) == []
