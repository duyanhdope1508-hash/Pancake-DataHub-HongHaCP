from app.probe_key import summarize_shops


def test_summarize_shops_returns_only_safe_fields() -> None:
    shops = summarize_shops(
        [
            {
                "id": 123,
                "name": "Cửa hàng mới",
                "access_token": "must-not-be-returned",
            }
        ]
    )

    assert shops == [{"shop_id": "123", "shop_name": "Cửa hàng mới"}]


def test_summarize_shops_skips_records_without_id() -> None:
    assert summarize_shops([{"name": "Thiếu ID"}]) == []
