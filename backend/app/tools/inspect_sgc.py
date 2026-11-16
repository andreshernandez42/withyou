"""Inspección de metadatos públicos de SGC. Ejecute dentro de api1.

No escribe a BD ni origina alertas; no considera GPServer como feed.
"""
from __future__ import annotations

import json
import httpx

ROOT = 'https://srvags.sgc.gov.co/arcgis/rest/services'
CANDIDATE = ('EPIS/EPIS_V2/FeatureServer', 'EPIS/EPIS_V2/MapServer',
             'catalogo_sismos/catalogo_de_sismos_2/FeatureServer')


def get(client: httpx.Client, url: str) -> dict:
    response = client.get(url, params={'f': 'json'})
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or 'error' in payload:
        raise ValueError(f'Respuesta inválida de {url}: {payload.get("error") if isinstance(payload,dict) else "JSON"}')
    return payload


def main():
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        for path in CANDIDATE:
            print('\nSERVICIO:', path)
            try:
                response = get(client, f'{ROOT}/{path}')
                print('  capas:', [(c.get('id'), c.get('name')) for c in response.get('layers', [])])
                for layer in response.get('layers', [])[:15]:
                    info = get(client, f'{ROOT}/{path}/{layer["id"]}')
                    fields = [
                        (field['name'], field.get('type'))
                        for field in info.get('fields', [])
                        if any(k in field['name'].lower() for k in ('fecha','time','magn','depth','prof','event','sism'))
                    ]
                    print('  capa:', layer.get('id'), layer.get('name'),
                          'geometría:', info.get('geometryType'), 'campos:', json.dumps(fields,ensure_ascii=False))
            except (httpx.HTTPError, ValueError) as exc:
                print('  no disponible o no validado:', str(exc)[:300])
    print('\nImportante: capas y HTTP 200 NO prueban actualidad ni elegibilidad para alertas.')


if __name__ == '__main__':
    main()
