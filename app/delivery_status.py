DELIVERY_STATUS_LABELS = {
    "new": "Mới tạo",
    "created": "Đã tạo vận đơn",
    "pending": "Chờ xử lý",
    "request_received": "Đã tiếp nhận yêu cầu",
    "confirmed": "Đã xác nhận vận chuyển",
    "ready_to_pick": "Chờ lấy hàng",
    "ready_to_pickup": "Chờ lấy hàng",
    "ready_to_ship": "Chờ lấy hàng",
    "waiting_for_pickup": "Chờ lấy hàng",
    "picking": "Đang lấy hàng",
    "picking_up": "Đang lấy hàng",
    "picked_up": "Đã lấy hàng",
    "shipped": "Đã gửi vận chuyển",
    "shipping": "Đang vận chuyển",
    "in_transit": "Đang vận chuyển",
    "on_the_way": "Đang vận chuyển",
    "out_for_delivery": "Đang giao hàng",
    "delivering": "Đang giao hàng",
    "delivered": "Giao thành công",
    "success": "Giao thành công",
    "partially_delivered": "Giao một phần",
    "delivery_failed": "Giao không thành công",
    "failed": "Giao không thành công",
    "undeliverable": "Không thể giao hàng",
    "delayed": "Giao hàng chậm",
    "returning": "Đang hoàn hàng",
    "waiting_for_return": "Chờ hoàn hàng",
    "returned": "Đã hoàn hàng",
    "return_received": "Đã nhận hàng hoàn",
    "canceled": "Đã hủy",
    "cancelled": "Đã hủy",
    "lost": "Thất lạc",
    "damaged": "Hư hỏng",
}

_VIETNAMESE_WORDS = (
    "giao",
    "vận chuyển",
    "lấy hàng",
    "hoàn",
    "hủy",
    "chờ",
    "thành công",
    "thất bại",
    "đã nhận",
)


def delivery_status_label(value: str | None) -> str:
    clean_value = (value or "").strip()
    if not clean_value:
        return "Chưa có trạng thái"
    normalized = clean_value.lower().replace("-", "_").replace(" ", "_")
    known_label = DELIVERY_STATUS_LABELS.get(normalized)
    if known_label:
        return known_label
    lower_value = clean_value.lower()
    if any(word in lower_value for word in _VIETNAMESE_WORDS):
        return clean_value
    return "Chưa xác định"
