from app.search import escape_like, mask_phone


def test_mask_phone_preserves_only_last_four_characters() -> None:
    assert mask_phone("0912345678") == "******5678"


def test_mask_phone_handles_short_and_missing_values() -> None:
    assert mask_phone("123") == "***"
    assert mask_phone(None) is None


def test_escape_like_prevents_wildcard_input() -> None:
    assert escape_like(r"100%_done\now") == r"100\%\_done\\now"

