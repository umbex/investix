from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import require_session
from app.providers.base import ProviderError
from app.providers.twelve_data import TwelveDataAdapter
from app.settings import get_settings

router = APIRouter(prefix="/api/instruments", tags=["instruments"], dependencies=[Depends(require_session)])


@router.get("/lookup")
def lookup(query: str = Query(..., min_length=1, max_length=64)) -> dict:
    settings = get_settings()
    if not settings.twelve_data_api_key:
        return {"status": "provider_disabled", "items": []}
    try:
        items = TwelveDataAdapter(api_key=settings.twelve_data_api_key).search_symbols(query)
    except ProviderError as error:
        if error.retryable:
            return {"status": "temporarily_unavailable", "items": [], "message": "Provider non disponibile: riprovare più tardi."}
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"status": "ok", "items": items}
