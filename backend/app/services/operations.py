from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Account, Instrument, Operation, OperationRevision
from app.schemas.operations import OperationCreate, OperationRevisionRequest


def create_operation(session: Session, payload: OperationCreate, *, commit: bool = True) -> Operation:
    account = session.scalar(select(Account).where(Account.name == payload.account_name))
    if account is None:
        account = Account(name=payload.account_name)
        session.add(account)
        session.flush()
    ticker = payload.ticker.upper()
    instrument = session.scalar(select(Instrument).where(Instrument.ticker == ticker))
    if instrument is None:
        instrument = Instrument(ticker=ticker)
        session.add(instrument)
        session.flush()
    values = payload.model_dump(exclude={"account_name", "ticker"})
    operation = Operation(account_id=account.id, instrument_id=instrument.id, **values)
    session.add(operation)
    if commit:
        session.commit()
        session.refresh(operation)
    else:
        session.flush()
    return operation


def list_operations(session: Session, ticker: str | None = None) -> tuple[list[Operation], int]:
    statement = select(Operation).join(Instrument).join(Account).where(Operation.cancelled.is_(False))
    if ticker:
        statement = statement.where(Instrument.ticker == ticker.upper())
    statement = statement.order_by(Operation.trade_date, Operation.source_order, Operation.id)
    items = list(session.scalars(statement))
    return items, len(items)


def revise_operation(session: Session, operation_id: int, request: OperationRevisionRequest) -> Operation | None:
    original = session.get(Operation, operation_id)
    if original is None or original.cancelled:
        return None
    values = {
        "account_id": original.account_id,
        "instrument_id": original.instrument_id,
        "kind": original.kind,
        "quantity": request.quantity if request.quantity is not None else original.quantity,
        "unit_price_eur": request.unit_price_eur if request.unit_price_eur is not None else original.unit_price_eur,
        "trade_date": request.trade_date if request.trade_date is not None else original.trade_date,
        "source_order": request.source_order if request.source_order is not None else original.source_order,
        "fee_eur": request.fee_eur if request.fee_eur is not None else original.fee_eur,
        "dividend_eur": request.dividend_eur if request.dividend_eur is not None else original.dividend_eur,
        "original_unit_price": request.original_unit_price if request.original_unit_price is not None else original.original_unit_price,
        "original_currency": request.original_currency.upper() if request.original_currency is not None else original.original_currency,
        "settlement_date": request.settlement_date if request.settlement_date is not None else original.settlement_date,
        "note": request.note if request.note is not None else original.note,
        "is_approximate": request.is_approximate if request.is_approximate is not None else original.is_approximate,
    }
    original.cancelled = True
    replacement = Operation(**values)
    session.add(replacement)
    session.flush()
    session.add(OperationRevision(operation_id=replacement.id, supersedes_operation_id=original.id, action="REVISE", reason=request.reason))
    session.commit()
    session.refresh(replacement)
    return replacement


def cancel_operation(session: Session, operation_id: int, reason: str) -> bool:
    operation = session.get(Operation, operation_id)
    if operation is None or operation.cancelled:
        return False
    operation.cancelled = True
    session.add(OperationRevision(operation_id=operation.id, action="CANCEL", reason=reason))
    session.commit()
    return True


def operation_response(operation: Operation) -> dict:
    account_name = operation.__dict__.get("account_name")
    ticker = operation.__dict__.get("ticker")
    return {
        "id": operation.id,
        "account_name": account_name,
        "ticker": ticker,
        "kind": operation.kind,
        "quantity": operation.quantity,
        "unit_price_eur": operation.unit_price_eur,
        "trade_date": operation.trade_date,
        "source_order": operation.source_order,
        "fee_eur": operation.fee_eur,
        "dividend_eur": operation.dividend_eur,
        "original_unit_price": operation.original_unit_price,
        "original_currency": operation.original_currency,
        "settlement_date": operation.settlement_date,
        "note": operation.note,
        "is_approximate": operation.is_approximate,
    }
