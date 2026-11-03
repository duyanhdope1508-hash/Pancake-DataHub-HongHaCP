from app.import_page_connectors import merge_discovered_pages
from app.page_connectors import PancakePageConnector
from app.pancake_user import extract_available_page_tokens


def test_extracts_admin_page_tokens_from_activated_pages() -> None:
    result = extract_available_page_tokens(
        {
            "success": True,
            "pages": {
                "activated": [
                    {
                        "id": "page-1",
                        "name": "First Page",
                        "settings": {"page_access_token": "valid-page-one-token"},
                    },
                    {
                        "id": "page-2",
                        "name": "No Admin Token",
                        "settings": {},
                    },
                ]
            },
        }
    )

    assert result == [
        {
            "page_id": "page-1",
            "page_name": "First Page",
            "page_access_token": "valid-page-one-token",
        }
    ]


def test_merge_discovered_pages_skips_existing_page() -> None:
    existing = PancakePageConnector(
        page_id="page-1",
        page_access_token="valid-existing-token",
    )
    merged, added = merge_discovered_pages(
        [existing],
        [
            {
                "page_id": "page-1",
                "page_name": "Existing",
                "page_access_token": "different-valid-token",
            },
            {
                "page_id": "page-2",
                "page_name": "New",
                "page_access_token": "valid-new-token",
            },
        ],
    )

    assert [connector.page_id for connector in merged] == ["page-1", "page-2"]
    assert [page["page_id"] for page in added] == ["page-2"]
