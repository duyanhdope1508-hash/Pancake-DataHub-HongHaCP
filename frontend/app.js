const state = {
  pageNumber: 1,
  pageSize: 20,
  totalPages: 1,
  currentUser: null,
  staffManagement: null,
  passwordChangeRequired: false,
  csrfToken: "",
  auditPageNumber: 1,
  auditTotalPages: 1,
  currentPageOrders: [],
  selectedOrderKeys: new Set(),
  allMatchingSelected: false,
  totalMatchingOrders: 0,
  appliedExportFilters: {},
  watermarkTimer: null,
  securityAlertTimer: null,
  inspectionNoticeTimer: null,
};

const elements = {
  loginShell: document.querySelector("#loginShell"),
  loginForm: document.querySelector("#loginForm"),
  loginUsername: document.querySelector("#loginUsername"),
  loginPassword: document.querySelector("#loginPassword"),
  loginError: document.querySelector("#loginError"),
  loginButton: document.querySelector("#loginButton"),
  appShell: document.querySelector("#appShell"),
  screenWatermark: document.querySelector("#screenWatermark"),
  inspectionNotice: document.querySelector("#inspectionNotice"),
  devtoolsPrivacyShield: document.querySelector("#devtoolsPrivacyShield"),
  currentUserName: document.querySelector("#currentUserName"),
  currentUserRole: document.querySelector("#currentUserRole"),
  manageStaffButton: document.querySelector("#manageStaffButton"),
  auditLogButton: document.querySelector("#auditLogButton"),
  securityAlertsButton: document.querySelector("#securityAlertsButton"),
  securityAlertCount: document.querySelector("#securityAlertCount"),
  securityAlertsDialog: document.querySelector("#securityAlertsDialog"),
  securityAlertsDialogTitle: document.querySelector("#securityAlertsDialogTitle"),
  closeSecurityAlertsDialog: document.querySelector("#closeSecurityAlertsDialog"),
  refreshSecurityAlerts: document.querySelector("#refreshSecurityAlerts"),
  securityAlertsList: document.querySelector("#securityAlertsList"),
  securityAlertsEmpty: document.querySelector("#securityAlertsEmpty"),
  securityAlertsError: document.querySelector("#securityAlertsError"),
  helpButton: document.querySelector("#helpButton"),
  helpDialog: document.querySelector("#helpDialog"),
  closeHelpDialog: document.querySelector("#closeHelpDialog"),
  changePasswordButton: document.querySelector("#changePasswordButton"),
  logoutButton: document.querySelector("#logoutButton"),
  passwordDialog: document.querySelector("#passwordDialog"),
  closePasswordDialog: document.querySelector("#closePasswordDialog"),
  passwordForm: document.querySelector("#passwordForm"),
  passwordRequiredNotice: document.querySelector("#passwordRequiredNotice"),
  currentPassword: document.querySelector("#currentPassword"),
  newPassword: document.querySelector("#newPassword"),
  confirmNewPassword: document.querySelector("#confirmNewPassword"),
  passwordFormMessage: document.querySelector("#passwordFormMessage"),
  cancelPasswordChange: document.querySelector("#cancelPasswordChange"),
  savePasswordButton: document.querySelector("#savePasswordButton"),
  staffDialog: document.querySelector("#staffDialog"),
  staffDialogTitle: document.querySelector("#staffDialogTitle"),
  closeStaffDialog: document.querySelector("#closeStaffDialog"),
  staffForm: document.querySelector("#staffForm"),
  staffFormTitle: document.querySelector("#staffFormTitle"),
  staffUserId: document.querySelector("#staffUserId"),
  staffDisplayName: document.querySelector("#staffDisplayName"),
  staffUsername: document.querySelector("#staffUsername"),
  staffRoleField: document.querySelector("#staffRoleField"),
  staffRole: document.querySelector("#staffRole"),
  staffResetPasswordField: document.querySelector("#staffResetPasswordField"),
  staffResetPassword: document.querySelector("#staffResetPassword"),
  staffActiveField: document.querySelector("#staffActiveField"),
  staffIsActive: document.querySelector("#staffIsActive"),
  staffShopSelector: document.querySelector("#staffShopSelector"),
  staffShopOptions: document.querySelector("#staffShopOptions"),
  staffFormMessage: document.querySelector("#staffFormMessage"),
  temporaryCredential: document.querySelector("#temporaryCredential"),
  temporaryUsername: document.querySelector("#temporaryUsername"),
  temporaryPassword: document.querySelector("#temporaryPassword"),
  copyTemporaryCredential: document.querySelector("#copyTemporaryCredential"),
  saveStaffButton: document.querySelector("#saveStaffButton"),
  cancelStaffEdit: document.querySelector("#cancelStaffEdit"),
  selectAllStaffShops: document.querySelector("#selectAllStaffShops"),
  clearStaffShops: document.querySelector("#clearStaffShops"),
  staffList: document.querySelector("#staffList"),
  staffListTitle: document.querySelector("#staffListTitle"),
  staffCount: document.querySelector("#staffCount"),
  auditDialog: document.querySelector("#auditDialog"),
  auditDialogTitle: document.querySelector("#auditDialogTitle"),
  closeAuditDialog: document.querySelector("#closeAuditDialog"),
  auditActionFilter: document.querySelector("#auditActionFilter"),
  auditActorFilter: document.querySelector("#auditActorFilter"),
  auditResultFilter: document.querySelector("#auditResultFilter"),
  auditIpFilter: document.querySelector("#auditIpFilter"),
  auditDateFrom: document.querySelector("#auditDateFrom"),
  auditDateTo: document.querySelector("#auditDateTo"),
  applyAuditFilters: document.querySelector("#applyAuditFilters"),
  resetAuditFilters: document.querySelector("#resetAuditFilters"),
  refreshAuditLog: document.querySelector("#refreshAuditLog"),
  auditBody: document.querySelector("#auditBody"),
  auditEmpty: document.querySelector("#auditEmpty"),
  auditError: document.querySelector("#auditError"),
  previousAuditPage: document.querySelector("#previousAuditPage"),
  nextAuditPage: document.querySelector("#nextAuditPage"),
  auditPageIndicator: document.querySelector("#auditPageIndicator"),
  filterForm: document.querySelector("#filterForm"),
  searchInput: document.querySelector("#searchInput"),
  shopFilter: document.querySelector("#shopFilter"),
  pageFilter: document.querySelector("#pageFilter"),
  statusFilter: document.querySelector("#statusFilter"),
  sortFilter: document.querySelector("#sortFilter"),
  toggleAdvanced: document.querySelector("#toggleAdvanced"),
  resetFilters: document.querySelector("#resetFilters"),
  exportExcel: document.querySelector("#exportExcel"),
  selectionSummary: document.querySelector("#selectionSummary"),
  selectAllFiltered: document.querySelector("#selectAllFiltered"),
  clearOrderSelection: document.querySelector("#clearOrderSelection"),
  selectCurrentPage: document.querySelector("#selectCurrentPage"),
  savedFilterSelect: document.querySelector("#savedFilterSelect"),
  savedFilterName: document.querySelector("#savedFilterName"),
  saveFilter: document.querySelector("#saveFilter"),
  deleteFilter: document.querySelector("#deleteFilter"),
  savedFilterMessage: document.querySelector("#savedFilterMessage"),
  advancedFilters: document.querySelector("#advancedFilters"),
  productFilter: document.querySelector("#productFilter"),
  carrierFilter: document.querySelector("#carrierFilter"),
  deliveryStatusFilter: document.querySelector("#deliveryStatusFilter"),
  dateFromFilter: document.querySelector("#dateFromFilter"),
  dateToFilter: document.querySelector("#dateToFilter"),
  minTotalFilter: document.querySelector("#minTotalFilter"),
  maxTotalFilter: document.querySelector("#maxTotalFilter"),
  trackingFilter: document.querySelector("#trackingFilter"),
  sentFilter: document.querySelector("#sentFilter"),
  returnedFilter: document.querySelector("#returnedFilter"),
  ordersBody: document.querySelector("#ordersBody"),
  emptyState: document.querySelector("#emptyState"),
  errorBanner: document.querySelector("#errorBanner"),
  resultCount: document.querySelector("#resultCount"),
  filteredOrders: document.querySelector("#filteredOrders"),
  revenueSummaryCard: document.querySelector("#revenueSummaryCard"),
  filteredRevenue: document.querySelector("#filteredRevenue"),
  filteredDelivered: document.querySelector("#filteredDelivered"),
  filteredFailed: document.querySelector("#filteredFailed"),
  totalOrders: document.querySelector("#totalOrders"),
  totalShops: document.querySelector("#totalShops"),
  totalPages: document.querySelector("#totalPages"),
  totalStatuses: document.querySelector("#totalStatuses"),
  systemStateText: document.querySelector("#systemStateText"),
  syncNow: document.querySelector("#syncNow"),
  firstPage: document.querySelector("#firstPage"),
  previousPage: document.querySelector("#previousPage"),
  nextPage: document.querySelector("#nextPage"),
  lastPage: document.querySelector("#lastPage"),
  pageButtons: document.querySelector("#pageButtons"),
  pageJumpForm: document.querySelector("#pageJumpForm"),
  pageJumpInput: document.querySelector("#pageJumpInput"),
  pageIndicator: document.querySelector("#pageIndicator"),
  orderDialog: document.querySelector("#orderDialog"),
  dialogTitle: document.querySelector("#dialogTitle"),
  dialogContent: document.querySelector("#dialogContent"),
  closeDialog: document.querySelector("#closeDialog"),
};

const SAVED_FILTERS_STORAGE_KEY = "pancakeDataHub.savedFilters.v1";
const MAX_SAVED_FILTERS = 20;
const DEVTOOLS_SIZE_THRESHOLD = 180;
const AUDIT_ACTION_LABELS = {
  "auth.login": "Đăng nhập",
  "auth.logout": "Đăng xuất",
  "auth.password_change": "Đổi mật khẩu",
  "staff.create": "Tạo nhân viên",
  "staff.update": "Sửa nhân viên",
  "staff.delete": "Xóa nhân viên",
  "admin.create": "Tạo quản trị viên",
  "admin.update": "Sửa quản trị viên",
  "admin.delete": "Xóa quản trị viên",
  "orders.sync": "Đồng bộ đơn",
  "orders.export": "Xuất Excel",
  "orders.view_detail": "Xem chi tiết đơn",
  "orders.view_detail.daily": "Tổng hợp lượt xem đơn",
  "security.high_usage": "Sắp chạm hạn mức dữ liệu",
  "security.rate_limit": "Chặn lấy dữ liệu hàng loạt",
};

const filterElements = {
  query: elements.searchInput,
  shopId: elements.shopFilter,
  pageId: elements.pageFilter,
  businessStatus: elements.statusFilter,
  product: elements.productFilter,
  carrierName: elements.carrierFilter,
  deliveryStatus: elements.deliveryStatusFilter,
  dateFrom: elements.dateFromFilter,
  dateTo: elements.dateToFilter,
  minTotal: elements.minTotalFilter,
  maxTotal: elements.maxTotalFilter,
  hasTracking: elements.trackingFilter,
  sentToCarrier: elements.sentFilter,
  returned: elements.returnedFilter,
  sortBy: elements.sortFilter,
};

const moneyFormatter = new Intl.NumberFormat("vi-VN", {
  style: "currency",
  currency: "VND",
  maximumFractionDigits: 0,
});

const integerFormatter = new Intl.NumberFormat("vi-VN");

function text(value, fallback = "—") {
  return value === null || value === undefined || value === "" ? fallback : String(value);
}

function formatMoney(value, currency = "VND") {
  if (value === null || value === undefined) return "—";
  if (currency === "VND") return moneyFormatter.format(Number(value));
  return `${integerFormatter.format(Number(value))} ${text(currency, "")}`.trim();
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function createElement(tag, className, value) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (value !== undefined) element.textContent = text(value);
  return element;
}

function showError(message) {
  elements.errorBanner.textContent = message;
  elements.errorBanner.hidden = false;
}

function clearError() {
  elements.errorBanner.hidden = true;
  elements.errorBanner.textContent = "";
}

function showSavedFilterMessage(message, isError = false) {
  elements.savedFilterMessage.textContent = message;
  elements.savedFilterMessage.classList.toggle("is-error", isError);
}

function readSavedFilters() {
  try {
    const parsed = JSON.parse(localStorage.getItem(SAVED_FILTERS_STORAGE_KEY) || "[]");
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (preset) =>
        preset &&
        typeof preset.id === "string" &&
        typeof preset.name === "string" &&
        preset.values &&
        typeof preset.values === "object",
    );
  } catch {
    return [];
  }
}

function writeSavedFilters(presets) {
  try {
    localStorage.setItem(SAVED_FILTERS_STORAGE_KEY, JSON.stringify(presets));
    return true;
  } catch {
    showSavedFilterMessage("Trình duyệt không cho phép lưu bộ lọc.", true);
    return false;
  }
}

function captureFilterValues() {
  return Object.fromEntries(
    Object.entries(filterElements).map(([key, element]) => [key, element.value]),
  );
}

function createPresetId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function renderSavedFilters(selectedId = "") {
  const presets = readSavedFilters();
  const options = [createElement("option", "", "Chọn bộ lọc…")];
  options[0].value = "";
  for (const preset of presets) {
    const option = createElement("option", "", preset.name);
    option.value = preset.id;
    options.push(option);
  }
  elements.savedFilterSelect.replaceChildren(...options);
  elements.savedFilterSelect.value = selectedId;
  elements.deleteFilter.disabled = !elements.savedFilterSelect.value;
}

function saveCurrentFilter() {
  showSavedFilterMessage("");
  if (!validateFilters()) return;
  const name = elements.savedFilterName.value.trim();
  if (!name) {
    showSavedFilterMessage("Hãy nhập tên bộ lọc trước khi lưu.", true);
    elements.savedFilterName.focus();
    return;
  }

  const presets = readSavedFilters();
  const normalizedName = name.toLocaleLowerCase("vi-VN");
  const existing = presets.find(
    (preset) => preset.name.toLocaleLowerCase("vi-VN") === normalizedName,
  );
  let selectedId;
  if (existing) {
    existing.name = name;
    existing.values = captureFilterValues();
    selectedId = existing.id;
  } else {
    if (presets.length >= MAX_SAVED_FILTERS) {
      showSavedFilterMessage(`Chỉ lưu tối đa ${MAX_SAVED_FILTERS} bộ lọc.`, true);
      return;
    }
    selectedId = createPresetId();
    presets.push({ id: selectedId, name, values: captureFilterValues() });
  }

  if (!writeSavedFilters(presets)) return;
  renderSavedFilters(selectedId);
  showSavedFilterMessage(existing ? "Đã cập nhật bộ lọc." : "Đã lưu bộ lọc.");
}

function applySavedFilter() {
  const selectedId = elements.savedFilterSelect.value;
  elements.deleteFilter.disabled = !selectedId;
  showSavedFilterMessage("");
  if (!selectedId) {
    elements.savedFilterName.value = "";
    return;
  }

  const preset = readSavedFilters().find((item) => item.id === selectedId);
  if (!preset) {
    renderSavedFilters();
    return;
  }
  elements.filterForm.reset();
  for (const [key, element] of Object.entries(filterElements)) {
    element.value = typeof preset.values[key] === "string" ? preset.values[key] : "";
  }
  elements.savedFilterSelect.value = selectedId;
  elements.savedFilterName.value = preset.name;
  elements.deleteFilter.disabled = false;
  updateAdvancedLabel();
  const hasAdvancedFilters = advancedFilterCount() > 0;
  elements.advancedFilters.hidden = !hasAdvancedFilters;
  elements.toggleAdvanced.setAttribute("aria-expanded", String(hasAdvancedFilters));
  state.pageNumber = 1;
  resetOrderSelection();
  loadOrders();
}

function deleteSavedFilter() {
  const selectedId = elements.savedFilterSelect.value;
  if (!selectedId) return;
  const preset = readSavedFilters().find((item) => item.id === selectedId);
  if (!preset || !window.confirm(`Xóa bộ lọc “${preset.name}”?`)) return;
  const presets = readSavedFilters().filter((item) => item.id !== selectedId);
  if (!writeSavedFilters(presets)) return;
  renderSavedFilters();
  elements.savedFilterName.value = "";
  showSavedFilterMessage("Đã xóa bộ lọc đã lưu.");
}

async function fetchJson(url) {
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const error = new Error(payload.detail || `Yêu cầu thất bại (${response.status})`);
    error.status = response.status;
    if (response.status === 401) showLogin();
    throw error;
  }
  return response.json();
}

function readCookie(name) {
  const prefix = `${name}=`;
  const entry = document.cookie.split("; ").find((value) => value.startsWith(prefix));
  return entry ? decodeURIComponent(entry.slice(prefix.length)) : "";
}

function secureFetch(url, options = {}) {
  const headers = new Headers(options.headers || {});
  if (state.csrfToken) headers.set("X-CSRF-Token", state.csrfToken);
  return fetch(url, { ...options, headers });
}

function showLogin(message = "") {
  if (state.watermarkTimer !== null) {
    window.clearInterval(state.watermarkTimer);
    state.watermarkTimer = null;
  }
  elements.screenWatermark.replaceChildren();
  if (state.inspectionNoticeTimer !== null) {
    window.clearTimeout(state.inspectionNoticeTimer);
    state.inspectionNoticeTimer = null;
  }
  elements.inspectionNotice.hidden = true;
  if (state.securityAlertTimer !== null) {
    window.clearInterval(state.securityAlertTimer);
    state.securityAlertTimer = null;
  }
  state.currentUser = null;
  state.staffManagement = null;
  state.passwordChangeRequired = false;
  state.csrfToken = "";
  state.currentPageOrders = [];
  state.selectedOrderKeys.clear();
  state.allMatchingSelected = false;
  state.totalMatchingOrders = 0;
  state.appliedExportFilters = {};
  elements.ordersBody.replaceChildren();
  elements.dialogContent.replaceChildren();
  elements.staffList.replaceChildren();
  elements.staffShopOptions.replaceChildren();
  elements.auditBody.replaceChildren();
  elements.auditActionFilter.value = "";
  elements.auditActorFilter.value = "";
  elements.auditResultFilter.value = "";
  elements.auditIpFilter.value = "";
  elements.auditDateFrom.value = "";
  elements.auditDateTo.value = "";
  elements.filterForm.reset();
  for (const summaryElement of [
    elements.totalOrders,
    elements.totalShops,
    elements.totalPages,
    elements.totalStatuses,
    elements.filteredOrders,
    elements.filteredRevenue,
    elements.filteredDelivered,
    elements.filteredFailed,
  ]) {
    summaryElement.textContent = "—";
  }
  elements.resultCount.textContent = "Đang tải…";
  elements.systemStateText.textContent = "Đang kiểm tra dữ liệu…";
  if (elements.orderDialog.open) elements.orderDialog.close();
  if (elements.passwordDialog.open) elements.passwordDialog.close();
  if (elements.auditDialog.open) elements.auditDialog.close();
  if (elements.securityAlertsDialog.open) elements.securityAlertsDialog.close();
  if (elements.helpDialog.open) elements.helpDialog.close();
  elements.passwordForm.reset();
  elements.appShell.hidden = true;
  elements.loginShell.hidden = false;
  elements.loginError.textContent = message;
  elements.loginError.hidden = !message;
  elements.loginPassword.value = "";
  if (elements.staffDialog.open) elements.staffDialog.close();
  elements.loginUsername.focus();
}

function renderScreenWatermark() {
  if (!state.currentUser) return;
  const timestamp = new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date());
  const label = `${text(state.currentUser.display_name, state.currentUser.username)} · @${state.currentUser.username} · ${timestamp}`;
  const marks = Array.from({ length: 30 }, () => {
    const mark = document.createElement("span");
    mark.textContent = label;
    return mark;
  });
  elements.screenWatermark.replaceChildren(...marks);
}

function showInspectionNotice() {
  elements.inspectionNotice.hidden = false;
  if (state.inspectionNoticeTimer !== null) {
    window.clearTimeout(state.inspectionNoticeTimer);
  }
  state.inspectionNoticeTimer = window.setTimeout(() => {
    elements.inspectionNotice.hidden = true;
    state.inspectionNoticeTimer = null;
  }, 2_500);
}

function isBlockedInspectionShortcut(event) {
  const key = event.key.toUpperCase();
  if (key === "F12") return true;
  if (event.ctrlKey && event.shiftKey && ["I", "J", "C"].includes(key)) return true;
  if (event.ctrlKey && key === "U") return true;
  return event.metaKey && event.altKey && ["I", "J", "C", "U"].includes(key);
}

function devtoolsLikelyDocked() {
  const desktopSized = window.outerWidth >= 900 && window.outerHeight >= 600;
  if (!desktopSized) return false;
  const widthGap = Math.max(0, window.outerWidth - window.innerWidth);
  const heightGap = Math.max(0, window.outerHeight - window.innerHeight);
  return widthGap > DEVTOOLS_SIZE_THRESHOLD || heightGap > DEVTOOLS_SIZE_THRESHOLD;
}

function updateDevtoolsPrivacyShield() {
  const active = devtoolsLikelyDocked();
  document.body.classList.toggle("devtools-privacy-active", active);
  elements.devtoolsPrivacyShield.hidden = !active;
}

function accountRoleLabel(user) {
  if (user.is_root_admin) return "Quản trị gốc";
  return user.role === "admin" ? "Quản trị viên" : "Nhân viên";
}

function showApplication(user) {
  state.currentUser = user;
  renderScreenWatermark();
  if (state.watermarkTimer !== null) window.clearInterval(state.watermarkTimer);
  state.watermarkTimer = window.setInterval(renderScreenWatermark, 60_000);
  elements.currentUserName.textContent = text(user.display_name, user.username);
  elements.currentUserRole.textContent = accountRoleLabel(user);
  elements.manageStaffButton.textContent = user.is_root_admin ? "Tài khoản" : "Nhân viên";
  elements.auditDialogTitle.textContent = user.is_root_admin
    ? "Nhật ký hoạt động"
    : "Nhật ký nhân viên";
  elements.securityAlertsDialogTitle.textContent = user.is_root_admin
    ? "Cảnh báo lấy dữ liệu hàng loạt"
    : "Cảnh báo nhân viên lấy dữ liệu hàng loạt";
  elements.manageStaffButton.hidden = user.role !== "admin";
  elements.auditLogButton.hidden = user.role !== "admin";
  elements.securityAlertsButton.hidden = user.role !== "admin";
  if (state.securityAlertTimer !== null) window.clearInterval(state.securityAlertTimer);
  state.securityAlertTimer = null;
  if (user.role === "admin") {
    loadSecurityAlerts(false).catch(() => {});
    state.securityAlertTimer = window.setInterval(() => {
      if (!document.hidden) loadSecurityAlerts(false).catch(() => {});
    }, 60_000);
  }
  elements.exportExcel.title =
    user.role === "admin"
      ? "Xuất các đơn đang khớp bộ lọc"
      : "Nhân viên: tối đa 500 đơn/file, 5 lần/giờ và 2.000 đơn/24 giờ";
  elements.syncNow.hidden = !user.can_sync;
  elements.revenueSummaryCard.hidden = !user.can_view_revenue;
  elements.loginShell.hidden = true;
  elements.appShell.hidden = false;
}

async function login(event) {
  event.preventDefault();
  elements.loginError.hidden = true;
  elements.loginButton.disabled = true;
  elements.loginButton.textContent = "Đang đăng nhập…";
  try {
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        username: elements.loginUsername.value,
        password: elements.loginPassword.value,
      }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || "Không thể đăng nhập.");
    state.csrfToken = readCookie("hongha_csrf");
    showApplication(payload.user);
    elements.loginPassword.value = "";
    if (payload.user.must_change_password) {
      openPasswordChange(true);
      return;
    }
    await loadApplicationData();
  } catch (error) {
    showLogin(error.message);
  } finally {
    elements.loginButton.disabled = false;
    elements.loginButton.textContent = "Đăng nhập";
  }
}

async function logout() {
  elements.logoutButton.disabled = true;
  try {
    await secureFetch("/api/auth/logout", {
      method: "POST",
      headers: { Accept: "application/json" },
    });
  } finally {
    elements.logoutButton.disabled = false;
    showLogin();
  }
}

async function loadApplicationData() {
  renderSavedFilters();
  await Promise.all([loadFilters(), loadSystemStatus(), loadOrders()]);
}

function setPasswordMessage(message, isError = false) {
  elements.passwordFormMessage.textContent = message;
  elements.passwordFormMessage.classList.toggle("is-error", isError);
}

function openPasswordChange(required = false) {
  state.passwordChangeRequired = required;
  elements.passwordForm.reset();
  setPasswordMessage("");
  elements.passwordRequiredNotice.hidden = !required;
  elements.closePasswordDialog.hidden = required;
  elements.cancelPasswordChange.hidden = required;
  elements.passwordDialog.showModal();
  elements.currentPassword.focus();
}

function closePasswordChange() {
  if (state.passwordChangeRequired) return;
  elements.passwordForm.reset();
  setPasswordMessage("");
  elements.passwordDialog.close();
}

async function saveOwnPassword(event) {
  event.preventDefault();
  setPasswordMessage("");
  if (elements.newPassword.value !== elements.confirmNewPassword.value) {
    setPasswordMessage("Hai lần nhập mật khẩu mới không khớp.", true);
    elements.confirmNewPassword.focus();
    return;
  }

  const wasRequired = state.passwordChangeRequired;
  elements.savePasswordButton.disabled = true;
  elements.savePasswordButton.textContent = "Đang đổi…";
  try {
    const response = await secureFetch("/api/auth/change-password", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        current_password: elements.currentPassword.value,
        new_password: elements.newPassword.value,
      }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      if (response.status === 401) showLogin();
      throw new Error(payload.detail || `Yêu cầu thất bại (${response.status})`);
    }

    state.currentUser.must_change_password = false;
    state.passwordChangeRequired = false;
    elements.passwordForm.reset();
    elements.passwordDialog.close();
    if (wasRequired) await loadApplicationData();
  } catch (error) {
    setPasswordMessage(error.message, true);
  } finally {
    elements.savePasswordButton.disabled = false;
    elements.savePasswordButton.textContent = "Đổi mật khẩu";
  }
}

function selectedStaffShopIds() {
  return Array.from(
    elements.staffShopOptions.querySelectorAll('input[type="checkbox"]:checked'),
    (input) => input.value,
  );
}

function setStaffFormMessage(message, isError = false) {
  elements.staffFormMessage.textContent = message;
  elements.staffFormMessage.classList.toggle("is-error", isError);
}

function hideTemporaryCredential() {
  elements.temporaryCredential.hidden = true;
  elements.temporaryUsername.textContent = "";
  elements.temporaryPassword.textContent = "";
}

function showTemporaryCredential(username, password) {
  elements.temporaryUsername.textContent = username;
  elements.temporaryPassword.textContent = password;
  elements.temporaryCredential.hidden = false;
}

function renderStaffShopOptions(selectedShopIds = []) {
  const selected = new Set(selectedShopIds);
  const options = (state.staffManagement?.shops || []).map((shop) => {
    const label = createElement("label", "staff-shop-option");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.value = shop.shop_id;
    checkbox.checked = selected.has(shop.shop_id);
    label.append(checkbox, createElement("span", "", shop.shop_name));
    return label;
  });
  elements.staffShopOptions.replaceChildren(...options);
}

function updateAccountRoleFields() {
  const isAdminAccount = elements.staffRole.value === "admin";
  elements.staffShopSelector.hidden = isAdminAccount;
  if (isAdminAccount) {
    for (const input of elements.staffShopOptions.querySelectorAll('input[type="checkbox"]')) {
      input.checked = false;
    }
  }
}

function resetStaffForm() {
  elements.staffForm.reset();
  elements.staffUserId.value = "";
  elements.staffUsername.disabled = false;
  elements.staffUsername.required = true;
  elements.staffRole.value = "staff";
  elements.staffRole.disabled = false;
  elements.staffRoleField.hidden = !state.currentUser?.is_root_admin;
  elements.staffResetPassword.checked = false;
  elements.staffResetPasswordField.hidden = true;
  elements.staffActiveField.hidden = true;
  elements.staffFormTitle.textContent = "Thêm tài khoản";
  elements.saveStaffButton.textContent = "Tạo tài khoản";
  elements.cancelStaffEdit.hidden = true;
  setStaffFormMessage("");
  hideTemporaryCredential();
  renderStaffShopOptions();
  updateAccountRoleFields();
}

function beginStaffEdit(user) {
  elements.staffUserId.value = user.id;
  elements.staffDisplayName.value = user.display_name;
  elements.staffUsername.value = user.username;
  elements.staffUsername.disabled = true;
  elements.staffUsername.required = false;
  elements.staffRole.value = user.role;
  elements.staffRole.disabled = true;
  elements.staffRoleField.hidden = !state.currentUser?.is_root_admin;
  elements.staffResetPassword.checked = false;
  elements.staffResetPasswordField.hidden = false;
  elements.staffIsActive.checked = user.is_active;
  elements.staffActiveField.hidden = false;
  elements.staffFormTitle.textContent = `Sửa: ${user.display_name}`;
  elements.saveStaffButton.textContent = "Lưu thay đổi";
  elements.cancelStaffEdit.hidden = false;
  setStaffFormMessage("");
  hideTemporaryCredential();
  renderStaffShopOptions(user.shop_ids);
  updateAccountRoleFields();
  elements.staffDisplayName.focus();
}

async function deleteStaff(user, button) {
  const roleLabel = accountRoleLabel(user);
  const confirmed = window.confirm(
    `Xóa ${roleLabel.toLowerCase()} "${user.display_name}" (@${user.username})?\n\n` +
      "Tài khoản sẽ bị đăng xuất, mất toàn bộ quyền shop và không thể đăng nhập lại.",
  );
  if (!confirmed) return;

  button.disabled = true;
  button.textContent = "Đang xóa…";
  setStaffFormMessage("");
  try {
    const response = await secureFetch(
      `/api/admin/users/${encodeURIComponent(user.id)}`,
      { method: "DELETE", headers: { Accept: "application/json" } },
    );
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      if (response.status === 401) showLogin();
      throw new Error(result.detail || `Yêu cầu thất bại (${response.status})`);
    }
    if (elements.staffUserId.value === user.id) resetStaffForm();
    await loadStaffManagement();
    setStaffFormMessage(`Đã xóa @${user.username} và thu hồi mọi phiên đăng nhập.`);
  } catch (error) {
    setStaffFormMessage(`Không thể xóa tài khoản. ${error.message}`, true);
    button.disabled = false;
    button.textContent = "Xóa";
  }
}

function renderStaffList() {
  const users = state.staffManagement?.users || [];
  const shopNames = new Map(
    (state.staffManagement?.shops || []).map((shop) => [shop.shop_id, shop.shop_name]),
  );
  elements.staffCount.textContent = `${integerFormatter.format(users.length)} tài khoản`;
  if (users.length === 0) {
    elements.staffList.replaceChildren(
      createElement("p", "staff-list-empty", "Chưa có tài khoản phù hợp."),
    );
    return;
  }

  const cards = users.map((user) => {
    const card = createElement("article", "staff-card");
    const header = createElement("div", "staff-card-header");
    const identity = createElement("div", "staff-card-identity");
    identity.append(
      createElement("strong", "", user.display_name),
      createElement("span", "", `@${user.username}`),
      createElement(
        "span",
        `staff-role-badge${user.is_root_admin ? " is-root" : ""}`,
        accountRoleLabel(user),
      ),
    );
    const statusText = user.is_active
      ? user.must_change_password
        ? "Chờ đổi mật khẩu"
        : "Đang hoạt động"
      : "Đã khóa";
    const statusClass = user.is_active
      ? user.must_change_password
        ? "is-pending"
        : "is-active"
      : "is-locked";
    header.append(
      identity,
      createElement(
        "span",
        `staff-account-status ${statusClass}`,
        statusText,
      ),
    );

    const assignedShops = user.shop_ids.map((shopId) => shopNames.get(shopId) || shopId);
    const shops = createElement(
      "p",
      "staff-card-shops",
      user.role === "admin"
        ? "Toàn quyền cửa hàng và dữ liệu"
        : assignedShops.length
          ? assignedShops.join(" · ")
          : "Chưa được cấp shop",
    );
    const footer = createElement("div", "staff-card-footer");
    footer.append(
      createElement(
        "span",
        "",
        [
          user.created_at ? `Tạo ${formatDate(user.created_at)}` : "",
          user.last_login_at ? `Đăng nhập gần nhất ${formatDate(user.last_login_at)}` : "Chưa đăng nhập",
        ]
          .filter(Boolean)
          .join(" · "),
      ),
    );
    if (user.can_manage) {
      const editButton = createElement("button", "secondary-button", "Sửa quyền");
      editButton.type = "button";
      editButton.addEventListener("click", () => beginStaffEdit(user));
      const deleteButton = createElement("button", "delete-staff-button", "Xóa");
      deleteButton.type = "button";
      deleteButton.addEventListener("click", () => deleteStaff(user, deleteButton));
      const actions = createElement("div", "staff-card-actions");
      actions.append(editButton, deleteButton);
      footer.append(actions);
    } else if (user.is_root_admin) {
      footer.append(createElement("span", "", "Tài khoản gốc được bảo vệ"));
    }
    card.append(header, shops, footer);
    return card;
  });
  elements.staffList.replaceChildren(...cards);
}

async function loadStaffManagement() {
  elements.staffList.replaceChildren(
    createElement("p", "staff-list-empty", "Đang tải tài khoản…"),
  );
  state.staffManagement = await fetchJson("/api/admin/users");
  const rootView = state.staffManagement.viewer_is_root_admin;
  elements.staffDialogTitle.textContent = rootView
    ? "Quản lý quản trị viên và nhân viên"
    : "Quản lý nhân viên";
  elements.staffListTitle.textContent = rootView
    ? "Danh sách tài khoản"
    : "Danh sách nhân viên";
  renderStaffList();
  resetStaffForm();
}

async function openStaffManagement() {
  elements.staffDialog.showModal();
  try {
    await loadStaffManagement();
  } catch (error) {
    elements.staffList.replaceChildren(
      createElement("p", "staff-list-empty is-error", `Không thể tải. ${error.message}`),
    );
  }
}

async function saveStaff(event) {
  event.preventDefault();
  setStaffFormMessage("");
  const userId = elements.staffUserId.value;
  const isEditing = Boolean(userId);
  const payload = {
    display_name: elements.staffDisplayName.value,
    shop_ids: selectedStaffShopIds(),
  };
  if (isEditing) {
    payload.is_active = elements.staffIsActive.checked;
    payload.reset_password = elements.staffResetPassword.checked;
  } else {
    payload.username = elements.staffUsername.value;
    payload.role = elements.staffRole.value;
  }

  elements.saveStaffButton.disabled = true;
  elements.saveStaffButton.textContent = "Đang lưu…";
  try {
    const response = await secureFetch(
      isEditing ? `/api/admin/users/${encodeURIComponent(userId)}` : "/api/admin/users",
      {
        method: isEditing ? "PUT" : "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(payload),
      },
    );
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      if (response.status === 401) showLogin();
      throw new Error(result.detail || `Yêu cầu thất bại (${response.status})`);
    }
    await loadStaffManagement();
    if (result.temporary_password) {
      showTemporaryCredential(result.username, result.temporary_password);
      setStaffFormMessage(
        isEditing
          ? "Đã đặt lại mật khẩu và đăng xuất các phiên cũ."
          : "Đã tạo tài khoản. Hãy sao chép thông tin đăng nhập bên dưới.",
      );
    } else {
      setStaffFormMessage(isEditing ? "Đã cập nhật tài khoản." : "Đã tạo tài khoản.");
    }
  } catch (error) {
    setStaffFormMessage(error.message, true);
  } finally {
    elements.saveStaffButton.disabled = false;
    elements.saveStaffButton.textContent = elements.staffUserId.value
      ? "Lưu thay đổi"
      : "Tạo tài khoản";
  }
}

async function copyTemporaryCredential() {
  const username = elements.temporaryUsername.textContent;
  const password = elements.temporaryPassword.textContent;
  if (!username || !password) return;
  try {
    await navigator.clipboard.writeText(`Tài khoản: ${username}\nMật khẩu tạm: ${password}`);
    elements.copyTemporaryCredential.textContent = "Đã sao chép";
    window.setTimeout(() => {
      elements.copyTemporaryCredential.textContent = "Sao chép tài khoản và mật khẩu";
    }, 1800);
  } catch {
    setStaffFormMessage("Không thể tự sao chép. Hãy bôi đen thông tin và sao chép thủ công.", true);
  }
}

function auditDetail(item) {
  const metadata = item.metadata || {};
  if (item.action === "orders.export") {
    return `${integerFormatter.format(metadata.order_count || 0)} đơn`;
  }
  if (item.action === "orders.sync") {
    if (item.result === "skipped") return "Đã có lượt đồng bộ khác đang chạy";
    return [
      metadata.shops_processed !== undefined
        ? `${integerFormatter.format(metadata.shops_processed)} shop`
        : "",
      metadata.rows_written !== undefined
        ? `${integerFormatter.format(metadata.rows_written)} dòng cập nhật`
        : "",
      metadata.connectors_failed
        ? `${integerFormatter.format(metadata.connectors_failed)} kết nối lỗi`
        : "",
    ]
      .filter(Boolean)
      .join(" · ");
  }
  if (["staff.create", "staff.update", "admin.create", "admin.update"].includes(item.action)) {
    const parts = [];
    if (metadata.shop_count !== undefined) {
      parts.push(`${integerFormatter.format(metadata.shop_count)} shop`);
    }
    if (metadata.password_changed) parts.push("Có đổi mật khẩu");
    if (metadata.active === false) parts.push("Đã khóa tài khoản");
    return parts.join(" · ") || "—";
  }
  if (["staff.delete", "admin.delete"].includes(item.action)) {
    return metadata.username
      ? `@${metadata.username} · Đã thu hồi quyền và phiên đăng nhập`
      : "Đã thu hồi tài khoản";
  }
  if (item.action === "auth.login" && item.result === "denied") {
    return metadata.username ? `Tài khoản: ${metadata.username}` : "Sai thông tin đăng nhập";
  }
  if (item.action === "security.rate_limit") {
    return `Đã dùng ${integerFormatter.format(metadata.used || 0)} / ${integerFormatter.format(metadata.limit || 0)} · ${metadata.quota || "Hạn mức bảo vệ"}`;
  }
  if (item.action === "security.high_usage") {
    return `${integerFormatter.format(metadata.percent || 0)}% hạn mức · ${integerFormatter.format(metadata.used || 0)} / ${integerFormatter.format(metadata.limit || 0)} · ${metadata.quota || "Hạn mức bảo vệ"}`;
  }
  if (item.action === "orders.view_detail.daily") {
    return `${integerFormatter.format(metadata.event_count || 0)} lượt mở · ${integerFormatter.format(metadata.unique_order_count || 0)} đơn trong ngày`;
  }
  return item.resource_id ? `${text(item.resource_type, "Đối tượng")}: ${item.resource_id}` : "—";
}

function auditResultLabel(result) {
  return {
    success: "Thành công",
    denied: "Từ chối",
    skipped: "Bỏ qua",
    partial: "Có lỗi một phần",
    warning: "Cảnh báo",
  }[result] || text(result);
}

function auditDevice(userAgent) {
  if (!userAgent) return "Không xác định";
  const browser = userAgent.includes("Edg/")
    ? "Edge"
    : userAgent.includes("Firefox/")
      ? "Firefox"
      : userAgent.includes("Chrome/")
        ? "Chrome"
        : userAgent.includes("Safari/")
          ? "Safari"
          : "Trình duyệt khác";
  const platform = userAgent.includes("Windows")
    ? "Windows"
    : userAgent.includes("Android")
      ? "Android"
      : userAgent.includes("iPhone") || userAgent.includes("iPad")
        ? "iPhone/iPad"
        : userAgent.includes("Mac OS")
          ? "macOS"
          : "Thiết bị khác";
  return `${browser} · ${platform}`;
}

function renderAuditLog(data) {
  const rows = data.items.map((item) => {
    const row = document.createElement("tr");
    const actor = item.actor_display_name || item.actor_username || "Hệ thống / không xác định";
    const actorCell = document.createElement("td");
    actorCell.append(
      createElement("strong", "", actor),
      createElement("span", "secondary-text", item.actor_username ? `@${item.actor_username}` : ""),
    );
    const originCell = createElement("td", "audit-origin");
    const device = createElement("span", "", auditDevice(item.user_agent));
    device.title = item.user_agent || "";
    originCell.append(
      createElement("strong", "", item.ip_address || "Không xác định"),
      device,
    );
    row.append(
      createElement("td", "", formatDate(item.created_at)),
      actorCell,
      createElement("td", "", AUDIT_ACTION_LABELS[item.action] || item.action),
      createElement(
        "td",
        `audit-result audit-result-${item.result}`,
        auditResultLabel(item.result),
      ),
      originCell,
      createElement("td", "audit-detail", auditDetail(item)),
    );
    return row;
  });
  elements.auditBody.replaceChildren(...rows);
  elements.auditEmpty.hidden = rows.length !== 0;

  const selectedAction = elements.auditActionFilter.value;
  const selectedActor = elements.auditActorFilter.value;
  const selectedResult = elements.auditResultFilter.value;
  const actionOptions = [createElement("option", "", "Tất cả hoạt động")];
  actionOptions[0].value = "";
  for (const action of data.actions) {
    const option = createElement("option", "", AUDIT_ACTION_LABELS[action] || action);
    option.value = action;
    actionOptions.push(option);
  }
  elements.auditActionFilter.replaceChildren(...actionOptions);
  elements.auditActionFilter.value = selectedAction;

  const actorOptions = [
    createElement(
      "option",
      "",
      state.currentUser?.is_root_admin ? "Tất cả tài khoản" : "Tất cả nhân viên",
    ),
  ];
  actorOptions[0].value = "";
  for (const actor of data.actors) {
    const label = `${actor.display_name || actor.username} · @${actor.username}`;
    const option = createElement("option", "", label);
    option.value = actor.user_id;
    actorOptions.push(option);
  }
  elements.auditActorFilter.replaceChildren(...actorOptions);
  elements.auditActorFilter.value = selectedActor;

  const resultOptions = [createElement("option", "", "Tất cả kết quả")];
  resultOptions[0].value = "";
  for (const result of data.results) {
    const option = createElement("option", "", auditResultLabel(result));
    option.value = result;
    resultOptions.push(option);
  }
  elements.auditResultFilter.replaceChildren(...resultOptions);
  elements.auditResultFilter.value = selectedResult;

  const pagination = data.pagination;
  state.auditPageNumber = pagination.page_number;
  state.auditTotalPages = Math.max(pagination.total_pages, 1);
  elements.auditPageIndicator.textContent = `Trang ${state.auditPageNumber} / ${state.auditTotalPages}`;
  elements.previousAuditPage.disabled = state.auditPageNumber <= 1;
  elements.nextAuditPage.disabled = state.auditPageNumber >= state.auditTotalPages;
}

async function loadAuditLog() {
  elements.auditError.textContent = "";
  if (
    elements.auditDateFrom.value &&
    elements.auditDateTo.value &&
    elements.auditDateFrom.value > elements.auditDateTo.value
  ) {
    elements.auditError.textContent = "Thời điểm bắt đầu phải trước thời điểm kết thúc.";
    return;
  }
  const params = new URLSearchParams({
    page_number: String(state.auditPageNumber),
    page_size: "50",
  });
  if (elements.auditActionFilter.value) {
    params.set("action", elements.auditActionFilter.value);
  }
  if (elements.auditActorFilter.value) {
    params.set("actor_user_id", elements.auditActorFilter.value);
  }
  if (elements.auditResultFilter.value) {
    params.set("result", elements.auditResultFilter.value);
  }
  if (elements.auditIpFilter.value.trim()) {
    params.set("ip_address", elements.auditIpFilter.value.trim());
  }
  if (elements.auditDateFrom.value) {
    params.set("date_from", new Date(elements.auditDateFrom.value).toISOString());
  }
  if (elements.auditDateTo.value) {
    params.set("date_to", new Date(elements.auditDateTo.value).toISOString());
  }
  try {
    renderAuditLog(await fetchJson(`/api/admin/audit-logs?${params.toString()}`));
  } catch (error) {
    elements.auditError.textContent = `Không thể tải nhật ký. ${error.message}`;
  }
}

async function openAuditLog() {
  state.auditPageNumber = 1;
  elements.auditDialog.showModal();
  await loadAuditLog();
}

function resetAuditFilters() {
  elements.auditActionFilter.value = "";
  elements.auditActorFilter.value = "";
  elements.auditResultFilter.value = "";
  elements.auditIpFilter.value = "";
  elements.auditDateFrom.value = "";
  elements.auditDateTo.value = "";
  state.auditPageNumber = 1;
  loadAuditLog();
}

function securityQuotaLabel(value) {
  return {
    "orders.list.rows.burst": "Xem nhanh danh sách trong 5 phút",
    "orders.list.rows": "Xem danh sách trong 1 giờ",
    "orders.view_detail.burst": "Mở chi tiết trong 5 phút",
    "orders.view_detail": "Mở chi tiết trong 1 giờ",
    "orders.export.requests": "Số lượt xuất Excel trong 1 giờ",
    "orders.export.rows": "Số đơn xuất Excel trong 24 giờ",
  }[value] || text(value, "Hạn mức bảo vệ");
}

function renderSecurityAlerts(data) {
  const cards = data.items.map((item) => {
    const metadata = item.metadata || {};
    const card = createElement(
      "article",
      `security-alert-card ${item.action === "security.rate_limit" ? "is-blocked" : "is-warning"}`,
    );
    const actor = item.actor_display_name || item.actor_username || "Tài khoản không xác định";
    const status = item.action === "security.rate_limit" ? "ĐÃ CHẶN" : "CẢNH BÁO";
    const heading = createElement("div", "security-alert-card-heading");
    heading.append(
      createElement("strong", "", actor),
      createElement("span", "security-alert-status", status),
    );
    const identity = item.actor_username ? `@${item.actor_username}` : "Không có username";
    const usage = `${integerFormatter.format(metadata.used || 0)} / ${integerFormatter.format(metadata.limit || 0)}`;
    card.append(
      heading,
      createElement("span", "security-alert-identity", `${identity} · ${formatDate(item.created_at)}`),
      createElement("p", "", `${securityQuotaLabel(metadata.quota)}: ${usage}`),
      createElement("span", "security-alert-origin", `${item.ip_address || "IP không xác định"} · ${auditDevice(item.user_agent)}`),
    );
    return card;
  });
  elements.securityAlertsList.replaceChildren(...cards);
  elements.securityAlertsEmpty.hidden = cards.length !== 0;
  const count = Number(data.total || 0);
  elements.securityAlertCount.textContent = count > 99 ? "99+" : String(count);
  elements.securityAlertCount.hidden = count === 0;
  elements.securityAlertsButton.classList.toggle("has-alerts", count > 0);
}

async function loadSecurityAlerts(renderList = true) {
  if (state.currentUser?.role !== "admin") return;
  if (renderList) elements.securityAlertsError.textContent = "";
  try {
    const data = await fetchJson("/api/admin/security-alerts?hours=24&limit=50");
    renderSecurityAlerts(data);
  } catch (error) {
    if (renderList) {
      elements.securityAlertsError.textContent = `Không thể tải cảnh báo. ${error.message}`;
    }
    throw error;
  }
}

async function openSecurityAlerts() {
  elements.securityAlertsDialog.showModal();
  await loadSecurityAlerts(true).catch(() => {});
}

function addOption(select, value, label) {
  const option = document.createElement("option");
  option.value = String(value);
  option.textContent = label;
  select.append(option);
}

function resetSelect(select, label) {
  const option = createElement("option", "", label);
  option.value = "";
  select.replaceChildren(option);
}

async function loadFilters() {
  const data = await fetchJson("/api/order-filters");
  resetSelect(elements.shopFilter, "Tất cả cửa hàng");
  resetSelect(elements.pageFilter, "Tất cả page");
  resetSelect(elements.statusFilter, "Tất cả tình trạng đơn");
  resetSelect(elements.carrierFilter, "Tất cả đơn vị");
  resetSelect(elements.deliveryStatusFilter, "Tất cả trạng thái");
  elements.totalOrders.textContent = integerFormatter.format(data.total_orders);
  elements.totalShops.textContent = integerFormatter.format(data.shops.length);
  elements.totalPages.textContent = integerFormatter.format(data.pages.length);
  elements.totalStatuses.textContent = integerFormatter.format(data.business_statuses.length);

  for (const shop of data.shops) {
    addOption(
      elements.shopFilter,
      shop.shop_id,
      `${text(shop.shop_name, shop.shop_id)} · ${integerFormatter.format(shop.order_count)}`,
    );
  }
  for (const page of data.pages) {
    addOption(
      elements.pageFilter,
      page.page_id,
      `${text(page.page_name, "Không tên")} · ${integerFormatter.format(page.order_count)}`,
    );
  }
  for (const status of data.business_statuses) {
    addOption(
      elements.statusFilter,
      status.business_status,
      `${status.business_status_label} · ${integerFormatter.format(status.order_count)}`,
    );
  }
  for (const carrier of data.carriers) {
    addOption(
      elements.carrierFilter,
      carrier.carrier_name,
      `${carrier.carrier_name} · ${integerFormatter.format(carrier.order_count)}`,
    );
  }
  for (const status of data.delivery_statuses) {
    addOption(
      elements.deliveryStatusFilter,
      status.delivery_status,
      `${status.delivery_status_label || "Chưa xác định"} · ${integerFormatter.format(status.order_count)}`,
    );
  }
}

async function loadSystemStatus() {
  const data = await fetchJson("/api/system-status");
  elements.totalOrders.textContent = integerFormatter.format(data.core_orders);
  elements.totalShops.textContent = integerFormatter.format(data.shops);
  const latest = data.latest_sync;
  if (!latest) {
    elements.systemStateText.textContent = "Chưa có lần đồng bộ";
    return;
  }
  if (latest.status === "running") {
    elements.systemStateText.textContent = "Đang đồng bộ…";
    return;
  }
  if (latest.status !== "success") {
    elements.systemStateText.textContent = "Cần kiểm tra đồng bộ";
    return;
  }
  elements.systemStateText.textContent = `Đồng bộ ${formatDate(latest.finished_at)}`;
}

async function waitForManualSync() {
  const deadline = Date.now() + 30 * 60 * 1000;
  while (Date.now() < deadline) {
    await new Promise((resolve) => window.setTimeout(resolve, 5000));
    const status = await fetchJson("/api/sync/status");
    if (status.status !== "running") {
      return status;
    }
  }
  return {
    status: "failed",
    detail: "Đồng bộ vẫn đang chạy lâu hơn dự kiến. Hãy kiểm tra lại sau.",
  };
}

async function syncNow() {
  clearError();
  elements.syncNow.disabled = true;
  elements.syncNow.textContent = "Đang đồng bộ…";
  elements.systemStateText.textContent = "Đang lấy đơn mới…";
  try {
    const response = await secureFetch("/api/sync", {
      method: "POST",
      headers: { Accept: "application/json" },
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || `Yêu cầu thất bại (${response.status})`);
    }
    if (payload.status !== "started") {
      throw new Error("Server không xác nhận tác vụ đồng bộ.");
    }
    elements.syncNow.textContent = "Đang đồng bộ nền…";
    const result = await waitForManualSync();
    if (result.status === "skipped") {
      elements.systemStateText.textContent = "Đang có lượt đồng bộ khác";
      elements.syncNow.textContent = "Đồng bộ đang chạy";
      return;
    }
    if (result.status !== "completed") {
      throw new Error(result.detail || "Đồng bộ nền gặp lỗi.");
    }
    await Promise.all([loadSystemStatus(), loadOrders()]);
    const shopCount = integerFormatter.format(result.shops_processed);
    const orderCount = integerFormatter.format(result.orders_transformed);
    if (result.success) {
      elements.syncNow.textContent = `Xong · ${shopCount} shop, ${orderCount} đơn cập nhật`;
    } else {
      showError(
        `Đã đồng bộ nhưng có ${integerFormatter.format(result.connectors_failed)} kết nối lỗi.`,
      );
      elements.syncNow.textContent = "Hoàn tất, có lỗi";
    }
  } catch (error) {
    showError(`Không thể đồng bộ. ${error.message}`);
    elements.systemStateText.textContent = "Đồng bộ chưa hoàn tất";
    elements.syncNow.textContent = "Thử đồng bộ lại";
  } finally {
    elements.syncNow.disabled = false;
  }
}

function orderSelectionKey(order) {
  return JSON.stringify([String(order.shop_id), String(order.order_id)]);
}

function resetOrderSelection() {
  state.selectedOrderKeys.clear();
  state.allMatchingSelected = false;
  renderOrderSelection();
}

function renderOrderSelection() {
  const checkboxes = elements.ordersBody.querySelectorAll(".order-select-checkbox");
  for (const checkbox of checkboxes) {
    checkbox.checked =
      state.allMatchingSelected || state.selectedOrderKeys.has(checkbox.dataset.orderKey);
    checkbox.disabled = state.allMatchingSelected;
  }

  const pageKeys = state.currentPageOrders.map(orderSelectionKey);
  const selectedOnPage = state.allMatchingSelected
    ? pageKeys.length
    : pageKeys.filter((key) => state.selectedOrderKeys.has(key)).length;
  elements.selectCurrentPage.checked = pageKeys.length > 0 && selectedOnPage === pageKeys.length;
  elements.selectCurrentPage.indeterminate = selectedOnPage > 0 && selectedOnPage < pageKeys.length;
  elements.selectCurrentPage.disabled = state.allMatchingSelected || pageKeys.length === 0;

  const selectedCount = state.allMatchingSelected
    ? state.totalMatchingOrders
    : state.selectedOrderKeys.size;
  elements.selectionSummary.textContent = state.allMatchingSelected
    ? `Đã chọn tất cả ${integerFormatter.format(selectedCount)} đơn đang lọc`
    : selectedCount
      ? `Đã chọn ${integerFormatter.format(selectedCount)} đơn`
      : "Chưa chọn đơn nào";
  elements.clearOrderSelection.disabled = selectedCount === 0;
  elements.selectAllFiltered.disabled = state.allMatchingSelected || state.totalMatchingOrders === 0;
  elements.selectAllFiltered.textContent = state.allMatchingSelected
    ? "Đã chọn toàn bộ kết quả"
    : `Chọn tất cả ${integerFormatter.format(state.totalMatchingOrders)} kết quả`;
  elements.exportExcel.disabled = selectedCount === 0;
}

function orderRow(order, sameCustomer = false) {
  const row = document.createElement("tr");
  if (sameCustomer) row.classList.add("customer-group-continuation");

  const selectionCell = createElement("td", "select-column");
  const selectionCheckbox = document.createElement("input");
  const selectionKey = orderSelectionKey(order);
  selectionCheckbox.type = "checkbox";
  selectionCheckbox.className = "order-select-checkbox";
  selectionCheckbox.dataset.orderKey = selectionKey;
  selectionCheckbox.setAttribute("aria-label", `Chọn đơn ${order.order_id}`);
  selectionCheckbox.addEventListener("change", () => {
    if (selectionCheckbox.checked) state.selectedOrderKeys.add(selectionKey);
    else state.selectedOrderKeys.delete(selectionKey);
    renderOrderSelection();
  });
  selectionCell.append(selectionCheckbox);

  const orderCell = document.createElement("td");
  orderCell.append(
    createElement("span", "order-code", order.order_id),
    createElement("span", "secondary-text", formatDate(order.inserted_at)),
  );

  const shopCell = document.createElement("td");
  shopCell.append(
    createElement("strong", "", order.shop_name),
    createElement("span", "secondary-text", `Shop ID ${order.shop_id}`),
  );

  const customerCell = document.createElement("td");
  customerCell.append(
    createElement("strong", "", order.customer_name),
    createElement("span", "secondary-text", order.customer_phone),
  );
  if (sameCustomer) {
    customerCell.append(createElement("span", "customer-group-note", "Trùng tên / SĐT"));
  }

  const pageCell = document.createElement("td");
  pageCell.append(
    createElement("span", "", order.page_name),
    createElement("span", "secondary-text", order.page_id),
  );

  const statusCell = document.createElement("td");
  statusCell.append(
    createElement("span", "status-pill", order.business_status_label),
    createElement(
      "span",
      "secondary-text",
      [order.status_name, order.carrier_name, order.delivery_status_label]
        .filter(Boolean)
        .join(" · "),
    ),
  );

  const totalCell = createElement("td", "money", formatMoney(order.total_price, order.currency));
  const updatedCell = createElement("td", "", formatDate(order.updated_at));

  const actionCell = document.createElement("td");
  const viewButton = createElement("button", "view-button", "Xem");
  viewButton.type = "button";
  viewButton.addEventListener("click", () => openOrder(order.order_id, order.shop_id));
  actionCell.append(viewButton);

  row.append(
    selectionCell,
    orderCell,
    shopCell,
    customerCell,
    pageCell,
    statusCell,
    totalCell,
    updatedCell,
    actionCell,
  );
  return row;
}

function renderOrders(data) {
  let previousCustomerGroup = null;
  const rows = data.items.map((order) => {
    const sameCustomer =
      elements.sortFilter.value === "customer" &&
      previousCustomerGroup === order.customer_group_token;
    previousCustomerGroup = order.customer_group_token;
    return orderRow(order, sameCustomer);
  });
  elements.ordersBody.replaceChildren(...rows);
  state.currentPageOrders = data.items;
  elements.emptyState.hidden = data.items.length !== 0;

  const pagination = data.pagination;
  state.pageNumber = pagination.page_number;
  state.totalPages = Math.max(pagination.total_pages, 1);
  state.totalMatchingOrders = pagination.total_items;
  elements.resultCount.textContent = `${integerFormatter.format(pagination.total_items)} kết quả`;
  renderPagination();
  renderOrderSelection();
}

function paginationTokens(currentPage, totalPages) {
  const pages = new Set([1, totalPages]);
  for (let page = currentPage - 2; page <= currentPage + 2; page += 1) {
    if (page >= 1 && page <= totalPages) pages.add(page);
  }
  const sorted = Array.from(pages).sort((left, right) => left - right);
  const tokens = [];
  for (const page of sorted) {
    const previous = tokens[tokens.length - 1];
    if (typeof previous === "number" && page - previous > 1) tokens.push("ellipsis");
    tokens.push(page);
  }
  return tokens;
}

function goToPage(pageNumber) {
  const target = Math.min(Math.max(Math.trunc(Number(pageNumber)), 1), state.totalPages);
  if (!Number.isFinite(target)) return;
  clearError();
  if (target === state.pageNumber) {
    elements.pageJumpInput.value = String(target);
    return;
  }
  state.pageNumber = target;
  loadOrders();
}

function renderPagination() {
  const tokens = paginationTokens(state.pageNumber, state.totalPages);
  const controls = tokens.map((token) => {
    if (token === "ellipsis") {
      return createElement("span", "page-ellipsis", "…");
    }
    const button = createElement("button", "page-number", integerFormatter.format(token));
    button.type = "button";
    button.setAttribute("aria-label", `Trang ${token}`);
    if (token === state.pageNumber) {
      button.classList.add("is-current");
      button.setAttribute("aria-current", "page");
      button.disabled = true;
    }
    button.addEventListener("click", () => goToPage(token));
    return button;
  });
  elements.pageButtons.replaceChildren(...controls);
  elements.pageIndicator.textContent = `Trang ${integerFormatter.format(state.pageNumber)} / ${integerFormatter.format(state.totalPages)}`;
  elements.pageJumpInput.max = String(state.totalPages);
  elements.pageJumpInput.value = String(state.pageNumber);
  const atFirstPage = state.pageNumber <= 1;
  const atLastPage = state.pageNumber >= state.totalPages;
  elements.firstPage.disabled = atFirstPage;
  elements.previousPage.disabled = atFirstPage;
  elements.nextPage.disabled = atLastPage;
  elements.lastPage.disabled = atLastPage;
}

function renderOrderSummary(summary) {
  elements.filteredOrders.textContent = integerFormatter.format(summary.total_orders);
  if (state.currentUser?.can_view_revenue) {
    elements.filteredRevenue.textContent = formatMoney(summary.total_revenue);
  }
  elements.filteredDelivered.textContent = integerFormatter.format(summary.delivered_orders);
  elements.filteredFailed.textContent = integerFormatter.format(
    summary.returned_orders + summary.canceled_orders,
  );
}

function validateFilters() {
  if (
    elements.dateFromFilter.value &&
    elements.dateToFilter.value &&
    elements.dateFromFilter.value > elements.dateToFilter.value
  ) {
    showError("Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.");
    elements.resultCount.textContent = "Bộ lọc chưa hợp lệ";
    return false;
  }
  if (
    elements.minTotalFilter.value &&
    elements.maxTotalFilter.value &&
    Number(elements.minTotalFilter.value) > Number(elements.maxTotalFilter.value)
  ) {
    showError("Giá trị tối thiểu không được lớn hơn giá trị tối đa.");
    elements.resultCount.textContent = "Bộ lọc chưa hợp lệ";
    return false;
  }
  return true;
}

function buildFilterParams(includePagination = true) {
  const params = new URLSearchParams();
  if (includePagination) {
    params.set("page_number", String(state.pageNumber));
    params.set("page_size", String(state.pageSize));
  }
  const query = elements.searchInput.value.trim();
  if (query) params.set("q", query);
  if (elements.shopFilter.value) params.set("shop_id", elements.shopFilter.value);
  if (elements.pageFilter.value) params.set("page_id", elements.pageFilter.value);
  if (elements.statusFilter.value) {
    params.set("business_status", elements.statusFilter.value);
  }
  if (includePagination && elements.sortFilter.value) {
    params.set("sort_by", elements.sortFilter.value);
  }
  if (elements.productFilter.value.trim()) params.set("product", elements.productFilter.value.trim());
  if (elements.carrierFilter.value) params.set("carrier_name", elements.carrierFilter.value);
  if (elements.deliveryStatusFilter.value) {
    params.set("delivery_status", elements.deliveryStatusFilter.value);
  }
  if (elements.dateFromFilter.value) {
    params.set("date_from", new Date(`${elements.dateFromFilter.value}T00:00:00`).toISOString());
  }
  if (elements.dateToFilter.value) {
    params.set("date_to", new Date(`${elements.dateToFilter.value}T23:59:59.999`).toISOString());
  }
  if (elements.minTotalFilter.value) params.set("min_total", elements.minTotalFilter.value);
  if (elements.maxTotalFilter.value) params.set("max_total", elements.maxTotalFilter.value);
  if (elements.trackingFilter.value) params.set("has_tracking", elements.trackingFilter.value);
  if (elements.sentFilter.value) params.set("sent_to_carrier", elements.sentFilter.value);
  if (elements.returnedFilter.value) params.set("returned", elements.returnedFilter.value);
  return params;
}

function buildExportFilters() {
  const booleanValue = (element) =>
    element.value === "" ? null : element.value === "true";
  return {
    q: elements.searchInput.value.trim() || null,
    shop_id: elements.shopFilter.value ? [elements.shopFilter.value] : null,
    page_id: elements.pageFilter.value ? [elements.pageFilter.value] : null,
    business_status: elements.statusFilter.value ? [elements.statusFilter.value] : null,
    carrier_name: elements.carrierFilter.value ? [elements.carrierFilter.value] : null,
    delivery_status: elements.deliveryStatusFilter.value
      ? [elements.deliveryStatusFilter.value]
      : null,
    date_from: elements.dateFromFilter.value
      ? new Date(`${elements.dateFromFilter.value}T00:00:00`).toISOString()
      : null,
    date_to: elements.dateToFilter.value
      ? new Date(`${elements.dateToFilter.value}T23:59:59.999`).toISOString()
      : null,
    min_total: elements.minTotalFilter.value || null,
    max_total: elements.maxTotalFilter.value || null,
    has_tracking: booleanValue(elements.trackingFilter),
    sent_to_carrier: booleanValue(elements.sentFilter),
    returned: booleanValue(elements.returnedFilter),
    product: elements.productFilter.value.trim() || null,
  };
}

async function loadOrders() {
  clearError();
  elements.resultCount.textContent = "Đang tải…";
  if (!validateFilters()) return;
  const params = buildFilterParams();
  params.set("include_summary", "false");
  const summaryParams = buildFilterParams(false);
  const exportFilters = buildExportFilters();
  elements.filteredOrders.textContent = "Đang tính…";
  elements.filteredRevenue.textContent = "Đang tính…";
  elements.filteredDelivered.textContent = "Đang tính…";
  elements.filteredFailed.textContent = "Đang tính…";
  const summaryPromise = fetchJson(`/api/orders/summary?${summaryParams.toString()}`)
    .then((summary) => {
      renderOrderSummary(summary);
      return null;
    })
    .catch((error) => error);

  try {
    const data = await fetchJson(`/api/orders?${params.toString()}`);
    state.appliedExportFilters = exportFilters;
    renderOrders(data);
    const summaryError = await summaryPromise;
    if (summaryError) {
      showError(`Danh sách đã tải nhưng chưa tính được thống kê. ${summaryError.message}`);
    }
  } catch (error) {
    elements.ordersBody.replaceChildren();
    showError(`Không thể tải đơn hàng. ${error.message}`);
    elements.resultCount.textContent = "Không tải được dữ liệu";
  }
}

async function exportOrders() {
  clearError();
  const selectedCount = state.allMatchingSelected
    ? state.totalMatchingOrders
    : state.selectedOrderKeys.size;
  if (selectedCount === 0) {
    showError("Hãy chọn ít nhất một đơn, một trang hoặc toàn bộ kết quả đang lọc.");
    return;
  }
  elements.exportExcel.disabled = true;
  elements.exportExcel.textContent = "Đang tạo file…";
  try {
    const payload = {
      selection_mode: state.allMatchingSelected ? "filtered" : "selected",
      orders: state.allMatchingSelected
        ? []
        : Array.from(state.selectedOrderKeys, (key) => {
            const [shop_id, order_id] = JSON.parse(key);
            return { shop_id, order_id };
          }),
      ...state.appliedExportFilters,
    };
    const response = await secureFetch("/api/orders/export", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || `Yêu cầu thất bại (${response.status})`);
    }
    const blob = await response.blob();
    const disposition = response.headers.get("Content-Disposition") || "";
    const filenameMatch = disposition.match(/filename="?([^";]+)"?/i);
    const filename = filenameMatch ? filenameMatch[1] : "pancake-orders.xlsx";
    const downloadUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = filename;
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(downloadUrl);
  } catch (error) {
    showError(`Không thể xuất Excel. ${error.message}`);
  } finally {
    elements.exportExcel.textContent = "Xuất đơn đã chọn";
    renderOrderSelection();
  }
}

function advancedFilterCount() {
  return [
    elements.productFilter,
    elements.carrierFilter,
    elements.deliveryStatusFilter,
    elements.dateFromFilter,
    elements.dateToFilter,
    elements.minTotalFilter,
    elements.maxTotalFilter,
    elements.trackingFilter,
    elements.sentFilter,
    elements.returnedFilter,
  ].filter((element) => element.value).length;
}

function updateAdvancedLabel() {
  const count = advancedFilterCount();
  elements.toggleAdvanced.textContent = count
    ? `Bộ lọc nâng cao (${count})`
    : "Bộ lọc nâng cao";
}

function detailField(label, value, className = "") {
  const field = createElement("div", `detail-field ${className}`.trim());
  field.append(createElement("span", "", label), createElement("strong", "", value));
  return field;
}

function receiptStatusLabel(value) {
  return {
    received: "Đã nhận",
    returning: "Đang hoàn",
    returned: "Đã hoàn",
    canceled: "Đã hủy",
    pending: "Chưa nhận",
  }[value] || text(value);
}

function renderOrderDetail(order) {
  elements.dialogTitle.textContent = text(order.order_id);
  const shipping = order.shipping || {};
  const grid = createElement("div", "detail-grid");
  grid.append(
    detailField("Cửa hàng", order.shop_name),
    detailField("Shop ID", order.shop_id),
    detailField("Khách hàng", order.customer?.name),
    detailField("Điện thoại", order.customer?.phone),
    detailField("Page", order.page_name),
    detailField("Tình trạng đơn", order.business_status_label),
    detailField("Giá trị", formatMoney(order.total_price, order.currency)),
    detailField("Cập nhật", formatDate(order.updated_at)),
    detailField("Mã vận đơn", shipping.tracking_code),
    detailField("Đơn vị vận chuyển", shipping.carrier_name),
    detailField("Phí vận chuyển", formatMoney(shipping.shipping_fee, order.currency)),
    detailField("Gửi vận chuyển", shipping.sent_to_carrier ? "Đã gửi" : "Chưa gửi"),
    detailField("Trạng thái giao hàng", shipping.delivery_status_label),
    detailField("Kết quả nhận hàng", receiptStatusLabel(shipping.receipt_status)),
    detailField("Người nhận", shipping.recipient_name),
    detailField("SĐT nhận hàng", shipping.phone),
    detailField("Phí hoàn", formatMoney(shipping.return_fee, order.currency)),
    detailField("Địa chỉ", shipping.address, "detail-field-wide"),
    detailField("Lý do hoàn / hủy", shipping.returned_reason, "detail-field-wide"),
  );

  const heading = createElement("h3", "items-heading", `Sản phẩm · ${order.items.length}`);
  const list = createElement("div", "items-list");
  for (const item of order.items) {
    const row = createElement("div", "item-row");
    row.append(
      createElement("strong", "", item.product_name),
      createElement("span", "", `SL ${text(item.quantity, "0")}`),
      createElement("span", "money", formatMoney(item.unit_price, order.currency)),
    );
    list.append(row);
  }
  elements.dialogContent.replaceChildren(grid, heading, list);
}

async function openOrder(orderId, shopId) {
  elements.dialogTitle.textContent = "Đang tải…";
  elements.dialogContent.replaceChildren(createElement("p", "secondary-text", "Đang lấy chi tiết đơn hàng…"));
  elements.orderDialog.showModal();
  try {
    const params = new URLSearchParams({ shop_id: shopId });
    const order = await fetchJson(`/api/orders/${encodeURIComponent(orderId)}?${params.toString()}`);
    renderOrderDetail(order);
  } catch (error) {
    elements.dialogContent.replaceChildren(
      createElement("div", "error-banner", `Không thể tải chi tiết. ${error.message}`),
    );
  }
}

elements.filterForm.addEventListener("submit", (event) => {
  event.preventDefault();
  state.pageNumber = 1;
  resetOrderSelection();
  loadOrders();
});

elements.loginForm.addEventListener("submit", login);
elements.logoutButton.addEventListener("click", logout);
elements.helpButton.addEventListener("click", () => elements.helpDialog.showModal());
elements.closeHelpDialog.addEventListener("click", () => elements.helpDialog.close());
elements.helpDialog.addEventListener("click", (event) => {
  if (event.target === elements.helpDialog) elements.helpDialog.close();
});
elements.changePasswordButton.addEventListener("click", () => openPasswordChange(false));
elements.passwordForm.addEventListener("submit", saveOwnPassword);
elements.closePasswordDialog.addEventListener("click", closePasswordChange);
elements.cancelPasswordChange.addEventListener("click", closePasswordChange);
elements.passwordDialog.addEventListener("cancel", (event) => {
  if (state.passwordChangeRequired) event.preventDefault();
});
elements.passwordDialog.addEventListener("click", (event) => {
  if (event.target === elements.passwordDialog) closePasswordChange();
});
elements.manageStaffButton.addEventListener("click", openStaffManagement);
elements.staffForm.addEventListener("submit", saveStaff);
elements.staffRole.addEventListener("change", updateAccountRoleFields);
elements.cancelStaffEdit.addEventListener("click", resetStaffForm);
elements.copyTemporaryCredential.addEventListener("click", copyTemporaryCredential);
elements.selectAllStaffShops.addEventListener("click", () => {
  for (const input of elements.staffShopOptions.querySelectorAll('input[type="checkbox"]')) {
    input.checked = true;
  }
});
elements.clearStaffShops.addEventListener("click", () => {
  for (const input of elements.staffShopOptions.querySelectorAll('input[type="checkbox"]')) {
    input.checked = false;
  }
});
elements.closeStaffDialog.addEventListener("click", () => elements.staffDialog.close());
elements.staffDialog.addEventListener("click", (event) => {
  if (event.target === elements.staffDialog) elements.staffDialog.close();
});
elements.auditLogButton.addEventListener("click", openAuditLog);
elements.securityAlertsButton.addEventListener("click", openSecurityAlerts);
elements.closeSecurityAlertsDialog.addEventListener("click", () => elements.securityAlertsDialog.close());
elements.securityAlertsDialog.addEventListener("click", (event) => {
  if (event.target === elements.securityAlertsDialog) elements.securityAlertsDialog.close();
});
elements.refreshSecurityAlerts.addEventListener("click", () => loadSecurityAlerts(true));
elements.closeAuditDialog.addEventListener("click", () => elements.auditDialog.close());
elements.auditDialog.addEventListener("click", (event) => {
  if (event.target === elements.auditDialog) elements.auditDialog.close();
});
elements.applyAuditFilters.addEventListener("click", () => {
  state.auditPageNumber = 1;
  loadAuditLog();
});
elements.resetAuditFilters.addEventListener("click", resetAuditFilters);
elements.auditIpFilter.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    state.auditPageNumber = 1;
    loadAuditLog();
  }
});
elements.refreshAuditLog.addEventListener("click", loadAuditLog);
elements.previousAuditPage.addEventListener("click", () => {
  if (state.auditPageNumber > 1) {
    state.auditPageNumber -= 1;
    loadAuditLog();
  }
});
elements.nextAuditPage.addEventListener("click", () => {
  if (state.auditPageNumber < state.auditTotalPages) {
    state.auditPageNumber += 1;
    loadAuditLog();
  }
});

elements.shopFilter.addEventListener("change", () => {
  state.pageNumber = 1;
  resetOrderSelection();
  loadOrders();
});

elements.pageFilter.addEventListener("change", () => {
  state.pageNumber = 1;
  resetOrderSelection();
  loadOrders();
});

elements.statusFilter.addEventListener("change", () => {
  state.pageNumber = 1;
  resetOrderSelection();
  loadOrders();
});

elements.sortFilter.addEventListener("change", () => {
  state.pageNumber = 1;
  resetOrderSelection();
  loadOrders();
});

elements.toggleAdvanced.addEventListener("click", () => {
  const willOpen = elements.advancedFilters.hidden;
  elements.advancedFilters.hidden = !willOpen;
  elements.toggleAdvanced.setAttribute("aria-expanded", String(willOpen));
});

elements.advancedFilters.addEventListener("change", updateAdvancedLabel);
elements.advancedFilters.addEventListener("input", updateAdvancedLabel);

elements.resetFilters.addEventListener("click", () => {
  elements.filterForm.reset();
  elements.savedFilterSelect.value = "";
  elements.savedFilterName.value = "";
  elements.deleteFilter.disabled = true;
  showSavedFilterMessage("");
  updateAdvancedLabel();
  state.pageNumber = 1;
  resetOrderSelection();
  loadOrders();
});

elements.exportExcel.addEventListener("click", exportOrders);
elements.selectCurrentPage.addEventListener("change", () => {
  for (const order of state.currentPageOrders) {
    const key = orderSelectionKey(order);
    if (elements.selectCurrentPage.checked) state.selectedOrderKeys.add(key);
    else state.selectedOrderKeys.delete(key);
  }
  renderOrderSelection();
});
elements.selectAllFiltered.addEventListener("click", () => {
  if (state.currentUser?.role === "staff" && state.totalMatchingOrders > 500) {
    showError(
      "Nhân viên chỉ được xuất tối đa 500 đơn. Hãy thu hẹp bộ lọc còn 500 đơn hoặc ít hơn.",
    );
    return;
  }
  clearError();
  state.selectedOrderKeys.clear();
  state.allMatchingSelected = true;
  renderOrderSelection();
});
elements.clearOrderSelection.addEventListener("click", resetOrderSelection);
elements.syncNow.addEventListener("click", syncNow);
elements.savedFilterSelect.addEventListener("change", applySavedFilter);
elements.saveFilter.addEventListener("click", saveCurrentFilter);
elements.deleteFilter.addEventListener("click", deleteSavedFilter);

elements.firstPage.addEventListener("click", () => goToPage(1));
elements.previousPage.addEventListener("click", () => goToPage(state.pageNumber - 1));
elements.nextPage.addEventListener("click", () => goToPage(state.pageNumber + 1));
elements.lastPage.addEventListener("click", () => goToPage(state.totalPages));
elements.pageJumpForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const requestedPage = elements.pageJumpInput.valueAsNumber;
  if (!Number.isInteger(requestedPage) || requestedPage < 1 || requestedPage > state.totalPages) {
    showError(`Hãy nhập số trang từ 1 đến ${integerFormatter.format(state.totalPages)}.`);
    elements.pageJumpInput.focus();
    return;
  }
  goToPage(requestedPage);
});

elements.closeDialog.addEventListener("click", () => elements.orderDialog.close());
elements.orderDialog.addEventListener("click", (event) => {
  if (event.target === elements.orderDialog) elements.orderDialog.close();
});

document.addEventListener("contextmenu", (event) => {
  event.preventDefault();
  showInspectionNotice();
});

document.addEventListener("keydown", (event) => {
  if (!isBlockedInspectionShortcut(event)) return;
  event.preventDefault();
  event.stopPropagation();
  showInspectionNotice();
});

async function initialize() {
  try {
    state.csrfToken = readCookie("hongha_csrf");
    const auth = await fetchJson("/api/auth/me");
    showApplication(auth.user);
    if (auth.user.must_change_password) {
      openPasswordChange(true);
      return;
    }
    await loadApplicationData();
  } catch (error) {
    if (error.status === 401) return;
    showError(`Không thể khởi tạo cổng tra cứu. ${error.message}`);
  }
}

initialize();
updateDevtoolsPrivacyShield();
window.setInterval(updateDevtoolsPrivacyShield, 750);
window.addEventListener("resize", updateDevtoolsPrivacyShield);
window.setInterval(() => {
  if (!state.currentUser || document.hidden) return;
  loadSystemStatus().catch(() => {
    elements.systemStateText.textContent = "Không kiểm tra được đồng bộ";
  });
}, 15_000);

document.addEventListener("visibilitychange", () => {
  if (!document.hidden && state.currentUser) {
    loadSystemStatus().catch(() => {
      elements.systemStateText.textContent = "Không kiểm tra được đồng bộ";
    });
  }
});
