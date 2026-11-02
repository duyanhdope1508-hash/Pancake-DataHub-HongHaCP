from app.pancake import extract_collection


def test_extracts_direct_collection() -> None:
    assert extract_collection([{"id": 1}], "orders") == [{"id": 1}]


def test_extracts_named_collection() -> None:
    payload = {"success": True, "shops": [{"id": 123, "name": "Shop A"}]}
    assert extract_collection(payload, "shops") == [{"id": 123, "name": "Shop A"}]


def test_extracts_nested_data_collection() -> None:
    payload = {"data": {"orders": [{"id": "DH001"}]}}
    assert extract_collection(payload, "orders") == [{"id": "DH001"}]


def test_ignores_non_object_items() -> None:
    payload = {"orders": [None, "bad", {"id": 1}]}
    assert extract_collection(payload, "orders") == [{"id": 1}]

