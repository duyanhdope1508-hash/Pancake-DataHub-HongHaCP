from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[1] / "frontend"


def test_frontend_assets_exist() -> None:
    assert (FRONTEND / "index.html").is_file()
    assert (FRONTEND / "styles.css").is_file()
    assert (FRONTEND / "app.js").is_file()


def test_frontend_uses_safe_dom_rendering() -> None:
    javascript = (FRONTEND / "app.js").read_text(encoding="utf-8")
    assert ".innerHTML" not in javascript
    assert "textContent" in javascript


def test_frontend_has_search_filters_and_dialog() -> None:
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    for element_id in (
        'id="filterForm"',
        'id="searchInput"',
        'id="pageFilter"',
        'id="statusFilter"',
        'id="ordersBody"',
        'id="orderDialog"',
    ):
        assert element_id in html

