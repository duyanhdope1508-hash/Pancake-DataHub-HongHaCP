from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[1] / "frontend"


def test_frontend_assets_exist() -> None:
    assert (FRONTEND / "index.html").is_file()
    assert (FRONTEND / "styles.css").is_file()
    assert (FRONTEND / "app.js").is_file()
    assert (FRONTEND / "favicon.svg").is_file()


def test_frontend_uses_versioned_assets() -> None:
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")

    assert 'href="/assets/favicon.svg?v=1"' in html
    assert 'href="/assets/styles.css?v=36"' in html
    assert 'src="/assets/app.js?v=37"' in html


def test_overview_counts_refresh_without_reloading_the_page() -> None:
    javascript = (FRONTEND / "app.js").read_text(encoding="utf-8")

    assert "integerFormatter.format(data.core_orders)" in javascript
    assert "integerFormatter.format(data.shops)" in javascript
    assert "}, 15_000);" in javascript
    assert 'document.addEventListener("visibilitychange"' in javascript


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


def test_authenticated_screen_is_watermarked_per_account() -> None:
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    javascript = (FRONTEND / "app.js").read_text(encoding="utf-8")
    css = (FRONTEND / "styles.css").read_text(encoding="utf-8")

    assert 'id="screenWatermark"' in html
    assert "renderScreenWatermark" in javascript
    assert "state.currentUser.username" in javascript
    assert "60_000" in javascript
    assert ".screen-watermark" in css
    assert "pointer-events: none" in css


def test_authenticated_ui_discourages_common_inspection_shortcuts() -> None:
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    javascript = (FRONTEND / "app.js").read_text(encoding="utf-8")

    assert 'id="inspectionNotice"' in html
    assert 'addEventListener("contextmenu"' in javascript
    assert 'addEventListener("keydown"' in javascript
    assert 'key === "F12"' in javascript
    assert '["I", "J", "C"]' in javascript
    assert 'key === "U"' in javascript
    assert "event.preventDefault()" in javascript


def test_docked_devtools_activates_full_screen_privacy_shield() -> None:
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    javascript = (FRONTEND / "app.js").read_text(encoding="utf-8")
    css = (FRONTEND / "styles.css").read_text(encoding="utf-8")

    assert 'id="devtoolsPrivacyShield"' in html
    assert "devtoolsLikelyDocked" in javascript
    assert "window.outerWidth - window.innerWidth" in javascript
    assert "window.outerHeight - window.innerHeight" in javascript
    assert 'classList.toggle("devtools-privacy-active", active)' in javascript
    assert "window.setInterval(updateDevtoolsPrivacyShield, 750)" in javascript
    assert ".devtools-privacy-shield" in css
    assert "body.devtools-privacy-active .app-shell" in css
    assert "filter: blur(22px)" in css


def test_admin_can_manage_staff_and_shop_assignments_from_ui() -> None:
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    javascript = (FRONTEND / "app.js").read_text(encoding="utf-8")

    for element_id in (
        'id="manageStaffButton"',
        'id="staffDialog"',
        'id="staffForm"',
        'id="staffDisplayName"',
        'id="staffUsername"',
        'id="staffRole"',
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
    assert "state.currentUser?.is_root_admin" in javascript
    assert '"Tất cả tài khoản"' in javascript
    assert '"Tất cả nhân viên"' in javascript
    assert '"Nhật ký nhân viên"' in javascript
    assert "user.is_root_admin" in javascript
    assert "user.can_manage" in javascript


def test_account_roster_has_an_independent_scroll_area() -> None:
    css = (FRONTEND / "styles.css").read_text(encoding="utf-8")

    assert ".staff-roster" in css
    assert "flex-direction: column" in css
    assert ".staff-list" in css
    assert "scrollbar-gutter: stable" in css
    assert "overflow-y: auto" in css


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
        'id="auditActorFilter"',
        'id="auditResultFilter"',
        'id="auditIpFilter"',
        'id="auditDateFrom"',
        'id="auditDateTo"',
        'id="applyAuditFilters"',
        'id="resetAuditFilters"',
        'id="auditBody"',
        'id="previousAuditPage"',
        'id="nextAuditPage"',
    ):
        assert element_id in html
    assert "/api/admin/audit-logs" in javascript
    assert "AUDIT_ACTION_LABELS" in javascript
    assert '"orders.view_detail": "Xem chi tiết đơn"' in javascript
    assert '"orders.view_detail.daily": "Tổng hợp lượt xem đơn"' in javascript
    assert "item.ip_address" in javascript
    assert "auditDevice(item.user_agent)" in javascript
    assert 'params.set("actor_user_id"' in javascript
    assert 'params.set("ip_address"' in javascript
    assert 'params.set("date_from"' in javascript
    assert "user.role !== \"admin\"" in javascript


def test_admin_receives_bulk_access_security_alerts() -> None:
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    javascript = (FRONTEND / "app.js").read_text(encoding="utf-8")

    for element_id in (
        'id="securityAlertsButton"',
        'id="securityAlertCount"',
        'id="securityAlertsDialog"',
        'id="securityAlertsList"',
        'id="securityAlertsEmpty"',
    ):
        assert element_id in html
    assert "/api/admin/security-alerts?hours=24&limit=50" in javascript
    assert "security.high_usage" in javascript
    assert "security.rate_limit" in javascript
    assert "60_000" in javascript
    assert '"Cảnh báo nhân viên lấy dữ liệu hàng loạt"' in javascript


def test_mutating_requests_send_session_bound_csrf_header() -> None:
    javascript = (FRONTEND / "app.js").read_text(encoding="utf-8")

    assert 'readCookie("hongha_csrf")' in javascript
    assert 'headers.set("X-CSRF-Token", state.csrfToken)' in javascript
    assert 'secureFetch("/api/auth/logout"' in javascript
    assert 'secureFetch("/api/auth/change-password"' in javascript
    assert 'secureFetch("/api/sync"' in javascript
    assert 'fetchJson("/api/sync/status")' in javascript
    assert 'payload.status !== "started"' in javascript
    assert '"staff.delete": "Xóa nhân viên"' in javascript
    assert 'method: "DELETE"' in javascript
    assert 'createElement("button", "delete-staff-button", "Xóa")' in javascript
    assert "Đã thu hồi quyền và phiên đăng nhập" in javascript


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
        'id="selectionSummary"',
        'id="selectAllFiltered"',
        'id="clearOrderSelection"',
        'id="selectCurrentPage"',
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
        'id="helpButton"',
        'id="helpDialog"',
        'id="closeHelpDialog"',
    ):
        assert element_id in html
    assert "paginationTokens" in javascript
    assert "goToPage(state.totalPages)" in javascript
    assert "pageJumpInput.valueAsNumber" in javascript
    assert "status.delivery_status_label" in javascript
    assert "order.delivery_status_label" in javascript
    assert "Đếm chính xác trên toàn bộ dữ liệu theo bộ lọc" in html
    assert "chậm phản ánh đơn vừa đồng bộ tối đa 5 phút" in html
    assert "shipping.delivery_status_label" in javascript
    assert 'selection_mode: state.allMatchingSelected ? "filtered" : "selected"' in javascript
    assert 'secureFetch("/api/orders/export"' in javascript
    assert "state.appliedExportFilters = exportFilters" in javascript
    assert 'elements.helpDialog.showModal()' in javascript
    assert 'elements.helpDialog.close()' in javascript
    assert "Nhân viên được xuất tối đa 500 đơn mỗi file" in html
    assert "Hệ thống tự lấy đơn mới khoảng 12 giờ một lần" in html


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

