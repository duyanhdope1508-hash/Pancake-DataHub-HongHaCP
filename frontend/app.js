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
};

const elements = {
  loginShell: document.querySelector("#loginShell"),
  loginForm: document.querySelector("#loginForm"),
  loginUsername: document.querySelector("#loginUsername"),
  loginPassword: document.querySelector("#loginPassword"),
  loginError: document.querySelector("#loginError"),
  loginButton: document.querySelector("#loginButton"),
  appShell: document.querySelector("#appShell"),
  currentUserName: document.querySelector("#currentUserName"),
  currentUserRole: document.querySelector("#currentUserRole"),
  manageStaffButton: document.querySelector("#manageStaffButton"),
  auditLogButton: document.querySelector("#auditLogButton"),
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
  closeStaffDialog: document.querySelector("#closeStaffDialog"),
  staffForm: document.querySelector("#staffForm"),
  staffFormTitle: document.querySelector("#staffFormTitle"),
  staffUserId: document.querySelector("#staffUserId"),
  staffDisplayName: document.querySelector("#staffDisplayName"),
  staffUsername: document.querySelector("#staffUsername"),
  staffResetPasswordField: document.querySelector("#staffResetPasswordField"),
  staffResetPassword: document.querySelector("#staffResetPassword"),
  staffActiveField: document.querySelector("#staffActiveField"),
  staffIsActive: document.querySelector("#staffIsActive"),
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
  staffCount: document.querySelector("#staffCount"),
  auditDialog: document.querySelector("#auditDialog"),
  closeAuditDialog: document.querySelector("#closeAuditDialog"),
  auditActionFilter: document.querySelector("#auditActionFilter"),
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
  previousPage: document.querySelector("#previousPage"),
  nextPage: document.querySelector("#nextPage"),
  pageIndicator: document.querySelector("#pageIndicator"),
  orderDialog: document.querySelector("#orderDialog"),
  dialogTitle: document.querySelector("#dialogTitle"),
  dialogContent: document.querySelector("#dialogContent"),
  closeDialog: document.querySelector("#closeDialog"),
};

const SAVED_FILTERS_STORAGE_KEY = "pancakeDataHub.savedFilters.v1";
const MAX_SAVED_FILTERS = 20;
const AUDIT_ACTION_LABELS = {
  "auth.login": "Đăng nhập",
  "auth.logout": "Đăng xuất",
  "auth.password_change": "Đổi mật khẩu",
  "staff.create": "Tạo nhân viên",
  "staff.update": "Sửa nhân viên",
  "orders.sync": "Đồng bộ đơn",
  "orders.export": "Xuất Excel",
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
  state.currentUser = null;
  state.staffManagement = null;
  state.passwordChangeRequired = false;
  state.csrfToken = "";
  elements.ordersBody.replaceChildren();
  elements.dialogContent.replaceChildren();
  elements.staffList.replaceChildren();
  elements.staffShopOptions.replaceChildren();
  elements.auditBody.replaceChildren();
  elements.auditActionFilter.value = "";
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
  elements.passwordForm.reset();
  elements.appShell.hidden = true;
  elements.loginShell.hidden = false;
  elements.loginError.textContent = message;
  elements.loginError.hidden = !message;
  elements.loginPassword.value = "";
  if (elements.staffDialog.open) elements.staffDialog.close();
  elements.loginUsername.focus();
}

function showApplication(user) {
  state.currentUser = user;
  elements.currentUserName.textContent = text(user.display_name, user.username);
  elements.currentUserRole.textContent = user.role === "admin" ? "Quản trị viên" : "Nhân viên";
  elements.manageStaffButton.hidden = user.role !== "admin";
  elements.auditLogButton.hidden = user.role !== "admin";
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

function resetStaffForm() {
  elements.staffForm.reset();
  elements.staffUserId.value = "";
  elements.staffUsername.disabled = false;
  elements.staffUsername.required = true;
  elements.staffResetPassword.checked = false;
  elements.staffResetPasswordField.hidden = true;
  elements.staffActiveField.hidden = true;
  elements.staffFormTitle.textContent = "Thêm nhân viên";
  elements.saveStaffButton.textContent = "Tạo nhân viên";
  elements.cancelStaffEdit.hidden = true;
  setStaffFormMessage("");
  hideTemporaryCredential();
  renderStaffShopOptions();
}

function beginStaffEdit(user) {
  elements.staffUserId.value = user.id;
  elements.staffDisplayName.value = user.display_name;
  elements.staffUsername.value = user.username;
  elements.staffUsername.disabled = true;
  elements.staffUsername.required = false;
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
  elements.staffDisplayName.focus();
}

function renderStaffList() {
  const users = state.staffManagement?.users || [];
  const shopNames = new Map(
    (state.staffManagement?.shops || []).map((shop) => [shop.shop_id, shop.shop_name]),
  );
  elements.staffCount.textContent = `${integerFormatter.format(users.length)} tài khoản`;
  if (users.length === 0) {
    elements.staffList.replaceChildren(
      createElement("p", "staff-list-empty", "Chưa có tài khoản nhân viên."),
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
      assignedShops.length ? assignedShops.join(" · ") : "Chưa được cấp shop",
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
    const editButton = createElement("button", "secondary-button", "Sửa quyền");
    editButton.type = "button";
    editButton.addEventListener("click", () => beginStaffEdit(user));
    footer.append(editButton);
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
          : "Đã tạo nhân viên. Hãy sao chép thông tin đăng nhập bên dưới.",
      );
    } else {
      setStaffFormMessage(isEditing ? "Đã cập nhật nhân viên." : "Đã tạo nhân viên.");
    }
  } catch (error) {
    setStaffFormMessage(error.message, true);
  } finally {
    elements.saveStaffButton.disabled = false;
    elements.saveStaffButton.textContent = elements.staffUserId.value
      ? "Lưu thay đổi"
      : "Tạo nhân viên";
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
  if (item.action === "staff.create" || item.action === "staff.update") {
    const parts = [];
    if (metadata.shop_count !== undefined) {
      parts.push(`${integerFormatter.format(metadata.shop_count)} shop`);
    }
    if (metadata.password_changed) parts.push("Có đổi mật khẩu");
    if (metadata.active === false) parts.push("Đã khóa tài khoản");
    return parts.join(" · ") || "—";
  }
  if (item.action === "auth.login" && item.result === "denied") {
    return metadata.username ? `Tài khoản: ${metadata.username}` : "Sai thông tin đăng nhập";
  }
  return item.resource_id ? `${text(item.resource_type, "Đối tượng")}: ${item.resource_id}` : "—";
}

function auditResultLabel(result) {
  return {
    success: "Thành công",
    denied: "Từ chối",
    skipped: "Bỏ qua",
    partial: "Có lỗi một phần",
  }[result] || text(result);
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
    row.append(
      createElement("td", "", formatDate(item.created_at)),
      actorCell,
      createElement("td", "", AUDIT_ACTION_LABELS[item.action] || item.action),
      createElement(
        "td",
        `audit-result audit-result-${item.result}`,
        auditResultLabel(item.result),
      ),
      createElement("td", "audit-detail", auditDetail(item)),
    );
    return row;
  });
  elements.auditBody.replaceChildren(...rows);
  elements.auditEmpty.hidden = rows.length !== 0;

  const selectedAction = elements.auditActionFilter.value;
  const actionOptions = [createElement("option", "", "Tất cả hoạt động")];
  actionOptions[0].value = "";
  for (const action of data.actions) {
    const option = createElement("option", "", AUDIT_ACTION_LABELS[action] || action);
    option.value = action;
    actionOptions.push(option);
  }
  elements.auditActionFilter.replaceChildren(...actionOptions);
  elements.auditActionFilter.value = selectedAction;

  const pagination = data.pagination;
  state.auditPageNumber = pagination.page_number;
  state.auditTotalPages = Math.max(pagination.total_pages, 1);
  elements.auditPageIndicator.textContent = `Trang ${state.auditPageNumber} / ${state.auditTotalPages}`;
  elements.previousAuditPage.disabled = state.auditPageNumber <= 1;
  elements.nextAuditPage.disabled = state.auditPageNumber >= state.auditTotalPages;
}

async function loadAuditLog() {
  elements.auditError.textContent = "";
  const params = new URLSearchParams({
    page_number: String(state.auditPageNumber),
    page_size: "50",
  });
  if (elements.auditActionFilter.value) {
    params.set("action", elements.auditActionFilter.value);
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
      `${status.delivery_status} · ${integerFormatter.format(status.order_count)}`,
    );
  }
}

async function loadSystemStatus() {
  const data = await fetchJson("/api/system-status");
  const latest = data.latest_sync;
  if (!latest) {
    elements.systemStateText.textContent = "Chưa có lần đồng bộ";
    return;
  }
  if (latest.status !== "success") {
    elements.systemStateText.textContent = "Cần kiểm tra đồng bộ";
    return;
  }
  elements.systemStateText.textContent = `Đồng bộ ${formatDate(latest.finished_at)}`;
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
    await Promise.all([loadSystemStatus(), loadOrders()]);
    const shopCount = integerFormatter.format(payload.shops_processed);
    const orderCount = integerFormatter.format(payload.orders_transformed);
    if (payload.success) {
      elements.syncNow.textContent = `Xong · ${shopCount} shop, ${orderCount} đơn cập nhật`;
    } else {
      showError(
        `Đã đồng bộ nhưng có ${integerFormatter.format(payload.connectors_failed)} kết nối lỗi.`,
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

function orderRow(order, sameCustomer = false) {
  const row = document.createElement("tr");
  if (sameCustomer) row.classList.add("customer-group-continuation");

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
      [order.status_name, order.carrier_name, order.delivery_status].filter(Boolean).join(" · "),
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
  elements.emptyState.hidden = data.items.length !== 0;

  const pagination = data.pagination;
  state.totalPages = Math.max(pagination.total_pages, 1);
  elements.resultCount.textContent = `${integerFormatter.format(pagination.total_items)} kết quả`;
  elements.pageIndicator.textContent = `Trang ${state.pageNumber} / ${state.totalPages}`;
  elements.previousPage.disabled = state.pageNumber <= 1;
  elements.nextPage.disabled = state.pageNumber >= state.totalPages;
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

async function loadOrders() {
  clearError();
  elements.resultCount.textContent = "Đang tải…";
  if (!validateFilters()) return;
  const params = buildFilterParams();
  params.set("include_summary", "false");
  const summaryParams = buildFilterParams(false);
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
    renderOrders(await fetchJson(`/api/orders?${params.toString()}`));
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
  if (!validateFilters()) return;
  elements.exportExcel.disabled = true;
  elements.exportExcel.textContent = "Đang tạo file…";
  try {
    const params = buildFilterParams(false);
    const response = await fetch(`/api/orders/export?${params.toString()}`);
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
    elements.exportExcel.disabled = false;
    elements.exportExcel.textContent = "Xuất Excel";
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
    detailField("Trạng thái giao hàng", shipping.delivery_status),
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
  loadOrders();
});

elements.loginForm.addEventListener("submit", login);
elements.logoutButton.addEventListener("click", logout);
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
elements.closeAuditDialog.addEventListener("click", () => elements.auditDialog.close());
elements.auditDialog.addEventListener("click", (event) => {
  if (event.target === elements.auditDialog) elements.auditDialog.close();
});
elements.auditActionFilter.addEventListener("change", () => {
  state.auditPageNumber = 1;
  loadAuditLog();
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
  loadOrders();
});

elements.pageFilter.addEventListener("change", () => {
  state.pageNumber = 1;
  loadOrders();
});

elements.statusFilter.addEventListener("change", () => {
  state.pageNumber = 1;
  loadOrders();
});

elements.sortFilter.addEventListener("change", () => {
  state.pageNumber = 1;
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
  loadOrders();
});

elements.exportExcel.addEventListener("click", exportOrders);
elements.syncNow.addEventListener("click", syncNow);
elements.savedFilterSelect.addEventListener("change", applySavedFilter);
elements.saveFilter.addEventListener("click", saveCurrentFilter);
elements.deleteFilter.addEventListener("click", deleteSavedFilter);

elements.previousPage.addEventListener("click", () => {
  if (state.pageNumber > 1) {
    state.pageNumber -= 1;
    loadOrders();
  }
});

elements.nextPage.addEventListener("click", () => {
  if (state.pageNumber < state.totalPages) {
    state.pageNumber += 1;
    loadOrders();
  }
});

elements.closeDialog.addEventListener("click", () => elements.orderDialog.close());
elements.orderDialog.addEventListener("click", (event) => {
  if (event.target === elements.orderDialog) elements.orderDialog.close();
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
window.setInterval(() => {
  if (!state.currentUser) return;
  loadSystemStatus().catch(() => {
    elements.systemStateText.textContent = "Không kiểm tra được đồng bộ";
  });
}, 60_000);
