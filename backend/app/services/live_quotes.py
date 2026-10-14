"""On-demand, quota-aware live quote cache."""

from collections.abc import Callable
from dataclasses import dataclass
from time import time

from app.providers.base import LiveQuote, ProviderError


@dataclass
class _CachedQuote:
    quote: LiveQuote
    cached_at: float


class LiveQuoteService:
    def __init__(self, *, provider, batch_size: int = 8, credits_per_minute: int = 8, daily_credits: int = 800, daily_reserve_percent: int = 20, cache_ttl_seconds: int = 240, now: Callable[[], float] = time) -> None:
        if batch_size < 1 or batch_size > credits_per_minute:
            raise ValueError("batch_size non può superare credits_per_minute")
        self.provider = provider
        self.batch_size = batch_size
        self.credits_per_minute = credits_per_minute
        self.daily_credits = daily_credits
        self.daily_reserve = max(0, daily_credits * daily_reserve_percent // 100)
        self.cache_ttl_seconds = cache_ttl_seconds
        self.now = now
        self._cache: dict[str, _CachedQuote] = {}
        self._last_dispatch_at: float | None = None
        self._credits_used = 0
        self._quota_retry_after: float | None = None
        self._sessions: dict[str, float] = {}

    def get_snapshot(self, symbols: list[str], *, session_id: str) -> dict:
        requested = list(dict.fromkeys(symbol.strip().upper() for symbol in symbols if symbol.strip()))
        now = self.now()
        self._sessions[session_id] = now
        status = "fresh"
        retry_after = self._quota_retry_after
        if retry_after and now < retry_after:
            status = "quota_exhausted"
        else:
            self._quota_retry_after = None
            missing = [symbol for symbol in requested if symbol not in self._cache or now - self._cache[symbol].cached_at >= self.cache_ttl_seconds]
            can_dispatch = self._last_dispatch_at is None or now - self._last_dispatch_at >= 60
            daily_available = self.daily_credits - self.daily_reserve - self._credits_used
            if missing and can_dispatch and daily_available > 0:
                batch = missing[: min(self.batch_size, daily_available)]
                self._last_dispatch_at = now
                try:
                    for quote in self.provider.fetch_live_quotes(batch):
                        self._cache[quote.ticker.upper()] = _CachedQuote(quote=quote, cached_at=now)
                    self._credits_used += len(batch)
                except ProviderError as error:
                    if error.retryable:
                        self._quota_retry_after = now + 60
                        status = "quota_exhausted"
                        retry_after = self._quota_retry_after
                    else:
                        status = "error"
            elif missing and daily_available <= 0:
                self._quota_retry_after = now + 86400
                status = "quota_exhausted"
                retry_after = self._quota_retry_after
            elif missing:
                status = "pending"

        items = []
        statuses: dict[str, str] = {}
        for symbol in requested:
            cached = self._cache.get(symbol)
            if cached is None:
                statuses[symbol] = "quota_exhausted" if status == "quota_exhausted" else "pending"
                continue
            age = max(0, now - cached.cached_at)
            item_status = "fresh" if age < self.cache_ttl_seconds else "stale"
            statuses[symbol] = item_status
            quote = cached.quote
            items.append({
                "ticker": quote.ticker,
                "price": quote.price,
                "price_eur": quote.price_eur,
                "currency": quote.currency,
                "change_percent": quote.change_percent,
                "observed_at": quote.observed_at,
                "provider": quote.provider,
                "status": item_status,
                "stale_since": cached.cached_at + self.cache_ttl_seconds if item_status == "stale" else None,
            })
        if status == "fresh" and any(value in {"pending", "stale"} for value in statuses.values()):
            status = "pending" if any(value == "pending" for value in statuses.values()) else "stale"
        return {"status": status, "items": items, "statuses": statuses, "credits_used": self._credits_used, "retry_after": retry_after}

    def close_expired_sessions(self, idle_seconds: int = 600) -> int:
        now = self.now()
        expired = [session_id for session_id, last_seen in self._sessions.items() if now - last_seen >= idle_seconds]
        for session_id in expired:
            del self._sessions[session_id]
        return len(expired)
