import asyncio
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import structlog
from playwright.async_api import async_playwright

from src.domain.entities.proxy import Proxy
from src.infrastructure.browser.auto_login import auto_login
from src.infrastructure.browser.behaviors.scroll import human_scroll, think_time
from src.infrastructure.browser.fingerprint import Fingerprint, random_fingerprint
from src.infrastructure.browser.metrics import install_metrics_observer, read_performance_metrics
from src.infrastructure.browser.stealth.patches import apply_stealth

logger = structlog.get_logger(__name__)

DEFAULT_MAX_CONCURRENT_BROWSERS = 5  # Phase 3: hardcoded. Phase 4: runtime_config-driven (§5.2).
DEFAULT_TIMEOUT_SECONDS = 30.0


@dataclass
class BrowserRunResult:
    success: bool
    fingerprint: Fingerprint | None = None
    metrics: dict[str, float | None] = field(default_factory=dict)
    screenshot_path: str | None = None
    error: str | None = None
    duration_ms: int | None = None


def _playwright_proxy_config(proxy: Proxy) -> dict:
    config = {"server": f"{proxy.protocol}://{proxy.host}:{proxy.port}"}
    if proxy.username:
        config["username"] = proxy.username
        config["password"] = proxy.password or ""
    return config


class BrowserEngine:
    """Owns a single Chromium instance; every run_session() call gets its own
    isolated BrowserContext (fresh cookies/storage/fingerprint), gated by a
    shared Semaphore(N) so no more than N contexts run concurrently (§5.2,
    §Appendix A.2 — N=5 hardcoded here in Phase 3, dynamic from Phase 4)."""

    def __init__(self, max_concurrent: int = DEFAULT_MAX_CONCURRENT_BROWSERS, headless: bool = True) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._current_concurrency = max_concurrent
        self._headless = headless
        self._playwright = None
        self._browser = None

    def set_concurrency(self, max_concurrent: int) -> None:
        """Phase 4 (§5.2, §5.6): swaps in a brand-new Semaphore(N). Sessions
        already running hold a reference to the OLD semaphore (captured when
        their `async with self._semaphore:` block was entered) and finish
        under the old cap undisturbed; only sessions that start *after* this
        call acquire the new one — exactly the "next batch" semantics
        `asyncio.Semaphore` can't give you via live resizing."""
        if max_concurrent == self._current_concurrency:
            return
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._current_concurrency = max_concurrent
        logger.info("browser_engine_concurrency_changed", max_concurrent=max_concurrent)

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self._headless)
        logger.info("browser_engine_started", headless=self._headless)

    async def stop(self) -> None:
        if self._browser is not None:
            await self._browser.close()
        if self._playwright is not None:
            await self._playwright.stop()
        logger.info("browser_engine_stopped")

    async def __aenter__(self) -> "BrowserEngine":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.stop()

    async def run_session(
        self,
        url: str,
        *,
        proxy: Proxy | None = None,
        credentials: dict | None = None,
        login_selectors: dict | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        take_screenshot: bool = True,
        screenshot_dir: str = "screenshots",
    ) -> BrowserRunResult:
        """Lifecycle (§5.2): semaphore acquire -> context create -> navigate
        (human-like) -> auto-login if credentials given -> metrics capture ->
        screenshot -> context close -> semaphore release. Never raises —
        failures come back as a result with success=False so the caller can
        persist a structured error (§5.2).

        `credentials` (already-decrypted {"email", "password"}) and
        `login_selectors` come from the caller (§Product-readiness) — this
        method never touches the database itself, and never logs either
        dict's contents."""
        if self._browser is None:
            raise RuntimeError("BrowserEngine.start() must be called before run_session()")

        async with self._semaphore:
            started = time.monotonic()
            fingerprint = random_fingerprint()
            context = None
            try:
                context_kwargs: dict = {
                    "viewport": fingerprint.viewport,
                    "user_agent": fingerprint.user_agent,
                    "timezone_id": fingerprint.timezone_id,
                    "locale": fingerprint.locale,
                }
                if proxy is not None:
                    context_kwargs["proxy"] = _playwright_proxy_config(proxy)

                context = await self._browser.new_context(**context_kwargs)
                await apply_stealth(context)
                await install_metrics_observer(context)

                page = await context.new_page()
                await think_time(0.3, 1.0)
                await page.goto(url, timeout=timeout_seconds * 1000, wait_until="load")

                if credentials is not None:
                    await think_time(0.3, 0.8)
                    await auto_login(page, credentials, login_selectors)

                await human_scroll(page)
                await think_time(0.3, 1.0)

                metrics = await read_performance_metrics(page)

                screenshot_path = None
                if take_screenshot:
                    Path(screenshot_dir).mkdir(parents=True, exist_ok=True)
                    screenshot_path = str(Path(screenshot_dir) / f"{uuid.uuid4()}.png")
                    await page.screenshot(path=screenshot_path)

                duration_ms = int((time.monotonic() - started) * 1000)
                logger.info("browser_session_succeeded", url=url, duration_ms=duration_ms, metrics=metrics)
                return BrowserRunResult(
                    success=True,
                    fingerprint=fingerprint,
                    metrics=metrics,
                    screenshot_path=screenshot_path,
                    duration_ms=duration_ms,
                )
            except Exception as exc:
                duration_ms = int((time.monotonic() - started) * 1000)
                logger.warning("browser_session_failed", url=url, error=str(exc), duration_ms=duration_ms)
                return BrowserRunResult(
                    success=False,
                    fingerprint=fingerprint,
                    error=str(exc),
                    duration_ms=duration_ms,
                )
            finally:
                if context is not None:
                    await context.close()
