from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_session
from app.db import get_session
from app.models import Benchmark
from app.schemas.benchmarks import BenchmarkConfig
from app.services.benchmarks import configure_benchmark, serialize_benchmark

router = APIRouter(prefix="/api/benchmarks", tags=["benchmarks"], dependencies=[Depends(require_session)])


@router.get("")
def list_benchmarks(session: Session = Depends(get_session)) -> list[dict]:
    return [serialize_benchmark(item) for item in session.scalars(select(Benchmark).order_by(Benchmark.name))]


@router.put("/{ticker}")
def configure(ticker: str, payload: BenchmarkConfig, session: Session = Depends(get_session)) -> dict:
    if payload.ticker.upper() != ticker.upper():
        payload = payload.model_copy(update={"ticker": ticker})
    return serialize_benchmark(configure_benchmark(session, payload))
