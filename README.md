# Pancake Data Hub — mốc 1

Bộ khung kiểm chứng kết nối Pancake POS và lưu dữ liệu đơn hàng dạng thô vào
PostgreSQL. Phiên bản này cố ý **chỉ đọc** từ Pancake và chưa mở endpoint chứa dữ
liệu khách hàng ra ngoài.

## Đã có

- Kết nối Pancake POS Open API bằng `api_key`.
- Lấy danh sách shop mà key được phép truy cập.
- Đồng bộ đơn hàng theo trang vào PostgreSQL bằng upsert, không tạo bản ghi trùng.
- Giữ nguyên JSON gốc để kiểm chứng mapping trước khi chuẩn hóa dữ liệu.
- Ghi lịch sử từng lần đồng bộ và lỗi nếu có.
- Docker Compose cho PostgreSQL và FastAPI.
- Health check nội bộ tại `http://127.0.0.1:8000/health`.

## Chạy lần đầu trên Windows

Yêu cầu: Docker Desktop đang hoạt động.

```powershell
Copy-Item .env.example .env
```

Mở `.env` trên chính máy này và thay:

```text
POSTGRES_PASSWORD=mot_mat_khau_dai_va_ngau_nhien
DATABASE_URL=postgresql+psycopg://pancake_app:mot_mat_khau_dai_va_ngau_nhien@db:5432/pancake_data
PANCAKE_API_KEY=key_cua_ban
```

Không gửi API key vào chat và không commit file `.env`.

Tạo API key trong Pancake POS theo tài liệu chính thức: **Cấu hình → Nâng cao →
Kết nối bên thứ 3 → Webhook - API → API Key**. Nếu tài khoản có quyền trên nhiều
shop, ưu tiên key theo tài khoản; nếu dùng key theo shop thì key đó có quyền admin
trên shop và phải được bảo vệ đặc biệt.

### 1. Build và chạy database/API

```powershell
docker compose up -d --build
docker compose ps
```

### 2. Chỉ kiểm tra key và liệt kê shop

```powershell
docker compose run --rm api python -m app.cli probe
```

Lệnh này chỉ in ID và tên shop, chưa tải đơn hàng.

### 3. Đồng bộ thử

Để giới hạn đúng một shop trong lần thử đầu, đặt trong `.env`:

```text
PANCAKE_SHOP_IDS=SHOP_ID_VUA_NHAN_DUOC
```

Sau đó chạy:

```powershell
docker compose run --rm api python -m app.cli sync
```

Kết quả trả về số bản ghi đã đọc và upsert. Chạy lại cùng dữ liệu sẽ cập nhật bản
ghi hiện có thay vì tạo bản sao.

### 4. Kiểm tra dịch vụ

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

## Điểm dừng nghiệm thu mốc 1

Chưa xây frontend trước khi trả lời được các câu hỏi sau bằng dữ liệu thật:

1. API key nhìn thấy đúng shop cần dùng.
2. Có thể lấy hết các trang đơn hàng của một shop.
3. JSON có đủ mã đơn, khách hàng, số điện thoại, sản phẩm, tổng tiền và trạng thái.
4. Có trường thời gian cập nhật để bắt được đơn cũ đổi trạng thái.
5. Chạy đồng bộ lại không tạo đơn trùng.

## Bảo mật hiện tại

- PostgreSQL và FastAPI chỉ bind vào `127.0.0.1`, chưa công khai Internet.
- API key chỉ nằm trong `.env` và được truyền vào container lúc chạy.
- Client không ghi URL request chứa API key vào log.
- Chưa có API đọc đơn hàng vì chưa triển khai authentication và phân quyền.

## Bước tiếp theo sau khi probe thành công

- Chụp mẫu response đã loại bỏ tên, SĐT, địa chỉ và API key để chốt mapping.
- Tạo schema `core` và chuẩn hóa đơn hàng/khách hàng/sản phẩm.
- Viết incremental sync dựa trên trường cập nhật thực tế của Pancake.
- Thêm đối soát số lượng và cảnh báo shop đồng bộ trễ.
- Sau đó mới làm đăng nhập, phân quyền theo shop và giao diện tra cứu.

