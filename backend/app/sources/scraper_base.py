"""Base class for HTML scraper adapters with retry, rate limiting, and circuit breaker."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# Rotating User-Agent pool
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
]


@dataclass
class CircuitState:
    """Tracks consecutive failures for circuit breaker pattern."""
    failures: int = 0
    last_failure: float = 0.0
    open_until: float = 0.0
    max_failures: int = 5
    cooldown_seconds: float = 120.0

    @property
    def is_open(self) -> bool:
        if self.failures < self.max_failures:
            return False
        return time.monotonic() < self.open_until

    def record_failure(self):
        self.failures += 1
        self.last_failure = time.monotonic()
        if self.failures >= self.max_failures:
            self.open_until = time.monotonic() + self.cooldown_seconds
            logger.warning(
                "Circuit breaker opened: %d consecutive failures, "
                "cooldown %.0fs",
                self.failures, self.cooldown_seconds,
            )

    def record_success(self):
        self.failures = 0


class BaseHTMLScraper:
    """Base class for HTML scraper adapters.

    Provides:
    - Shared httpx.AsyncClient with User-Agent rotation
    - Per-request rate limiting
    - Retry with exponential backoff
    - Circuit breaker (skip source after N consecutive failures)
    - Response validation (detect blocks, CAPTCHAs, empty pages)
    """

    name: str = "base"
    delay_seconds: float = 1.0
    timeout_seconds: float = 30.0
    max_results: int = 50

    def __init__(self):
        self._request_count = 0
        self._circuit = CircuitState()
        self._client = httpx.AsyncClient(
            timeout=self.timeout_seconds,
            follow_redirects=True,
            headers={
                "Accept": "text/html,application/xhtml+xml,application/json",
                "Accept-Language": "en-US,en;q=0.9,pl;q=0.8",
            },
        )
        self._last_request_time = 0.0

    def _get_user_agent(self) -> str:
        self._request_count += 1
        return USER_AGENTS[self._request_count % len(USER_AGENTS)]

    async def _rate_limit(self):
        """Enforce minimum delay between requests."""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self.delay_seconds:
            await asyncio.sleep(self.delay_seconds - elapsed)
        self._last_request_time = time.monotonic()

    def _validate_response(self, resp: httpx.Response) -> bool:
        """Check if response is valid (not blocked/CAPTCHA/empty)."""
        if resp.status_code == 403:
            logger.warning("[%s] 403 Forbidden - possibly blocked", self.name)
            return False
        if resp.status_code == 429:
            logger.warning("[%s] 429 Too Many Requests - rate limited", self.name)
            return False
        if resp.status_code >= 500:
            logger.warning("[%s] Server error %d", self.name, resp.status_code)
            return False

        text = resp.text.lower()
        # Detect common CAPTCHA/block patterns
        captcha_patterns = [
            "captcha", "recaptcha", "are you a robot",
            "access denied", "please verify", "unusual traffic",
        ]
        for pattern in captcha_patterns:
            if pattern in text[:2000]:
                logger.warning("[%s] Detected block/CAPTCHA pattern: %s", self.name, pattern)
                return False

        return True

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=15),
        reraise=True,
    )
    async def fetch(self, url: str, params: dict | None = None) -> httpx.Response | None:
        """Fetch a URL with rate limiting, retry, and validation.

        Returns None if the circuit is open or the response is invalid.
        """
        if self._circuit.is_open:
            logger.debug("[%s] Circuit breaker open, skipping request", self.name)
            return None

        await self._rate_limit()

        headers = {"User-Agent": self._get_user_agent()}

        try:
            resp = await self._client.get(url, params=params, headers=headers)

            if not self._validate_response(resp):
                self._circuit.record_failure()
                return None

            resp.raise_for_status()
            self._circuit.record_success()
            return resp

        except httpx.HTTPStatusError as e:
            if e.response.status_code in (403, 429):
                self._circuit.record_failure()
                return None
            raise

    async def fetch_json(self, url: str, params: dict | None = None) -> dict | None:
        """Fetch JSON endpoint with all protections."""
        resp = await self.fetch(url, params)
        if resp is None:
            return None
        try:
            return resp.json()
        except Exception:
            logger.warning("[%s] Failed to parse JSON response", self.name)
            return None
