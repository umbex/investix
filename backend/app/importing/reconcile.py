from decimal import Decimal


class ReconciliationError(ValueError):
    pass


def reconcile_quantities(imported: dict[str, Decimal], reference: dict[str, Decimal], *, tolerance: Decimal = Decimal("0")) -> None:
    differences = {
        key: (imported.get(key, Decimal("0")), reference.get(key, Decimal("0")))
        for key in set(imported) | set(reference)
        if abs(imported.get(key, Decimal("0")) - reference.get(key, Decimal("0"))) > tolerance
    }
    if differences:
        detail = ", ".join(f"{key}: importato {actual}, riferimento {expected}" for key, (actual, expected) in sorted(differences.items()))
        raise ReconciliationError(f"Riconciliazione quantità non superata: {detail}")
