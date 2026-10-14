from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.auth import require_session
from app.db import get_session
from app.models import Account, Instrument, Operation
from app.schemas.operations import CancelRequest, OperationCreate, OperationPage, OperationResponse, OperationRevisionRequest
from app.services.operations import cancel_operation, create_operation, list_operations, revise_operation

router = APIRouter(prefix="/api/operations", tags=["operations"], dependencies=[Depends(require_session)])


def serialize(operation: Operation, session: Session) -> OperationResponse:
    account = session.get(Account, operation.account_id)
    instrument = session.get(Instrument, operation.instrument_id)
    return OperationResponse(
        id=operation.id,
        account_name=account.name,
        ticker=instrument.ticker,
        kind=operation.kind,
        quantity=operation.quantity,
        unit_price_eur=operation.unit_price_eur,
        trade_date=operation.trade_date,
        source_order=operation.source_order,
        fee_eur=operation.fee_eur,
        dividend_eur=operation.dividend_eur,
        original_unit_price=operation.original_unit_price,
        original_currency=operation.original_currency,
        settlement_date=operation.settlement_date,
        note=operation.note,
        is_approximate=operation.is_approximate,
    )


@router.post("", response_model=OperationResponse, status_code=status.HTTP_201_CREATED)
def create(payload: OperationCreate, session: Session = Depends(get_session)) -> OperationResponse:
    return serialize(create_operation(session, payload), session)


@router.get("", response_model=OperationPage)
def list_ledger(ticker: str | None = Query(default=None), session: Session = Depends(get_session)) -> OperationPage:
    items, total = list_operations(session, ticker=ticker)
    return OperationPage(items=[serialize(item, session) for item in items], total=total)


@router.post("/{operation_id}/revise", response_model=OperationResponse, status_code=status.HTTP_201_CREATED)
def revise(operation_id: int, payload: OperationRevisionRequest, session: Session = Depends(get_session)) -> OperationResponse:
    operation = revise_operation(session, operation_id, payload)
    if operation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operazione non disponibile")
    return serialize(operation, session)


@router.post("/{operation_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
def cancel(operation_id: int, payload: CancelRequest, session: Session = Depends(get_session)) -> Response:
    if not cancel_operation(session, operation_id, payload.reason):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operazione non disponibile")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
