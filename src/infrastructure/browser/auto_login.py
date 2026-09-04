"""Best-effort auto-login for targets that have credentials configured
(dashboard-managed, §Product-readiness). Never logs the email/password
themselves — only booleans and selector strings (which fields were found),
so structlog output (even with exc_info=True) can never leak a secret."""

import structlog

from src.infrastructure.browser.behaviors.scroll import think_time
from src.infrastructure.browser.behaviors.typing import human_type

logger = structlog.get_logger(__name__)

DEFAULT_EMAIL_SELECTORS = [
    'input[type="email"]',
    'input[name="email"]',
    'input[name="username"]',
    "#email",
    "#username",
]
DEFAULT_PASSWORD_SELECTORS = ['input[type="password"]', "#password"]
DEFAULT_SUBMIT_SELECTORS = [
    'button[type="submit"]',
    'input[type="submit"]',
    'button:has-text("Log in")',
    'button:has-text("Sign in")',
]


async def _find_selector(page, candidates: list[str | None]) -> str | None:
    for selector in candidates:
        if not selector:
            continue
        try:
            if await page.query_selector(selector) is not None:
                return selector
        except Exception:
            continue  # an invalid/unsupported selector string — just skip it
    return None


async def auto_login(page, credentials: dict, selectors: dict | None = None) -> bool:
    """Tries a per-target selector override first (`target.config.
    login_selectors`), then a handful of common login-form heuristics.
    Returns True if it found a form and submitted it, False if it couldn't
    find matching fields — a missing/absent login form is not treated as an
    error, since not every target actually needs a login (§Product-readiness
    point 3: "যদি না থাকে, তাহলে কোনো অ্যাকশন নেবে না")."""
    selectors = selectors or {}

    email_selector = await _find_selector(page, [selectors.get("email_selector"), *DEFAULT_EMAIL_SELECTORS])
    password_selector = await _find_selector(
        page, [selectors.get("password_selector"), *DEFAULT_PASSWORD_SELECTORS]
    )

    if not email_selector or not password_selector:
        logger.warning(
            "auto_login_fields_not_found",
            email_field_found=bool(email_selector),
            password_field_found=bool(password_selector),
        )
        return False

    try:
        await human_type(page, email_selector, credentials["email"])
        await think_time(0.2, 0.6)
        await human_type(page, password_selector, credentials["password"])
        await think_time(0.2, 0.6)

        submit_selector = await _find_selector(page, [selectors.get("submit_selector"), *DEFAULT_SUBMIT_SELECTORS])
        if submit_selector:
            await page.click(submit_selector)
        else:
            await page.keyboard.press("Enter")
        await page.wait_for_load_state("load")
    except Exception:
        # Deliberately no `error=str(exc)` here — an unexpected Playwright
        # exception's message is not something we want to bet the password
        # never ends up embedded in, given a login form's own error text
        # sometimes gets echoed back into exception messages by some sites.
        logger.warning("auto_login_submit_failed", email_selector=email_selector, password_selector=password_selector)
        return False

    logger.info("auto_login_submitted", email_selector=email_selector, password_selector=password_selector)
    return True
