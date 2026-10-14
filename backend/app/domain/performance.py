from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class PortfolioPerformance:
    total_return: Decimal | None
    days: int


def calculate_daily_twr(points: list[tuple[date, Decimal, Decimal]]) -> PortfolioPerformance:
    """Compound daily returns, treating cash flows as occurring at end of day."""
    ordered = sorted(points, key=lambda point: point[0])
    if len(ordered) < 2:
        return PortfolioPerformance(total_return=None, days=0)

    multiplier = Decimal("1")
    for (_, previous_value, _), (_, ending_value, ending_flow) in zip(ordered, ordered[1:]):
        if previous_value <= 0:
            return PortfolioPerformance(total_return=None, days=(ordered[-1][0] - ordered[0][0]).days)
        multiplier *= (ending_value - ending_flow) / previous_value
    return PortfolioPerformance(
        total_return=multiplier - Decimal("1"),
        days=(ordered[-1][0] - ordered[0][0]).days,
    )


def calculate_cagr(start_value: Decimal, end_value: Decimal, elapsed_days: int) -> Decimal | None:
    if start_value <= 0 or end_value < 0 or elapsed_days <= 0:
        return None
    years = Decimal(elapsed_days) / Decimal("365")
    return (end_value / start_value) ** (Decimal("1") / years) - Decimal("1")
