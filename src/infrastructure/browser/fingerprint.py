import random
from dataclasses import dataclass

# Small, curated pools — real-world common values, not an exhaustive
# fingerprint database. Good enough for "randomize per session" (§5.2);
# a dedicated fingerprint-database library is a future upgrade if needed.
VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1280, "height": 720},
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
]

TIMEZONES = [
    "Asia/Dhaka",
    "America/New_York",
    "Europe/London",
    "Asia/Kolkata",
    "Asia/Singapore",
]

LOCALES = ["en-US", "en-GB", "bn-BD", "en-IN"]


@dataclass
class Fingerprint:
    viewport: dict
    user_agent: str
    timezone_id: str
    locale: str

    def as_config_dict(self) -> dict:
        """What gets persisted into sessions.fingerprint_config (§3)."""
        return {"timezone_id": self.timezone_id, "locale": self.locale}


def random_fingerprint() -> Fingerprint:
    return Fingerprint(
        viewport=random.choice(VIEWPORTS),
        user_agent=random.choice(USER_AGENTS),
        timezone_id=random.choice(TIMEZONES),
        locale=random.choice(LOCALES),
    )
