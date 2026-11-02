from app.inspection import summarize_records


def test_summary_contains_only_structure() -> None:
    records = [
        {
            "id": "order-1",
            "customer_name": "Sensitive Name",
            "phone_number": "0900000000",
            "updated_at": "2026-11-02T00:00:00Z",
        },
        {
            "id": "order-2",
            "customer_name": "Another Name",
            "total": 100_000,
        },
    ]

    result = summarize_records(records)

    assert result["sample_count"] == 2
    assert result["fields"] == [
        "customer_name",
        "id",
        "phone_number",
        "total",
        "updated_at",
    ]
    assert result["id_fields_present"] == ["id"]
    assert result["update_fields_present"] == ["updated_at"]
    assert "Sensitive Name" not in str(result)
    assert "0900000000" not in str(result)


def test_summary_handles_empty_page() -> None:
    assert summarize_records([]) == {
        "sample_count": 0,
        "fields": [],
        "id_fields_present": [],
        "update_fields_present": [],
    }

