from fastapi import APIRouter
from providers.manager import manager as provider_manager
from schemas import ProviderStatus, ProviderStatusResponse, ProviderSettingsRequest
from config import settings

router = APIRouter(prefix="/api/providers", tags=["providers"])


@router.get("/status")
def get_provider_status():
    statuses = provider_manager.get_provider_status()
    items = []
    for s in statuses:
        items.append(ProviderStatus(
            name=s["name"],
            available=s["available"],
            configured=s["configured"],
            last_sync=s.get("last_sync"),
            error=s.get("error", ""),
        ))
    return ProviderStatusResponse(
        providers=items,
        current_priority=settings.priority,
    )
