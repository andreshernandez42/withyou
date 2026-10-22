from app.adapters.sgc import SgcEarthquakeAdapter

def test_sgc_arcgis_normalizer():
    payload={"features":[{"attributes":{"OBJECTID":99,"magnitud":5.8,"profundidad":32},"geometry":{"x":-74.1,"y":4.7}}]}
    rows=SgcEarthquakeAdapter().normalize_arcgis(payload)
    assert rows[0]['source']=='SGC'
    assert rows[0]['magnitude']==5.8
    assert rows[0]['latitude']==4.7
    assert rows[0]['longitude']==-74.1
