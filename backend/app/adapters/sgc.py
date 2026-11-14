from __future__ import annotations
from datetime import datetime, timezone
import httpx
from app.core.config import settings

CANDIDATES={
    'magnitude':['magnitud','MAGNITUD','magnitude','Magnitude','MAG','mag'],
    'depth':['profundidad','PROFUNDIDAD','depth','Depth','prof'],
    'external_id':['OBJECTID','objectid','id','ID','evento','event_id'],
    'time':['fecha','FECHA','timestamp','time','fecha_hora','FECHA_HORA','date'],
}

def _first(attrs:dict,names:list[str]):
    for name in names:
        if name in attrs and attrs[name] not in (None,''):return attrs[name]
    return None


def _parse_time(value):
    if value in (None,''):return None
    if isinstance(value,(int,float)):
        # ArcGIS suele usar milisegundos desde epoch.
        seconds=float(value)/1000 if float(value)>10_000_000_000 else float(value)
        try:return datetime.fromtimestamp(seconds,tz=timezone.utc)
        except Exception:return None
    text=str(value).strip().replace('Z','+00:00')
    try:
        dt=datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:return None

class SgcEarthquakeAdapter:
    async def fetch_recent(self,limit:int=50)->list[dict]:
        params={'where':'1=1','outFields':'*','returnGeometry':'true','f':'json','resultRecordCount':max(1,min(limit,200)),'orderByFields':'OBJECTID DESC'}
        async with httpx.AsyncClient(timeout=20,follow_redirects=True) as client:
            response=await client.get(settings.sgc_query_url,params=params)
            response.raise_for_status()
            ctype=response.headers.get('content-type','')
            if 'json' not in ctype.lower():raise ValueError(f'SGC respondió contenido no JSON: {ctype}')
            payload=response.json()
        if 'error' in payload:raise ValueError(f"ArcGIS error: {payload['error']}")
        return self.normalize_arcgis(payload)

    def normalize_arcgis(self,payload:dict)->list[dict]:
        rows=[]
        for feature in payload.get('features',[]):
            attrs=feature.get('attributes') or {};geom=feature.get('geometry') or {}
            x=geom.get('x');y=geom.get('y')
            if x is None or y is None:continue
            mag=_first(attrs,CANDIDATES['magnitude']);depth=_first(attrs,CANDIDATES['depth']);ext=_first(attrs,CANDIDATES['external_id']);t=_first(attrs,CANDIDATES['time'])
            try:mag=float(mag) if mag not in (None,'') else None
            except (TypeError,ValueError):mag=None
            try:depth=float(depth) if depth not in (None,'') else None
            except (TypeError,ValueError):depth=None
            rows.append({'external_id':str(ext) if ext is not None else None,'source':'SGC','type':'EARTHQUAKE','latitude':float(y),'longitude':float(x),'magnitude':mag,'depth_km':depth,'starts_at':_parse_time(t),'raw':attrs})
        return rows
