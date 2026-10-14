from datetime import date
import csv
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.auth import require_session
from app.db import get_session
from app.services.performance import benchmark_series, portfolio_series

router = APIRouter(prefix="/api/performance", tags=["performance"], dependencies=[Depends(require_session)])


@router.get("")
def summary(
    ticker: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    session: Session = Depends(get_session),
) -> dict:
    return _payload(session, ticker=ticker, date_from=date_from, date_to=date_to)


def _payload(session: Session, *, ticker: str | None, date_from: date | None, date_to: date | None) -> dict:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from deve essere precedente o uguale a date_to")
    series = portfolio_series(session, ticker=ticker)
    points = [point for point in series.points if (date_from is None or point.day >= date_from) and (date_to is None or point.day <= date_to)]
    benchmarks = benchmark_series(session, series)
    for benchmark in benchmarks:
        benchmark["points"] = [point for point in benchmark["points"] if (date_from is None or date.fromisoformat(point["date"]) >= date_from) and (date_to is None or date.fromisoformat(point["date"]) <= date_to)]
    return {
        "points": [
            {"date": point.day.isoformat(), "value_eur": point.value_eur, "external_flow_eur": point.external_flow_eur, "cumulative_return": point.cumulative_return}
            for point in points
        ],
        "total_return": series.total_return,
        "methodology": "TWR giornaliero flow-adjusted; flussi a fine giornata",
        "benchmarks": benchmarks,
    }


@router.get("/export.csv")
def export_csv(
    ticker: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    session: Session = Depends(get_session),
) -> Response:
    payload = _payload(session, ticker=ticker, date_from=date_from, date_to=date_to)
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=["date", "value_eur", "external_flow_eur", "cumulative_return"])
    writer.writeheader()
    writer.writerows(payload["points"])
    return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=investix-performance.csv"})
