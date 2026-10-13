from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import require_session
from app.db import get_session
from app.services.performance import benchmark_series, portfolio_series

router = APIRouter(prefix="/api/performance", tags=["performance"], dependencies=[Depends(require_session)])


@router.get("")
def summary(ticker: str | None = Query(default=None), session: Session = Depends(get_session)) -> dict:
    series = portfolio_series(session, ticker=ticker)
    return {
        "points": [
            {"date": point.day.isoformat(), "value_eur": point.value_eur, "external_flow_eur": point.external_flow_eur, "cumulative_return": point.cumulative_return}
            for point in series.points
        ],
        "total_return": series.total_return,
        "methodology": "TWR giornaliero flow-adjusted; flussi a fine giornata",
        "benchmarks": benchmark_series(session, series),
    }
