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
    'button:has-text("Enter")',  # Shopify storefront password page
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
    """Recognizes two form shapes (§Product-readiness — Shopify storefront /
    cPanel-style single-password pages don't have an email field at all):

    - email + password — the common case.
    - password only — no email field is looked for (or filled) at all.

    Which one applies is decided by *live DOM inspection*, not by trusting
    `credentials["login_type"]` blindly: if that key says "single_password",
    the email field is skipped even if one happens to exist (explicit
    dashboard setting wins); otherwise, if no email field can be found on
    the page, it degrades to password-only automatically rather than giving
    up — a stored "email_password" setting on a page that turns out to be
    password-only shouldn't just silently fail to log in.

    Returns True if it found a password field and submitted, False if it
    couldn't (no password field at all is the only hard failure — a missing
    login form isn't an error, §Product-readiness point 3)."""
    selectors = selectors or {}
    login_type = credentials.get("login_type", "email_password")

    password_selector = await _find_selector(page, [selectors.get("password_selector"), *DEFAULT_PASSWORD_SELECTORS])
    if not password_selector:
        logger.warning("auto_login_fields_not_found", password_field_found=False)
        return False

    email_selector = None
    if login_type != "single_password":
        email_selector = await _find_selector(page, [selectors.get("email_selector"), *DEFAULT_EMAIL_SELECTORS])

    fill_email = bool(email_selector and credentials.get("email"))
    logger.info(
        "auto_login_form_detected",
        mode="email_password" if fill_email else "single_password",
        email_field_found=bool(email_selector),
    )

    try:
        if fill_email:
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
