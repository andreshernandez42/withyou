"""Read-only live validation. Run from repository root: python scripts/validate_sgc.py."""
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
import httpx
from app.adapters.sgc import SgcEarthquakeAdapter
from app.core.config import settings

ROOT = 'https://srvags.sgc.gov.co/arcgis/rest/services'
SERVICES = {
    'EPIS directory (not earthquakes)': f'{ROOT}/EPIS',
    'petroleum FeatureServer': f'{ROOT}/EPIS/EPIS_V2/FeatureServer',
    'petroleum MapServer': f'{ROOT}/EPIS/EPIS_V2/MapServer',
    'ClipTools metadata': f'{ROOT}/EPIS/ClipTools/GPServer',
    'ExportTools metadata': f'{ROOT}/EPIS/ExportTools/GPServer',
    'earthquake layer': settings.sgc_query_url.rsplit('/query', 1)[0],
}

async def main():
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        async def inspect(name, url):
            try:
                r = await client.get(url, params={'f': 'json'})
                r.raise_for_status()
                data = r.json()
                error = data.get('error')
                return {'name': name, 'url': url, 'http_status': r.status_code,
                        'ok': not bool(error), 'error': error,
                        'layers': data.get('layers'), 'tasks': data.get('tasks'),
                        'services': data.get('services'), 'execution_type': data.get('executionType')}
            except Exception as exc:
                return {'name': name, 'url': url, 'ok': False, 'error': str(exc)}
        services = await asyncio.gather(*(inspect(n, u) for n, u in SERVICES.items()))
    try:
        items = await SgcEarthquakeAdapter().fetch_recent(100)
        ingestion = {'ok': True, 'recent_records': len(items), 'records': items}
    except Exception as exc:
        ingestion = {'ok': False, 'error': str(exc)}
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'services': services, 'ingestion': ingestion,
              'note': 'Metadata verification only for GPServer; no paid or state-changing jobs submitted. A successful empty time window is not evidence of a recent earthquake.'}
    target = Path(__file__).resolve().parents[1] / 'docs/validation/sgc_live.json'
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if all(s['ok'] for s in services) and ingestion['ok'] else 1

if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
