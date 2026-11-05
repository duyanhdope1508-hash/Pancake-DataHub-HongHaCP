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
        'id="systemStateText"',
        'id="searchInput"',
        'id="shopFilter"',
        'id="pageFilter"',
        'id="statusFilter"',
        'id="toggleAdvanced"',
        'id="advancedFilters"',
        'id="productFilter"',
        'id="carrierFilter"',
        'id="deliveryStatusFilter"',
        'id="dateFromFilter"',
        'id="dateToFilter"',
        'id="minTotalFilter"',
        'id="maxTotalFilter"',
        'id="trackingFilter"',
        'id="sentFilter"',
        'id="returnedFilter"',
        'id="resetFilters"',
        'id="filteredOrders"',
        'id="filteredRevenue"',
        'id="filteredDelivered"',
        'id="filteredFailed"',
        'id="ordersBody"',
        'id="orderDialog"',
    ):
        assert element_id in html

