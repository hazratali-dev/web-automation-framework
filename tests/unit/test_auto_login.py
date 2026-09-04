import asyncio

import pytest

from src.infrastructure.browser.auto_login import auto_login


@pytest.fixture(autouse=True)
def fast_sleep(monkeypatch):
    """auto_login()'s human_type()/think_time() calls do real asyncio.sleep()
    per character — harmless in production, but would make this whole test
    file take several real seconds for no reason. Patch it to instant."""

    async def _no_sleep(*_args, **_kwargs):
        return None

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)


class FakePage:
    """Minimal Playwright Page stand-in — enough to drive auto_login's
    selector-detection branch without a real browser. `present_selectors` is
    the set of CSS selectors that would find an element on this fake page."""

    def __init__(self, present_selectors: set[str]) -> None:
        self.present_selectors = present_selectors
        self.typed: list[tuple[str, str]] = []
        self.clicked: list[str] = []
        self.pressed: list[str] = []

    async def query_selector(self, selector: str):
        return object() if selector in self.present_selectors else None

    async def click(self, selector: str) -> None:
        self.clicked.append(selector)

    async def wait_for_load_state(self, state: str) -> None:
        pass

    class _Keyboard:
        def __init__(self, page: "FakePage") -> None:
            self._page = page

        async def type(self, char: str) -> None:
            self._page.typed.append(("keyboard", char))

        async def press(self, key: str) -> None:
            self._page.pressed.append(key)

    @property
    def keyboard(self):
        return FakePage._Keyboard(self)


async def test_single_password_form_fills_only_password():
    page = FakePage(present_selectors={'input[type="password"]', 'button[type="submit"]'})
    credentials = {"email": None, "password": "shop123", "login_type": "single_password"}

    result = await auto_login(page, credentials)

    assert result is True
    # human_type() clicks the field before typing into it, then the submit
    # click at the end — no email selector ever appears in this sequence.
    assert page.clicked == ['input[type="password"]', 'button[type="submit"]']
    assert "".join(c for _, c in page.typed) == "shop123"


async def test_email_password_form_fills_both_fields():
    page = FakePage(
        present_selectors={'input[type="email"]', 'input[type="password"]', 'button[type="submit"]'}
    )
    credentials = {"email": "user@example.com", "password": "hunter2", "login_type": "email_password"}

    result = await auto_login(page, credentials)

    assert result is True
    typed = "".join(c for _, c in page.typed)
    assert typed == "user@example.comhunter2"


async def test_email_password_login_type_degrades_to_password_only_when_no_email_field_exists():
    """The stored login_type says email_password, but this particular page
    (e.g. Shopify storefront) turns out to have no email field — should
    still log in with just the password rather than failing outright."""
    page = FakePage(present_selectors={'input[type="password"]'})
    credentials = {"email": "user@example.com", "password": "shop123", "login_type": "email_password"}

    result = await auto_login(page, credentials)

    assert result is True
    assert "".join(c for _, c in page.typed) == "shop123"


async def test_no_password_field_at_all_fails_gracefully():
    page = FakePage(present_selectors=set())
    credentials = {"email": "user@example.com", "password": "x", "login_type": "email_password"}

    result = await auto_login(page, credentials)

    assert result is False
    assert page.typed == []


async def test_single_password_ignores_email_field_even_if_present_on_page():
    """login_type explicitly says single_password — email is skipped even
    though an email field exists on the page (explicit setting wins)."""
    page = FakePage(present_selectors={'input[type="email"]', 'input[type="password"]'})
    credentials = {"email": "user@example.com", "password": "shop123", "login_type": "single_password"}

    result = await auto_login(page, credentials)

    assert result is True
    assert "".join(c for _, c in page.typed) == "shop123"
