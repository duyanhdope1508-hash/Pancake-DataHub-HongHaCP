const state = {
  pageNumber: 1,
  pageSize: 20,
  totalPages: 1,
};

const elements = {
  filterForm: document.querySelector("#filterForm"),
  searchInput: document.querySelector("#searchInput"),
  shopFilter: document.querySelector("#shopFilter"),
  pageFilter: document.querySelector("#pageFilter"),
  statusFilter: document.querySelector("#statusFilter"),
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
  if (!response.ok) throw new Error(`Yêu cầu thất bại (${response.status})`);
  return response.json();
}

function addOption(select, value, label) {
  const option = document.createElement("option");
  option.value = String(value);
  option.textContent = label;
  select.append(option);
}

async function loadFilters() {
  const data = await fetchJson("/api/order-filters");
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
    const response = await fetch("/api/sync", {
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

function orderRow(order) {
  const row = document.createElement("tr");

  const orderCell = document.createElement("td");
  orderCell.append(
    createElement("span", "order-code", order.order_id),
    createElement("span", "secondary-text", order.shop_id),
  );

  const customerCell = document.createElement("td");
  customerCell.append(
    createElement("strong", "", order.customer_name),
    createElement("span", "secondary-text", order.customer_phone_masked),
  );

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

  row.append(orderCell, customerCell, pageCell, statusCell, totalCell, updatedCell, actionCell);
  return row;
}

function renderOrders(data) {
  elements.ordersBody.replaceChildren(...data.items.map(orderRow));
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
  elements.filteredRevenue.textContent = formatMoney(summary.total_revenue);
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
    detailField("Khách hàng", order.customer?.name),
    detailField("Điện thoại", order.customer?.phone_masked),
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
    detailField("SĐT nhận hàng", shipping.phone_masked),
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
    renderSavedFilters();
    await Promise.all([loadFilters(), loadSystemStatus(), loadOrders()]);
  } catch (error) {
    showError(`Không thể khởi tạo cổng tra cứu. ${error.message}`);
  }
}

initialize();
window.setInterval(() => {
  loadSystemStatus().catch(() => {
    elements.systemStateText.textContent = "Không kiểm tra được đồng bộ";
  });
}, 60_000);
