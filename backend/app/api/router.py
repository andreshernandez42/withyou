from fastapi import APIRouter
from app.api.routes import auth,users,contacts,policies,checkpoints,events,safety,welfare,cases,personal_safety,notifications,official,admin,privacy

api_router=APIRouter()
for r in [auth.router,users.router,contacts.router,policies.router,checkpoints.router,events.router,safety.router,welfare.router,cases.router,personal_safety.router,notifications.router,official.router,admin.router,privacy.router]:
    api_router.include_router(r)
