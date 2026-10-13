"""Apply reviewed preferred-quote metadata without changing ledger operations."""

import argparse

from app.db import create_session_factory
from app.services.instrument_catalog import configure_instrument


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Configure reviewed instrument quote metadata")
    parser.add_argument("--stocks26-eqqq", action="store_true", help="Configure EQQQ as its Borsa Italiana EUR listing")
    args = parser.parse_args(argv)
    if not args.stocks26_eqqq:
        parser.error("Selezionare almeno un catalogo approvato")
    with create_session_factory()() as session:
        if args.stocks26_eqqq:
            configure_instrument(
                session,
                ticker="EQQQ",
                isin="IE0032077012",
                quote_symbol="EQQQ.MI",
                quote_venue="Borsa Italiana",
                quote_currency="EUR",
            )
        session.commit()
    print("Catalogo strumenti aggiornato: EQQQ -> Borsa Italiana (EUR)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
