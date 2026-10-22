from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.resume import router as resume_router
from app.api.v1.profile import router as profile_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.applications import router as applications_router
from app.api.v1.notifications import router as notifications_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(resume_router)
api_router.include_router(profile_router)
api_router.include_router(jobs_router)
api_router.include_router(applications_router, prefix="/applications", tags=["applications"])
api_router.include_router(notifications_router)

