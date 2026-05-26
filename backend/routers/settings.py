from fastapi import APIRouter
from config import settings
from schemas import ProviderSettingsRequest

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/provider")
def get_provider_settings():
    return {
        "priority": settings.priority,
        "ths_http_token": settings.ths_http_token,
        "ths_http_refresh_token": "***" if settings.ths_http_refresh_token else "",
        "ths_sdk_enabled": settings.ths_sdk_enabled,
        "default_adjust": settings.default_adjust,
    }


@router.post("/provider")
def save_provider_settings(req: ProviderSettingsRequest):
    settings.update(
        priority=req.priority,
        ths_http_token=req.ths_http_token,
        ths_http_refresh_token=req.ths_http_refresh_token,
        ths_sdk_enabled=req.ths_sdk_enabled,
        default_adjust=req.default_adjust,
    )
    return {"status": "ok"}
