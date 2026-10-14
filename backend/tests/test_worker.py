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


def test_eod_schedule_runs_each_market_once_at_its_local_time() -> None:
    from app.worker import due_market_jobs
    from datetime import datetime

    assert due_market_jobs(datetime(2026, 10, 12, 18, 0), last_runs={}) == ["EU"]
    assert due_market_jobs(datetime(2026, 10, 12, 16, 30), last_runs={}) == ["US"]
    assert due_market_jobs(datetime(2026, 10, 12, 18, 0), last_runs={"EU": date(2026, 10, 12)}) == []


def test_eod_schedule_converts_utc_to_each_market_timezone() -> None:
    from app.worker import due_jobs_at
    from datetime import timezone

    assert due_jobs_at(datetime(2026, 10, 12, 16, 0, tzinfo=timezone.utc), last_runs={}) == ["EU"]
    assert due_jobs_at(datetime(2026, 10, 12, 20, 30, tzinfo=timezone.utc), last_runs={}) == ["US"]


def test_scheduled_refresh_marks_due_market_after_success() -> None:
    from app.worker import run_scheduled_once

    settings = Settings(session_secret="test-session-secret-with-at-least-32chars")
    last_runs: dict[str, date] = {}

    result = run_scheduled_once(
        settings,
        now_utc=datetime(2026, 10, 12, 16, 0, tzinfo=timezone.utc),
        last_runs=last_runs,
        session_factory=lambda: None,
    )

    assert result == {"EU": {"refreshed": [], "failed": {}}}
    assert last_runs == {"EU": date(2026, 10, 12)}


def test_worker_status_is_atomic_and_contains_no_credentials(tmp_path) -> None:
    from app.worker import write_worker_status

    status_path = tmp_path / "worker-status.json"
    settings = Settings(session_secret="test-session-secret-with-at-least-32chars", worker_status_file=str(status_path), twelve_data_api_key="secret-that-must-not-be-written")
    write_worker_status(settings, now_utc=datetime(2026, 10, 12, 16, 0, tzinfo=timezone.utc), last_runs={"EU": date(2026, 10, 12)}, results={})

    content = status_path.read_text()
    assert "secret-that-must-not-be-written" not in content
    assert '"provider": "twelve_data"' in content
    assert not status_path.with_suffix(".json.partial").exists()
