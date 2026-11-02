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
  ordersBody: document.querySelector("#ordersBody"),
  emptyState: document.querySelector("#emptyState"),
  errorBanner: document.querySelector("#errorBanner"),
  resultCount: document.querySelector("#resultCount"),
  totalOrders: document.querySelector("#totalOrders"),
  totalShops: document.querySelector("#totalShops"),
  totalPages: document.querySelector("#totalPages"),
  totalStatuses: document.querySelector("#totalStatuses"),
  systemStateText: document.querySelector("#systemStateText"),
  previousPage: document.querySelector("#previousPage"),
  nextPage: document.querySelector("#nextPage"),
  pageIndicator: document.querySelector("#pageIndicator"),
  orderDialog: document.querySelector("#orderDialog"),
  dialogTitle: document.querySelector("#dialogTitle"),
  dialogContent: document.querySelector("#dialogContent"),
  closeDialog: document.querySelector("#closeDialog"),
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
  elements.totalStatuses.textContent = integerFormatter.format(data.statuses.length);

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
  for (const status of data.statuses) {
    addOption(
      elements.statusFilter,
      status.status,
      `${text(status.status_name, `Mã ${status.status}`)} · ${integerFormatter.format(status.order_count)}`,
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
  statusCell.append(createElement("span", "status-pill", order.status_name || `Mã ${order.status}`));

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

async function loadOrders() {
  clearError();
  elements.resultCount.textContent = "Đang tải…";
  const params = new URLSearchParams({
    page_number: String(state.pageNumber),
    page_size: String(state.pageSize),
  });
  const query = elements.searchInput.value.trim();
  if (query) params.set("q", query);
  if (elements.shopFilter.value) params.set("shop_id", elements.shopFilter.value);
  if (elements.pageFilter.value) params.set("page_id", elements.pageFilter.value);
  if (elements.statusFilter.value) params.set("status", elements.statusFilter.value);

  try {
    renderOrders(await fetchJson(`/api/orders?${params.toString()}`));
  } catch (error) {
    elements.ordersBody.replaceChildren();
    showError(`Không thể tải đơn hàng. ${error.message}`);
    elements.resultCount.textContent = "Không tải được dữ liệu";
  }
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
    detailField("Trạng thái", order.status_name || `Mã ${order.status}`),
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
    await Promise.all([loadFilters(), loadSystemStatus()]);
    await loadOrders();
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
