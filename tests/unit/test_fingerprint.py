from src.infrastructure.browser.fingerprint import LOCALES, TIMEZONES, USER_AGENTS, VIEWPORTS, random_fingerprint


def test_random_fingerprint_picks_from_known_pools():
    fp = random_fingerprint()
    assert fp.viewport in VIEWPORTS
    assert fp.user_agent in USER_AGENTS
    assert fp.timezone_id in TIMEZONES
    assert fp.locale in LOCALES


def test_random_fingerprint_varies_across_calls():
    fingerprints = {random_fingerprint().user_agent for _ in range(50)}
    assert len(fingerprints) > 1  # extremely unlikely to always pick the same one


def test_as_config_dict_only_carries_the_session_metadata_fields():
    fp = random_fingerprint()
    config = fp.as_config_dict()
    assert set(config.keys()) == {"timezone_id", "locale"}
