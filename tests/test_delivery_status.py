from app.delivery_status import delivery_status_label


def test_known_delivery_statuses_are_translated_to_vietnamese() -> None:
    assert delivery_status_label("request_received") == "Đã tiếp nhận yêu cầu"
    assert delivery_status_label("on_the_way") == "Đang vận chuyển"
    assert delivery_status_label("out_for_delivery") == "Đang giao hàng"
    assert delivery_status_label("delivered") == "Giao thành công"
    assert delivery_status_label("returning") == "Đang hoàn hàng"
    assert delivery_status_label("returned") == "Đã hoàn hàng"
    assert delivery_status_label("canceled") == "Đã hủy"


def test_delivery_status_preserves_existing_vietnamese_label() -> None:
    assert delivery_status_label("Đang giao hàng") == "Đang giao hàng"


def test_unknown_or_missing_delivery_status_has_safe_vietnamese_fallback() -> None:
    assert delivery_status_label("carrier_private_state") == "Chưa xác định"
    assert delivery_status_label(None) == "Chưa có trạng thái"
