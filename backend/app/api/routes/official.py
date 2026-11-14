from fastapi import APIRouter,Depends,HTTPException,Query
from app.core.dependencies import current_user
from app.models import User
from app.adapters.sirdec import SirdecOpenDataAdapter
from app.adapters.ideam import IdeamAdapter
from app.core.config import settings

router=APIRouter(tags=['official-sources'])

@router.get('/official/sirdec/preview')
async def sirdec_preview(limit:int=Query(20,ge=1,le=200),offset:int=Query(0,ge=0),user:User=Depends(current_user)):
    try:return await SirdecOpenDataAdapter().preview(limit,offset)
    except Exception as e:raise HTTPException(502,f'No fue posible consultar Datos Abiertos/SIRDEC: {e}')

@router.get('/official/sirdec/public-portal')
def sirdec_portal(user:User=Depends(current_user)):
    return SirdecOpenDataAdapter().public_portal()

@router.get('/official/ideam/status')
async def ideam_status(user:User=Depends(current_user)):
    try:return await IdeamAdapter().fetch()
    except Exception as e:raise HTTPException(502,f'No fue posible consultar IDEAM configurado: {e}')

@router.get('/official/ungrd')
def ungrd(user:User=Depends(current_user)):
    return {"url":settings.ungrd_portal_url,"mode":"reference","note":"No se afirma API pública donde no exista contrato documentado."}
