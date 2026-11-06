import os
import tempfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import xlsxwriter
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.business_status import business_status_label, classify_business_status
from app.models import CoreOrder, Shop
from app.search import filtered_orders_statement

EXPORT_MAX_ORDERS = 100_000
STAFF_EXPORT_MAX_ORDERS = 500
LOCAL_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")


class ExportLimitExceeded(ValueError):
    def __init__(self, total_orders: int, max_orders: int = EXPORT_MAX_ORDERS):
        self.total_orders = total_orders
        self.max_orders = max_orders
        super().__init__(
            f"Export contains {total_orders} orders; maximum is {max_orders}"
        )


def export_limit_for_role(role: str) -> int:
    return EXPORT_MAX_ORDERS if role == "admin" else STAFF_EXPORT_MAX_ORDERS


def _excel_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(LOCAL_TIMEZONE).replace(tzinfo=None)
    return value


def _write_text(worksheet: Any, row: int, column: int, value: Any, cell_format: Any) -> None:
    if value is None or value == "":
        worksheet.write_blank(row, column, None, cell_format)
        return
    worksheet.write_string(row, column, str(value), cell_format)


def export_orders_xlsx(
    session: Session,
    *,
    query: str | None = None,
    shop_id: str | list[str] | None = None,
    page_id: str | list[str] | None = None,
    status: int | list[int] | None = None,
    business_status: str | list[str] | None = None,
    carrier_name: str | list[str] | None = None,
    delivery_status: str | list[str] | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    min_total: Decimal | None = None,
    max_total: Decimal | None = None,
    has_tracking: bool | None = None,
    sent_to_carrier: bool | None = None,
    returned: bool | None = None,
    product: str | None = None,
    max_orders: int = EXPORT_MAX_ORDERS,
) -> tuple[Path, int]:
    statement = filtered_orders_statement(
        query=query,
        shop_id=shop_id,
        page_id=page_id,
        status=status,
        business_status=business_status,
        carrier_name=carrier_name,
        delivery_status=delivery_status,
        date_from=date_from,
        date_to=date_to,
        min_total=min_total,
        max_total=max_total,
        has_tracking=has_tracking,
        sent_to_carrier=sent_to_carrier,
        returned=returned,
        product=product,
    )
    count_source = statement.with_only_columns(
        CoreOrder.shop_id,
        CoreOrder.source_order_id,
        maintain_column_froms=True,
    ).order_by(None).subquery()
    total_orders = session.scalar(select(func.count()).select_from(count_source)) or 0
    if total_orders > max_orders:
        raise ExportLimitExceeded(total_orders, max_orders)

    shop_names = dict(session.execute(select(Shop.id, Shop.name)).all())
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix="pancake-orders-", suffix=".xlsx"
    )
    os.close(file_descriptor)
    output_path = Path(temporary_name)

    try:
        workbook = xlsxwriter.Workbook(
            output_path,
            {
                "constant_memory": True,
                "strings_to_formulas": False,
                "strings_to_urls": False,
            },
        )
        workbook.set_properties(
            {
                "title": "Danh sách đơn hàng đã lọc",
                "subject": "Pancake Data Hub",
                "company": "Hồng Hà",
            }
        )
        worksheet = workbook.add_worksheet("Đơn hàng")
        worksheet.hide_gridlines(2)

        title_format = workbook.add_format(
            {"bold": True, "font_size": 15, "font_color": "#1C2621"}
        )
        context_format = workbook.add_format(
            {"font_size": 10, "font_color": "#65716A"}
        )
        header_format = workbook.add_format(
            {
                "bold": True,
                "font_color": "#FFFFFF",
                "bg_color": "#1E6B4D",
                "border": 1,
                "border_color": "#FFFFFF",
                "align": "center",
                "valign": "vcenter",
            }
        )
        text_format = workbook.add_format({"valign": "vcenter"})
        date_format = workbook.add_format(
            {"num_format": "dd/mm/yyyy hh:mm", "valign": "vcenter"}
        )
        number_format = workbook.add_format(
            {"num_format": "#,##0", "valign": "vcenter"}
        )
        money_format = workbook.add_format(
            {"num_format": "#,##0", "valign": "vcenter"}
        )

        headers = [
            "Mã đơn",
            "Cửa hàng",
            "Shop ID",
            "Page",
            "Ngày tạo",
            "Khách hàng",
            "Điện thoại",
            "Địa chỉ giao hàng",
            "Tình trạng đơn",
            "Trạng thái gốc",
            "Đơn vị vận chuyển",
            "Trạng thái giao",
            "Mã vận đơn",
            "Số lượng",
            "Giá trị đơn",
            "Phí vận chuyển",
            "Lý do hoàn / hủy",
        ]
        last_column = len(headers) - 1
        worksheet.merge_range(0, 0, 0, last_column, "Danh sách đơn hàng", title_format)
        generated_at = datetime.now(LOCAL_TIMEZONE).strftime("%d/%m/%Y %H:%M")
        worksheet.merge_range(
            1,
            0,
            1,
            last_column,
            f"Xuất từ Pancake Data Hub lúc {generated_at} · {total_orders:,} đơn",
            context_format,
        )
        worksheet.write_row(3, 0, headers, header_format)
        worksheet.set_row(3, 28)
        worksheet.freeze_panes(4, 1)

        widths = [20, 26, 15, 26, 18, 24, 16, 40, 19, 16, 20, 20, 22, 12, 16, 16, 42]
        for column, width in enumerate(widths):
            worksheet.set_column(column, column, width)

        rows = session.execute(
            statement.order_by(CoreOrder.source_updated_at.desc().nullslast())
        ).yield_per(1000)
        excel_row = 4
        for order, customer in rows:
            normalized_status = classify_business_status(
                status=order.status,
                status_name=order.status_name,
                delivery_status=order.delivery_status,
                sent_to_carrier_at=order.sent_to_carrier_at,
            )
            values = [
                order.source_order_id,
                shop_names.get(order.shop_id, order.shop_id),
                order.shop_id,
                order.page_name,
                _excel_datetime(order.inserted_at),
                customer.name if customer else None,
                (
                    customer.primary_phone
                    if customer and customer.primary_phone
                    else order.shipping_phone
                ),
                order.shipping_address,
                business_status_label(normalized_status),
                order.status_name,
                order.carrier_name,
                order.delivery_status,
                order.tracking_code,
                order.total_quantity,
                order.total_price,
                order.shipping_fee,
                order.returned_reason,
            ]
            for column, value in enumerate(values):
                if column == 4 and value is not None:
                    worksheet.write_datetime(excel_row, column, value, date_format)
                elif column in {13, 14, 15} and value is not None:
                    numeric_value = float(value)
                    worksheet.write_number(
                        excel_row,
                        column,
                        numeric_value,
                        money_format if column in {14, 15} else number_format,
                    )
                else:
                    _write_text(worksheet, excel_row, column, value, text_format)
            excel_row += 1

        last_data_row = max(excel_row - 1, 3)
        worksheet.autofilter(3, 0, last_data_row, last_column)
        workbook.close()
    except Exception:
        output_path.unlink(missing_ok=True)
        raise

    return output_path, total_orders
