from app.page_identity_sync import extract_page_customer_records


def test_extracts_page_customer_identity_from_message_context() -> None:
    records = extract_page_customer_records(
        "page-1",
        "conversation-1",
        {
            "customers": [
                {
                    "id": "page-customer-1",
                    "customer_id": "customer-1",
                    "fb_id": "psid-1",
                    "global_id": "global-1",
                    "name": "Customer One",
                }
            ]
        },
    )

    assert records == [
        {
            "page_id": "page-1",
            "page_customer_id": "page-customer-1",
            "source_customer_id": "customer-1",
            "psid": "psid-1",
            "global_id": "global-1",
            "name": "Customer One",
            "conversation_id": "conversation-1",
            "raw_payload": {
                "id": "page-customer-1",
                "customer_id": "customer-1",
                "fb_id": "psid-1",
                "global_id": "global-1",
                "name": "Customer One",
            },
        }
    ]


def test_falls_back_to_psid_when_page_customer_id_is_missing() -> None:
    records = extract_page_customer_records(
        "page-1",
        "conversation-1",
        {"customers": [{"fb_id": "psid-1", "name": "Customer One"}]},
    )

    assert records[0]["page_customer_id"] == "psid:psid-1"
    assert records[0]["psid"] == "psid-1"
