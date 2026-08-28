# Báo Cáo Thực Hành: Day 26 - MCP Tools Integration

**Học viên:** Nguyễn Văn An (2A202601817)  
**Môn học:** Track 3 - AI Agent Development & Model Context Protocol (MCP)  
**Repository:** `Day26-MCP-Tools-Integration`

---

## 📌 Bảng Tự Đánh Giá Kết Quả (Self-Assessment Checklist)

| Mức độ | Tiêu chí đánh giá | Trạng thái | Minh chứng / File thực thi |
|---|---|:---:|---|
| **Bài Dễ (Easy)** | MCP Server khởi động được | ✅ Đạt | `my-mcp-server/server.py` |
| | Có ít nhất 1-2 tools tự xây | ✅ Đạt | `search_logs`, `get_recent_errors`, `get_log_statistics` |
| | Tool giải quyết công việc thực tế | ✅ Đạt | Giám sát & phân tích log lỗi, tra cứu sự cố hệ thống |
| | Tool không chỉ trả dữ liệu hard-code | ✅ Đạt | Parse file log thật `data/app.log`, database `data/orders.json` |
| | MCP Client khám phá và gọi tool đúng | ✅ Đạt | `my-mcp-server/client.py` chạy thành công 100% |
| **Bài Trung Bình (Medium)** | Server chạy bằng Streamable HTTP | ✅ Đạt | Chế độ `--http` (host `0.0.0.0`, port `8088`) |
| | Authentication bằng Bearer Token | ✅ Đạt | `StaticTokenVerifier` qua `AuthSettings` |
| | Token hợp lệ gọi được tool | ✅ Đạt | Case 1: `dev-token-abc123` ➔ Thành công (200 OK) |
| | Thiếu token bị từ chối 401 | ✅ Đạt | Case 2: Missing Token ➔ 401 Unauthorized |
| | Token sai bị từ chối 401/403 | ✅ Đạt | Case 3: `wrong-token` ➔ 401/403 Forbidden |
| | Bộ test tự động Auth | ✅ Đạt | `my-mcp-server/test_auth.py` |
| **Bài Khó (Hard)** | Thay đổi format trả về của tool | ✅ Đạt | `get_order` (v1) ➔ `get_order_v2` (v2 JSON rich) |
| | Client cũ vẫn hoạt động (Backward Compat) | ✅ Đạt | Client gọi `get_order` v1 không bị lỗi |
| | Client mới dùng capability mới | ✅ Đạt | Client gọi `get_order_v2` nhận audit trail, items, customer |
| | Resource `server://info` công bố metadata | ✅ Đạt | Metadata version 2.0.0, tool catalog, deprecation flags |
| | Smart Client tự kiểm tra metadata & fallback | ✅ Đạt | `my-mcp-server/test_versioning.py` |

---

## 📂 Cấu Trúc Repository

```
Day26-MCP-Tools-Integration/
├── README.md                      ← Báo cáo tổng hợp bài nộp Day 26
├── requirements.txt               ← Thư viện phụ thuộc toàn dự án
├── .gitignore                     ← Loại trừ .env, __pycache__, credentials
│
├── my-mcp-server/                 ← [DỰ ÁN CHÍNH THỰC HÀNH DAY 26]
│   ├── server.py                  ← FastMCP Server (Tools, Resources, Auth, Versioning)
│   ├── client.py                  ← MCP Client kiểm tra stdio / streamable-http
│   ├── test_auth.py               ← Test tự động Authentication (Medium Level)
│   ├── test_versioning.py         ← Test tự động Versioning & Fallback (Hard Level)
│   ├── run_server.bat             ← Khởi động nhanh server trên Windows
│   ├── run_tests.bat              ← Chạy toàn bộ test suites
│   ├── requirements.txt           ← Requirements riêng của server
│   ├── README.md                  ← Hướng dẫn chi tiết dự án my-mcp-server
│   └── data/
│       ├── app.log                ← Log hệ thống thực tế với multi-service & stacktrace
│       └── orders.json            ← Cơ sở dữ liệu đơn hàng & audit trail
│
├── 01-function-calling/           ← Tham khảo: Function Calling thuần (Gemini SDK)
├── 02-mcp-basics/                 ← Tham khảo: MCP Server + Client cơ bản
├── 03-production/                 ← Tham khảo: Production Auth & Tool Registry
└── 04-lab/                        ← Tham khảo: Weather Agent ADK + FastMCP Remote
```

---

## 1. Use Case Thực Tế (Bước 1)

- **Công việc hiện tại:** Giám sát log hệ thống phân tán, truy vết nguyên nhân gây lỗi ứng dụng (504 Gateway Timeout, 500 Internal Error, JWT Expired, Cạn kiệt Database Connection Pool) và tra cứu đối chiếu trạng thái đơn hàng bị gián đoạn.
- **Cách làm thủ công trước đây:**
  1. Mở file log bằng text editor hoặc dùng terminal gõ lệnh `grep` / `tail -n 100`.
  2. Đọc thủ công từng dòng stack trace để tìm mã lỗi và service liên quan.
  3. Copy `order_id` từ log lỗi, sau đó mở phần mềm quản lý hoặc database tra cứu lại thông tin đơn hàng và khách hàng.
- **Input:** Từ khoá tìm kiếm, log level (`INFO`, `WARN`, `ERROR`, `CRITICAL`), khoảng thời gian / limit, mã `order_id`.
- **Output:**
  - Danh sách log trích xuất có cấu trúc (timestamp, level, service, message, stacktrace).
  - Thống kê tình trạng sức khoẻ hệ thống (Health Status, tổng số lỗi theo service/level).
  - Chi tiết đơn hàng và lịch sử kiểm toán giao dịch (audit trail).

---

## 2. Thiết Kế MCP Tools & Resources (Bước 2)

Hệ thống cung cấp 5 MCP Tools và 2 MCP Resources thực hiện tác vụ trên dữ liệu thật (`data/app.log` và `data/orders.json`):

### Danh sách Tools:
1. `search_logs(keyword: str, level: str = "ALL", limit: int = 50)`: Tìm kiếm log linh hoạt theo từ khóa và cấp độ.
2. `get_recent_errors(limit: int = 10, service: str = "ALL")`: Trích xuất danh sách các lỗi ERROR/CRITICAL mới nhất kèm stack trace.
3. `get_log_statistics(hours: int = 24)`: Thống kê số lượng log, phân loại theo level và tổng hợp tỷ lệ lỗi theo service.
4. `get_order(order_id: str)` *(v1)*: Tra cứu thông tin đơn hàng cơ bản (giữ nguyên cho legacy clients).
5. `get_order_v2(order_id: str, include_audit_trail: bool = False, format: str = "json")` *(v2)*: Tra cứu thông tin đơn hàng nâng cao, hỗ trợ audit trail và phân tích trạng thái thanh toán.

### Danh sách Resources:
1. `server://info`: Cung cấp metadata server version (`2.0.0`), danh mục tools, trạng thái deprecation và migration notes.
2. `logs://recent`: Cho phép agent đọc trực tiếp 20 dòng log mới nhất theo thời gian thực.

---

## 3. Cài Đặt và Khởi Động MCP Server (Bước 3)

```bash
cd my-mcp-server
pip install -r requirements.txt

# Chế độ Stdio (Dùng cho Claude Code / Claude Desktop / Subprocess)
python server.py

# Chế độ Streamable HTTP (Dùng cho Web Client / Remote Agent / Auth testing)
python server.py --http
```

---

## 4. Tích Hợp với Claude Code & Client (Bước 4)

### Đăng ký MCP Server vào Claude Code:
```bash
# Đăng ký dạng stdio
claude mcp add incident-log-order-server python "d:/LAB_VINUNI/26/Day26-2A202601817-NguyenVanAn/my-mcp-server/server.py"

# Đăng ký dạng HTTP với Authentication token
claude mcp add incident-log-order-server-http http://localhost:8088/mcp --header "Authorization: Bearer dev-token-abc123"
```

### Câu hỏi thử nghiệm bằng ngôn ngữ tự nhiên:
- *"Tìm giúp tôi 5 lỗi gần nhất của service payment-gateway trong log."*
- *"Hệ thống có lỗi CRITICAL nào liên quan đến database không?"*
- *"Tổng hợp tình hình log và cho biết service nào đang bị lỗi nhiều nhất."*
- *"Tra cứu thông tin chi tiết đơn hàng ORD-2026-003 xem vì sao bị thất bại."*

Luồng hoạt động chuẩn Model Context Protocol:
```
User (Ngôn ngữ tự nhiên) 
   │
   ▼
Claude Code (LLM quyết định gọi search_logs / get_recent_errors / get_order_v2)
   │
   ▼
MCP Client ───[Model Context Protocol]───► FastMCP Server (my-mcp-server)
   │                                              │
   ◄────────── Kết quả JSON / cấu trúc ───────────┘
   ▼
Claude Code tổng hợp câu trả lời thông minh cho User
```

---

## 5. Xác Thực Authentication - Mức Độ Trung Bình (Bước 5)

Server hỗ trợ xác thực Bearer Token thông qua `TokenVerifier`:
- Endpoint: `http://localhost:8088/mcp`
- Header: `Authorization: Bearer <TOKEN>`
- Tokens: `dev-token-abc123`, `admin-token-secret888`

### Kiểm thử tự động với `test_auth.py`:
```bash
# Chạy server ở terminal 1:
python my-mcp-server/server.py --http

# Chạy test ở terminal 2:
python my-mcp-server/test_auth.py
```
**Kết quả thực tế:**
- `[TEST 1]` Token hợp lệ (`dev-token-abc123`): ✅ **PASSED (200 OK, lấy được danh sách tool & gọi tool thành công)**
- `[TEST 2]` Không truyền token: ✅ **PASSED (Bị từ chối 401 Unauthorized)**
- `[TEST 3]` Truyền sai token (`wrong-token-hacker999`): ✅ **PASSED (Bị từ chối 401/403 Forbidden)**

---

## 6. Versioning & Backward Compatibility - Mức Độ Khó (Bước 6)

### So sánh format trả về giữa v1 và v2:
- **v1 (`get_order` - Legacy):**
  ```json
  {
    "id": "ORD-2026-001",
    "status": "COMPLETED",
    "customer": "Nguyen Van A",
    "total": 450000
  }
  ```
- **v2 (`get_order_v2` - Rich Format):**
  ```json
  {
    "api_version": "2.0.0",
    "order_id": "ORD-2026-001",
    "found": true,
    "status": "COMPLETED",
    "customer": {
      "customer_id": "CUST-881",
      "name": "Nguyen Van A",
      "email": "nguyenvana@example.com",
      "phone": "+84912345678"
    },
    "items": [
      {
        "product_id": "PROD-SKU-01",
        "name": "Bàn phím cơ không dây",
        "quantity": 1,
        "price": 450000
      }
    ],
    "total_amount": 450000,
    "currency": "VND",
    "payment_method": "VNPAY",
    "transaction_id": "TXN-998812",
    "created_at": "2026-08-28T08:02:45+07:00",
    "updated_at": "2026-08-28T08:03:16+07:00",
    "audit_trail": [
      {
        "timestamp": "2026-08-28T08:02:45+07:00",
        "action": "ORDER_CREATED",
        "performed_by": "user:USR-1001",
        "details": "Order placed via Web Checkout"
      },
      {
        "timestamp": "2026-08-28T08:03:15+07:00",
        "action": "PAYMENT_CONFIRMED",
        "performed_by": "system:payment-gateway",
        "details": "Payment success with VNPAY TXN-998812"
      }
    ]
  }
  ```

### Cơ chế Versioning & Resource `server://info`:
1. Server công bố resource `server://info` chứa metadata version (`2.0.0`) và danh mục các tools (`get_order` v1.0.0 deprecated, `get_order_v2` v2.0.0 active).
2. Client cũ gọi `get_order` vẫn hoạt động 100% không bị lỗi.
3. Client mới đọc `server://info`, phát hiện server hỗ trợ `get_order_v2` sẽ ưu tiên gọi tool mới. Nếu server cũ chỉ có `get_order`, client sẽ tự động fallback mà không làm crash ứng dụng.

### Kiểm thử tự động với `test_versioning.py`:
```bash
python my-mcp-server/test_versioning.py
```
**Kết quả kiểm thử:**
- Đọc resource `server://info` thành công.
- Client cũ gọi `get_order` v1 nhận đúng format cũ.
- Client mới gọi `get_order_v2` nhận đủ audit trail và payload mở rộng.
- Smart Client chọn đúng tool theo capability và fallback an toàn.

---

## 7. Lý Thuyết: Phân Biệt MCP và Function Calling

| Tiêu chí | Function Calling | Model Context Protocol (MCP) |
|---|---|---|
| **Bản chất** | Khả năng của mô hình (Model capability) | Giao thức giao tiếp client–server chuẩn hoá |
| **Ai định nghĩa tool?** | Viết trực tiếp trong từng ứng dụng | Server tự công bố (self-describing) |
| **Khả năng tái sử dụng** | Phải copy code và schema cho từng app | Viết 1 lần, mọi MCP client (Claude Code, Desktop, Cursor) đều cắm vào dùng ngay |
| **Nơi thực thi** | Ứng dụng AI tự chạy | MCP Server riêng biệt thực thi |
| **Bảo mật & Phân tán** | Khó quản lý phân tán | Hỗ trợ Streamable HTTP, Bearer Auth, Scopes |

---

## 8. Hướng Dẫn Tự Kiểm Tra & Xử Lý Lỗi (Troubleshooting)

| Vấn đề thường gặp | Nguyên nhân | Cách khắc phục |
|---|---|---|
| `Claude Code không thấy Server` | Đường dẫn file hoặc môi trường python chưa đúng | Dùng đường dẫn tuyệt đối đến file `server.py` |
| `Claude Code thấy Server nhưng không thấy Tool` | Thiếu decorator `@mcp.tool()` hoặc lỗi syntax | Kiểm tra docstrings, type hints và decorator |
| `HTTP client không kết nối được` | Sai port hoặc firewall chặn | Đảm bảo server bind `0.0.0.0` và port không bị trùng (mặc định `8088`) |
| `401 Unauthorized khi gọi tool qua HTTP` | Thiếu hoặc sai định dạng header Authorization | Thêm header đúng chuẩn: `Authorization: Bearer dev-token-abc123` |
| `Client cũ bị hỏng khi cập nhật tool` | Đổi tên hoặc xoá field của v1 | Giữ nguyên tool v1, tạo tool v2 song song và bổ sung tham số optional có default value |

---

## 9. Cam Kết An Toàn & Bảo Mật (Security Compliance)

- Toàn bộ code trong repository **không chứa API Key thật, Private Key, Secret hoặc Passwords**.
- File `.gitignore` đã cấu hình để loại trừ `.env`, `.venv/`, `__pycache__/` và các file tạm.
- Các token trong code (`dev-token-abc123`, `admin-token-secret888`) là token giả lập cho môi trường dev/lab.
