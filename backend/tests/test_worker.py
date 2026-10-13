from datetime import date, datetime, timezone
from decimal import Decimal

from app.settings import Settings
from app.worker import build_twelve_data_adapter


def test_worker_keeps_public_provider_disabled_without_a_key() -> None:
    settings = Settings(session_secret="test-session-secret-with-at-least-32chars")

    assert build_twelve_data_adapter(settings) is None


def test_worker_builds_twelve_adapter_with_ecb_fx_resolver() -> None:
    settings = Settings(session_secret="test-session-secret-with-at-least-32chars", twelve_data_api_key="test-key")
    adapter = build_twelve_data_adapter(settings, fetch_fx=lambda _: Decimal("0.9"))

    assert adapter is not None
    assert adapter._fx_to_eur(datetime(2026, 10, 12, tzinfo=timezone.utc)) == Decimal("0.9")


def test_worker_refresh_once_skips_cleanly_when_provider_is_disabled() -> None:
    from app.worker import refresh_once

    settings = Settings(session_secret="test-session-secret-with-at-least-32chars")

    assert refresh_once(settings, session_factory=lambda: None) == {"refreshed": [], "failed": {}}
