from decimal import Decimal


def normalize_price_to_eur(raw_price: Decimal, currency: str, fx_to_eur: Decimal) -> Decimal:
    """Return a quote in EUR, handling London pence before GBP conversion."""
    native_price = raw_price / Decimal("100") if currency.upper() == "GBX" else raw_price
    return native_price * fx_to_eur
