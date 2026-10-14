"""Build auditable daily portfolio values from the ledger and persisted prices."""

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal

from app.domain.performance import calculate_daily_twr


@dataclass(frozen=True)
class HistoricalOperation:
    trade_date: date
    kind: str
    ticker: str
    quantity: Decimal
    unit_price_eur: Decimal


@dataclass(frozen=True)
class HistoricalQuote:
    day: date
    ticker: str
    price_eur: Decimal


@dataclass(frozen=True)
class PortfolioSeriesPoint:
    day: date
    value_eur: Decimal
    external_flow_eur: Decimal
    cumulative_return: Decimal | None = None


@dataclass(frozen=True)
class PortfolioSeries:
    points: list[PortfolioSeriesPoint]
    total_return: Decimal | None


def build_portfolio_series(*, operations: list[HistoricalOperation], quotes: list[HistoricalQuote]) -> PortfolioSeries:
    quotes_by_day: dict[date, list[HistoricalQuote]] = {}
    for quote in quotes:
        quotes_by_day.setdefault(quote.day, []).append(quote)

    holdings: dict[str, Decimal] = {}
    latest_prices: dict[str, Decimal] = {}
    points: list[PortfolioSeriesPoint] = []
    ordered_operations = sorted(operations, key=lambda item: item.trade_date)
    next_operation = 0
    pending_flow = Decimal("0")
    for day in sorted(quotes_by_day):
        while next_operation < len(ordered_operations) and ordered_operations[next_operation].trade_date <= day:
            operation = ordered_operations[next_operation]
            holdings[operation.ticker] = holdings.get(operation.ticker, Decimal("0")) + _quantity_delta(operation)
            pending_flow += _external_flow(operation)
            next_operation += 1
        for quote in quotes_by_day[day]:
            latest_prices[quote.ticker] = quote.price_eur
        open_tickers = [ticker for ticker, quantity in holdings.items() if quantity > 0]
        if not open_tickers or any(ticker not in latest_prices for ticker in open_tickers):
            continue
        value_eur = sum((holdings[ticker] * latest_prices[ticker] for ticker in open_tickers), Decimal("0"))
        points.append(PortfolioSeriesPoint(day, value_eur, pending_flow))
        pending_flow = Decimal("0")

    performance = calculate_daily_twr([(point.day, point.value_eur, point.external_flow_eur) for point in points])
    return PortfolioSeries(_with_cumulative_returns(points), performance.total_return)


def _with_cumulative_returns(points: list[PortfolioSeriesPoint]) -> list[PortfolioSeriesPoint]:
    if len(points) < 2:
        return points
    multiplier = Decimal("1")
    result = [replace(points[0], cumulative_return=Decimal("0"))]
    for previous, ending in zip(points, points[1:]):
        if previous.value_eur <= 0:
            return [replace(point, cumulative_return=None) for point in points]
        multiplier *= (ending.value_eur - ending.external_flow_eur) / previous.value_eur
        result.append(replace(ending, cumulative_return=multiplier - Decimal("1")))
    return result


def _quantity_delta(operation: HistoricalOperation) -> Decimal:
    if operation.kind in {"BUY", "OPENING_BALANCE", "TRANSFER_IN"}:
        return operation.quantity
    if operation.kind in {"SELL", "TRANSFER_OUT"}:
        return -operation.quantity
    if operation.kind == "ADJUSTMENT":
        return operation.quantity
    if operation.kind == "SPLIT":
        return operation.quantity
    return Decimal("0")


def _external_flow(operation: HistoricalOperation) -> Decimal:
    value = operation.quantity * operation.unit_price_eur
    if operation.kind in {"BUY", "OPENING_BALANCE"}:
        return value
    if operation.kind == "SELL":
        return -value
    return Decimal("0")
