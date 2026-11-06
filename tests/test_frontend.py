from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[1] / "frontend"


def test_frontend_assets_exist() -> None:
    assert (FRONTEND / "index.html").is_file()
    assert (FRONTEND / "styles.css").is_file()
    assert (FRONTEND / "app.js").is_file()


def test_frontend_requires_login_before_loading_data() -> None:
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    javascript = (FRONTEND / "app.js").read_text(encoding="utf-8")

    assert 'id="loginForm"' in html
    assert 'id="appShell" class="app-shell" hidden' in html
    assert "/api/auth/me" in javascript
    assert "/api/auth/login" in javascript
    assert "/api/auth/logout" in javascript
    assert 'id="revenueSummaryCard"' in html
    assert "user.can_sync" in javascript
    assert "user.can_view_revenue" in javascript
    assert "tối đa 500 đơn/file, 5 lần/giờ và 2.000 đơn/24 giờ" in javascript


def test_admin_can_manage_staff_and_shop_assignments_from_ui() -> None:
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    javascript = (FRONTEND / "app.js").read_text(encoding="utf-8")

    for element_id in (
        'id="manageStaffButton"',
        'id="staffDialog"',
        'id="staffForm"',
        'id="staffDisplayName"',
        'id="staffUsername"',
        'id="staffResetPassword"',
        'id="temporaryCredential"',
        'id="temporaryPassword"',
        'id="staffIsActive"',
        'id="staffShopOptions"',
        'id="staffList"',
    ):
        assert element_id in html
    assert "/api/admin/users" in javascript
    assert 'method: isEditing ? "PUT" : "POST"' in javascript
    assert "result.temporary_password" in javascript
    assert "navigator.clipboard.writeText" in javascript
    assert "user.role !== \"admin\"" in javascript


def test_users_can_change_temporary_password_before_loading_data() -> None:
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    javascript = (FRONTEND / "app.js").read_text(encoding="utf-8")

    for element_id in (
        'id="changePasswordButton"',
        'id="passwordDialog"',
        'id="passwordForm"',
        'id="currentPassword"',
        'id="newPassword"',
        'id="confirmNewPassword"',
    ):
        assert element_id in html
    assert "/api/auth/change-password" in javascript
    assert "auth.user.must_change_password" in javascript
    assert "if (wasRequired) await loadApplicationData()" in javascript


def test_admin_can_filter_and_page_through_audit_log() -> None:
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    javascript = (FRONTEND / "app.js").read_text(encoding="utf-8")

    for element_id in (
        'id="auditLogButton"',
        'id="auditDialog"',
        'id="auditActionFilter"',
        'id="auditBody"',
        'id="previousAuditPage"',
        'id="nextAuditPage"',
    ):
        assert element_id in html
    assert "/api/admin/audit-logs" in javascript
    assert "AUDIT_ACTION_LABELS" in javascript
    assert '"orders.view_detail": "Xem chi tiết đơn"' in javascript
    assert "item.ip_address" in javascript
    assert "auditDevice(item.user_agent)" in javascript
    assert "user.role !== \"admin\"" in javascript


def test_mutating_requests_send_session_bound_csrf_header() -> None:
    javascript = (FRONTEND / "app.js").read_text(encoding="utf-8")

    assert 'readCookie("hongha_csrf")' in javascript
    assert 'headers.set("X-CSRF-Token", state.csrfToken)' in javascript
    assert 'secureFetch("/api/auth/logout"' in javascript
    assert 'secureFetch("/api/auth/change-password"' in javascript
    assert 'secureFetch("/api/sync"' in javascript


def test_frontend_uses_safe_dom_rendering() -> None:
    javascript = (FRONTEND / "app.js").read_text(encoding="utf-8")
    assert ".innerHTML" not in javascript
    assert "textContent" in javascript


def test_frontend_has_search_filters_and_dialog() -> None:
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    javascript = (FRONTEND / "app.js").read_text(encoding="utf-8")
    for element_id in (
        'id="filterForm"',
        'id="systemStateText"',
        'id="syncNow"',
        'id="searchInput"',
        'id="shopFilter"',
        'id="pageFilter"',
        'id="statusFilter"',
        'id="sortFilter"',
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
        'id="exportExcel"',
        'id="savedFilterSelect"',
        'id="savedFilterName"',
        'id="saveFilter"',
        'id="deleteFilter"',
        'id="savedFilterMessage"',
        'id="filteredOrders"',
        'id="filteredRevenue"',
        'id="filteredDelivered"',
        'id="filteredFailed"',
        'id="ordersBody"',
        'id="firstPage"',
        'id="pageButtons"',
        'id="lastPage"',
        'id="pageJumpForm"',
        'id="pageJumpInput"',
        'id="orderDialog"',
    ):
        assert element_id in html
    assert "paginationTokens" in javascript
    assert "goToPage(state.totalPages)" in javascript
    assert "pageJumpInput.valueAsNumber" in javascript
    assert "status.delivery_status_label" in javascript
    assert "order.delivery_status_label" in javascript
    assert "shipping.delivery_status_label" in javascript


def test_frontend_saved_filters_are_local_and_bounded() -> None:
    javascript = (FRONTEND / "app.js").read_text(encoding="utf-8")
    assert "localStorage" in javascript
    assert "MAX_SAVED_FILTERS = 20" in javascript
    assert "captureFilterValues" in javascript
    assert "applySavedFilter" in javascript


def test_frontend_uses_compact_dashboard_with_help_tooltips() -> None:
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    assert "Đơn hàng từ mọi page, trong một nơi." not in html
    assert 'class="overview"' in html
    assert html.count('class="info-tip') >= 6
    assert "data-tooltip=" in html
    assert "HỒNG HÀ CP" in html
    assert 'class="brand-accent">DATAHUB' in html
    assert "info-tip drop-down" in html
    assert 'class="site-footer"' in html
    assert "Developed by Daniel Ng" in html

