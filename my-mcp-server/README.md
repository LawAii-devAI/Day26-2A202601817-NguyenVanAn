# Incident Diagnostics & Order Management MCP Server

MCP Server chuyên dụng giải quyết bài toán thực tế: **Giám sát Log hệ thống, chẩn đoán lỗi phân tán và tra cứu thông tin đơn hàng/giao dịch liên quan**.

Dự án được xây dựng trên nền tảng **FastMCP** (chuẩn **Model Context Protocol** của Anthropic), hỗ trợ đầy đủ các yêu cầu từ mức độ **Dễ (Easy)**, **Trung bình (Medium - Authentication)** đến **Khó (Hard - Versioning & Backward Compatibility)**.

---

## 📑 Mục lục
1. [Bước 1 - Use Case Thực Tế](#bước-1---use-case-thực-tế)
2. [Bước 2 - Thiết Kế MCP Tools & Resources](#bước-2---thiết-kế-mcp-tools--resources)
3. [Bước 3 - Cài Đặt & Chạy MCP Server](#bước-3---cài-đặt--chạy-mcp-server)
4. [Bước 4 - Tích Hợp Claude Code & Claude Desktop](#bước-4---tích-hợp-claude-code--claude-desktop)
5. [Bước 5 - Authentication (Mức độ Trung bình)](#bước-5---authentication-mức-độ-trung-bình)
6. [Bước 6 - Versioning & Backward Compatibility (Mức độ Khó)](#bước-6---versioning--backward-compatibility-mức-độ-khó)
7. [Bước 7 - Kiểm Thử Tự Động Toàn Diện](#bước-7---kiểm-thử-tự-động-toàn-diện)

---

## Bước 1 - Use Case Thực Tế

- **Công việc hiện tại:** Hằng ngày kỹ sư DevOps, Backend Developer và Support Team phải liên tục kiểm tra các file log hệ thống (`app.log`) để phát hiện các ngoại lệ (Exception), lỗi timeout cổng thanh toán, cạn kiệt kết nối cơ sở dữ liệu, lỗi xác thực JWT, và kiểm tra thông tin đơn hàng / khách hàng bị ảnh hưởng.
- **Cách làm thủ công trước đây:** 
  1. Mở file log hàng nghìn dòng bằng text editor hoặc dùng các lệnh `grep`, `findstr`, `tail -n 100`.
  2. Tự đọc stack trace để đoán service và nguyên nhân lỗi.
  3. Copy `order_id` hoặc `user_id` từ log lỗi, sau đó mở cơ sở dữ liệu hoặc công cụ admin tra cứu thủ công tình trạng đơn hàng.
- **Input:** Từ khoá tìm kiếm, log level (`INFO`, `WARN`, `ERROR`, `CRITICAL`), khoảng thời gian / limit, mã `order_id`.
- **Output:** 
  - Danh sách log/lỗi có cấu trúc (timestamp, level, service, message, stack trace chi tiết).
  - Báo cáo thống kê tần suất lỗi theo từng service.
  - Chi tiết đơn hàng, khách hàng, sản phẩm và lịch sử xử lý (audit trail).

---

## Bước 2 - Thiết Kế MCP Tools & Resources

Tất cả các tool đều thao tác trên **dữ liệu thực tế** (`data/app.log` và `data/orders.json`), tự động phân tích cú pháp (regex parsing, JSON validation) chứ không trả dữ liệu hard-code cố định.

### 1. Danh sách MCP Tools

| Tool | Mô tả | Tham số đầu vào (Input) | Kết quả đầu ra (Output) |
|---|---|---|---|
| `search_logs` | Tìm kiếm log theo từ khóa và cấp độ | `keyword: str`, `level: str = "ALL"`, `limit: int = 50` | `list[dict]` chứa timestamp, level, service, message, stack_trace |
| `get_recent_errors` | Trích xuất các lỗi ERROR & CRITICAL mới nhất | `limit: int = 10`, `service: str = "ALL"` | `list[dict]` các lỗi mới nhất được parse chi tiết |
| `get_log_statistics` | Thống kê số lượng log theo cấp độ và service | `hours: int = 24` | `dict` tổng quan health status, số lỗi theo level và theo service |
| `get_order` *(v1)* | Tra cứu đơn hàng cơ bản (Legacy client) | `order_id: str` | `dict` `{id, status, customer, total}` |
| `get_order_v2` *(v2)* | Tra cứu đơn hàng chi tiết kèm audit trail | `order_id: str`, `include_audit_trail: bool = False`, `format: str = "json"` | `dict` `{api_version, order_id, status, customer, items, total_amount, audit_trail}` |

### 2. Danh sách MCP Resources

- `server://info`: Cung cấp metadata server (`version: "2.0.0"`), danh mục tool v1 & v2, ghi chú deprecation và migration guide.
- `logs://recent`: Trả về 20 dòng log mới nhất theo thời gian thực.

---

## Bước 3 - Cài Đặt & Chạy MCP Server

### Cài đặt môi trường
```bash
pip install -r requirements.txt
```

### Chạy Server ở chế độ Stdio (Mặc định cho Claude Code / Subprocess)
```bash
python server.py
```

### Chạy Server ở chế độ Streamable HTTP (Hỗ trợ Remote & Authentication)
```bash
python server.py --http
# Hoặc chạy script nhanh trên Windows: run_server.bat
```
Server sẽ lắng nghe tại: `http://localhost:8088/mcp`

---

## Bước 4 - Tích Hợp Claude Code & Claude Desktop

### Cách 1: Đăng ký qua Claude Code CLI
```bash
# Thêm MCP server ở chế độ stdio
claude mcp add incident-log-order-server python "d:/LAB_VINUNI/26/Day26-2A202601817-NguyenVanAn/my-mcp-server/server.py"

# Hoặc thêm MCP server qua Streamable HTTP
claude mcp add incident-log-order-server-http http://localhost:8088/mcp --header "Authorization: Bearer dev-token-abc123"
```

### Cách 2: Cấu hình qua file JSON (`.claude.json` hoặc `claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "incident-log-order-server": {
      "command": "python",
      "args": [
        "d:/LAB_VINUNI/26/Day26-2A202601817-NguyenVanAn/my-mcp-server/server.py"
      ]
    },
    "incident-log-order-server-http": {
      "url": "http://localhost:8088/mcp",
      "headers": {
        "Authorization": "Bearer dev-token-abc123"
      }
    }
  }
}
```

### Thử nghiệm bằng câu hỏi tự nhiên (Natural Language Prompts):
Sau khi đăng ký, bạn có thể hỏi Claude Code bằng ngôn ngữ tự nhiên:
- *"Tìm giúp tôi 5 lỗi gần nhất trong log của service payment-gateway."*
- *"Kiểm tra xem hệ thống có lỗi nào nghiêm trọng (CRITICAL) trong database không?"*
- *"Thống kê tình trạng sức khoẻ log toàn hệ thống."*
- *"Tra cứu thông tin đơn hàng ORD-2026-002 và cho tôi biết tại sao đơn này bị lỗi thanh toán."*

---

## Bước 5 - Authentication (Mức độ Trung bình)

Server triển khai lớp xác thực `TokenVerifier` trên nền tảng **Streamable HTTP**:
- Header bắt buộc: `Authorization: Bearer <TOKEN>`
- Danh sách token hợp lệ:
  - `dev-token-abc123` (Role: dev-engineer)
  - `admin-token-secret888` (Role: sec-ops-admin)

### Kiểm thử tự động với `test_auth.py`
Khởi động server HTTP ở terminal 1 (`python server.py --http`), sau đó chạy ở terminal 2:
```bash
python test_auth.py
```
Kết quả kiểm thử 3 kịch bản bảo mật:
1. **Valid Token (`dev-token-abc123`)** ➔ `200 OK`, kết nối và gọi tool thành công.
2. **Missing Token (Không truyền header)** ➔ Bị từ chối với lỗi `401 Unauthorized`.
3. **Invalid Token (`wrong-token-hacker999`)** ➔ Bị từ chối với lỗi `401/403 Forbidden`.

---

## Bước 6 - Versioning & Backward Compatibility (Mức độ Khó)

Khi nâng cấp format dữ liệu trả về cho đơn hàng, server áp dụng nguyên tắc **Zero Breaking Changes**:
1. **Giữ nguyên tool v1 (`get_order`)**: Trả về payload dạng phẳng `{id, status, customer, total}` dành cho các client cũ.
2. **Tạo tool mới v2 (`get_order_v2`)**: Bổ sung các tham số optional (`include_audit_trail`, `format`) và trả về JSON cấu trúc chi tiết bao gồm customer object, line items, transaction id, audit trail.
3. **Công bố Metadata qua `server://info`**:
   Client mới đọc resource `server://info` để kiểm tra version và danh mục tools trước khi quyết định gọi:
   - Nếu có `get_order_v2` và chưa bị deprecated ➔ Gọi `get_order_v2`.
   - Nếu chỉ có `get_order` v1 ➔ Tự động fallback về `get_order` v1.

### Kiểm thử tự động với `test_versioning.py`
```bash
python test_versioning.py
```

---

## Bước 7 - Kiểm Thử Tự Động Toàn Diện

Bạn có thể chạy toàn bộ các bài test bằng file batch:
```bash
run_tests.bat
```
Hoặc chạy từng script riêng:
1. `python client.py` — Kiểm tra toàn bộ tools và resources cơ bản.
2. `python test_versioning.py` — Kiểm tra versioning, compatibility và smart fallback.
3. `python test_auth.py` — Kiểm tra 3 kịch bản Authentication.
