from fastapi import APIRouter, Depends, Query

from app.auth import require_session
from app.providers.twelve_data import TwelveDataAdapter
from app.services.live_quotes import LiveQuoteService
from app.settings import get_settings

router = APIRouter(prefix="/api/quotes", tags=["live-quotes"], dependencies=[Depends(require_session)])
_service: LiveQuoteService | None = None


def _get_service() -> LiveQuoteService | None:
    global _service
    if _service is not None:
        return _service
    settings = get_settings()
    if not settings.twelve_data_api_key:
        return None
    _service = LiveQuoteService(
        provider=TwelveDataAdapter(api_key=settings.twelve_data_api_key),
        batch_size=settings.live_batch_size,
        credits_per_minute=settings.live_credits_per_minute,
        daily_credits=settings.live_daily_credits,
        daily_reserve_percent=settings.live_daily_reserve_percent,
    )
    return _service


@router.get("/live")
def live_quotes(symbols: str = Query(..., min_length=1), session_id: str = Query(default="default", min_length=1, max_length=128)) -> dict:
    requested = [value for value in symbols.split(",") if value.strip()]
    service = _get_service()
    if service is None:
        return {"status": "provider_disabled", "items": [], "statuses": {symbol.upper(): "pending" for symbol in requested}, "credits_used": 0, "retry_after": None}
    return service.get_snapshot(requested, session_id=session_id)
