"""Incident Diagnostics & Order Management MCP Server.

Cung cấp các công cụ và tài nguyên cho AI Agents (Claude Code, Claude Desktop, Cursor, ADK):
  - Khám phá & tra cứu log hệ thống (search_logs, get_recent_errors, get_log_statistics)
  - Quản lý & tra cứu đơn hàng / sự cố (get_order v1, get_order_v2)
  - Bảo mật bằng Bearer Token qua Streamable HTTP
  - Hỗ trợ Versioning, Backward Compatibility & Resource metadata (server://info)
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

# ── Paths & Configurations ───────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOG_FILE_PATH = DATA_DIR / "app.log"
ORDERS_FILE_PATH = DATA_DIR / "orders.json"

SERVER_NAME = "incident-log-order-server"
SERVER_VERSION = "2.0.0"
PORT = int(os.environ.get("PORT", "8088"))
HOST = os.environ.get("HOST", "0.0.0.0")

# ── Token Store for Streamable HTTP Auth ──────────────────────────────
# In production: replace with DB lookup, JWT verification, or OAuth 2.0
VALID_TOKENS: dict[str, str] = {
    os.environ.get("MCP_AUTH_TOKEN", "dev-token-abc123"): "dev-engineer",
    "admin-token-secret888": "sec-ops-admin",
}


class StaticTokenVerifier(TokenVerifier):
    """Xác thực Bearer token cho MCP Server theo chuẩn Model Context Protocol."""

    async def verify_token(self, token: str) -> AccessToken | None:
        client_id = VALID_TOKENS.get(token)
        if client_id is None:
            return None
        return AccessToken(
            token=token,
            client_id=client_id,
            scopes=["logs:read", "orders:read", "orders:manage"],
        )


# ── Initialize FastMCP Server ─────────────────────────────────────────
mcp = FastMCP(
    SERVER_NAME,
    host=HOST,
    port=PORT,
    instructions=(
        f"Server {SERVER_NAME} v{SERVER_VERSION}. "
        "Chuyên dụng cho DevOps & Support: Tra cứu log hệ thống, phát hiện lỗi và tra cứu chi tiết đơn hàng."
    ),
    auth=AuthSettings(
        issuer_url=f"http://localhost:{PORT}",
        resource_server_url=f"http://localhost:{PORT}",
    ),
    token_verifier=StaticTokenVerifier(),
)


# ── Helper Utilities ──────────────────────────────────────────────────
def _ensure_data_files() -> None:
    """Tạo thư mục data và file mẫu nếu chưa tồn tại."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not LOG_FILE_PATH.exists():
        LOG_FILE_PATH.write_text(
            "2026-08-28 08:00:00 [INFO] [system] System initialized.\n",
            encoding="utf-8",
        )
    if not ORDERS_FILE_PATH.exists():
        ORDERS_FILE_PATH.write_text("{}", encoding="utf-8")


def _read_orders_db() -> dict[str, Any]:
    """Đọc dữ liệu đơn hàng từ file JSON."""
    _ensure_data_files()
    try:
        with open(ORDERS_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {}


# ── MCP Tools (Phục vụ truy vết Log & Incident) ───────────────────────


@mcp.tool()
def search_logs(
    keyword: str,
    level: str = "ALL",
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Tìm kiếm các dòng log trong hệ thống theo từ khóa và cấp độ log.

    Args:
        keyword: Từ khoá cần tìm (ví dụ: 'timeout', 'USR-1001', 'ORD-2026-002', 'database')
        level: Cấp độ log cần lọc ('ALL', 'INFO', 'WARN', 'ERROR', 'CRITICAL')
        limit: Số lượng dòng log tối đa trả về (mặc định: 50)
    """
    _ensure_data_files()
    results: list[dict[str, Any]] = []
    log_pattern = re.compile(
        r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+\[(\w+)\]\s+\[([\w\-]+)\]\s+(.*)$"
    )

    norm_keyword = keyword.strip().lower()
    norm_level = level.strip().upper()

    current_entry: dict[str, Any] | None = None

    with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.rstrip("\r\n")
            match = log_pattern.match(line_str)

            if match:
                # Nếu đã có entry trước đó, kiểm tra và đẩy vào results
                if current_entry is not None:
                    full_text = f"{current_entry['raw']} {' '.join(current_entry.get('stack_trace', []))}".lower()
                    level_match = norm_level == "ALL" or current_entry["level"] == norm_level
                    keyword_match = not norm_keyword or norm_keyword in full_text
                    if level_match and keyword_match:
                        results.append(current_entry)
                        if len(results) >= limit:
                            return results

                timestamp, log_lvl, service, message = match.groups()
                current_entry = {
                    "timestamp": timestamp,
                    "level": log_lvl.upper(),
                    "service": service,
                    "message": message,
                    "raw": line_str,
                    "stack_trace": [],
                }
            elif current_entry is not None:
                # Dòng nối tiếp (stack trace)
                current_entry["stack_trace"].append(line_str)

    # Đẩy entry cuối cùng
    if current_entry is not None:
        full_text = f"{current_entry['raw']} {' '.join(current_entry.get('stack_trace', []))}".lower()
        level_match = norm_level == "ALL" or current_entry["level"] == norm_level
        keyword_match = not norm_keyword or norm_keyword in full_text
        if level_match and keyword_match:
            results.append(current_entry)

    return results[:limit]


@mcp.tool()
def get_recent_errors(
    limit: int = 10,
    service: str = "ALL",
) -> list[dict[str, Any]]:
    """Lấy danh sách các lỗi (ERROR hoặc CRITICAL) mới nhất phát sinh trong hệ thống.

    Args:
        limit: Số lượng lỗi cần lấy (mặc định: 10)
        service: Lọc theo service cụ thể ('ALL' hoặc tên service như 'payment-gateway', 'auth-service')
    """
    _ensure_data_files()
    errors: list[dict[str, Any]] = []
    norm_service = service.strip().lower()

    # Tìm toàn bộ ERROR và CRITICAL
    all_errors = search_logs(keyword="", level="ALL", limit=1000)
    for entry in all_errors:
        if entry["level"] in ("ERROR", "CRITICAL"):
            if norm_service == "all" or entry["service"].lower() == norm_service:
                errors.append(entry)

    # Trả về các lỗi mới nhất (đảo ngược thứ tự)
    errors.reverse()
    return errors[:limit]


@mcp.tool()
def get_log_statistics(hours: int = 24) -> dict[str, Any]:
    """Thống kê tổng quan tình trạng log, phân loại theo level và service.

    Args:
        hours: Khung thời gian thống kê tính theo giờ (mặc định: 24h)
    """
    _ensure_data_files()
    logs = search_logs(keyword="", level="ALL", limit=5000)

    stats_by_level: dict[str, int] = {"INFO": 0, "WARN": 0, "ERROR": 0, "CRITICAL": 0}
    stats_by_service: dict[str, dict[str, int]] = {}

    for entry in logs:
        lvl = entry["level"]
        svc = entry["service"]

        stats_by_level[lvl] = stats_by_level.get(lvl, 0) + 1

        if svc not in stats_by_service:
            stats_by_service[svc] = {"total": 0, "errors": 0}
        stats_by_service[svc]["total"] += 1
        if lvl in ("ERROR", "CRITICAL"):
            stats_by_service[svc]["errors"] += 1

    return {
        "summary": {
            "total_logs": len(logs),
            "total_errors": stats_by_level.get("ERROR", 0) + stats_by_level.get("CRITICAL", 0),
            "health_status": "DEGRADED" if (stats_by_level.get("CRITICAL", 0) > 0) else "HEALTHY",
        },
        "by_level": stats_by_level,
        "by_service": stats_by_service,
        "report_generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ── MCP Tools (Phục vụ Versioning & Backward Compatibility) ───────────


@mcp.tool()
def get_order(order_id: str) -> dict[str, Any]:
    """[v1 Legacy] Tra cứu thông tin cơ bản của đơn hàng.

    LƯU Ý: Tool này ở phiên bản 1.0.0 (giữ nguyên cho backward compatibility).
    Khuyến nghị các client mới sử dụng 'get_order_v2'.

    Args:
        order_id: Mã đơn hàng (ví dụ: 'ORD-2026-001')
    """
    db = _read_orders_db()
    order = db.get(order_id)
    if not order:
        return {
            "id": order_id,
            "status": "NOT_FOUND",
            "error": f"Không tìm thấy đơn hàng {order_id}",
        }

    # Format trả về phiên bản cũ (v1) — cấu trúc gọn nhẹ
    return {
        "id": order["order_id"],
        "status": order["status"],
        "customer": order["customer"]["name"],
        "total": order["total_amount"],
    }


@mcp.tool()
def get_order_v2(
    order_id: str,
    include_audit_trail: bool = False,
    format: str = "json",
) -> dict[str, Any]:
    """[v2 Rich] Tra cứu thông tin chi tiết toàn diện của đơn hàng kèm lịch sử kiểm toán.

    Args:
        order_id: Mã đơn hàng (ví dụ: 'ORD-2026-001', 'ORD-2026-002')
        include_audit_trail: Có bao gồm lịch sử các bước xử lý không (mặc định: False)
        format: Định dạng dữ liệu ('json' hoặc 'summary')
    """
    db = _read_orders_db()
    order = db.get(order_id)
    if not order:
        return {
            "api_version": "2.0.0",
            "order_id": order_id,
            "found": False,
            "error": f"Order {order_id} does not exist in the database.",
        }

    response: dict[str, Any] = {
        "api_version": "2.0.0",
        "order_id": order["order_id"],
        "found": True,
        "status": order["status"],
        "customer": order["customer"],
        "items": order["items"],
        "total_amount": order["total_amount"],
        "currency": order.get("currency", "VND"),
        "payment_method": order.get("payment_method"),
        "transaction_id": order.get("transaction_id"),
        "created_at": order.get("created_at"),
        "updated_at": order.get("updated_at"),
    }

    if include_audit_trail:
        response["audit_trail"] = order.get("audit_trail", [])

    return response


# ── MCP Resources ─────────────────────────────────────────────────────


@mcp.resource("server://info")
def server_info() -> str:
    """Cung cấp metadata, version và danh mục capabilities của server."""
    metadata = {
        "name": SERVER_NAME,
        "version": SERVER_VERSION,
        "capabilities": {
            "logging": ["search_logs", "get_recent_errors", "get_log_statistics"],
            "orders": ["get_order", "get_order_v2"],
        },
        "tools": {
            "get_order": {
                "version": "1.0.0",
                "deprecated": True,
                "replacement": "get_order_v2",
                "notes": "Returns basic payload {id, status, customer, total}",
            },
            "get_order_v2": {
                "version": "2.0.0",
                "deprecated": False,
                "features": ["audit_trail", "customer_details", "line_items"],
            },
            "search_logs": {"version": "1.0.0", "deprecated": False},
            "get_recent_errors": {"version": "1.0.0", "deprecated": False},
            "get_log_statistics": {"version": "1.0.0", "deprecated": False},
        },
        "auth": {
            "type": "bearer_token",
            "header": "Authorization: Bearer <token>",
            "test_tokens": ["dev-token-abc123", "admin-token-secret888"],
        },
    }
    return json.dumps(metadata, ensure_ascii=False, indent=2)


@mcp.resource("logs://recent")
def recent_logs_resource() -> str:
    """Tài nguyên xem trực tiếp 20 dòng log mới nhất."""
    _ensure_data_files()
    try:
        with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return "".join(lines[-20:])
    except Exception as e:
        return f"Error reading logs: {e}"


# ── Server Entrypoint ─────────────────────────────────────────────────
if __name__ == "__main__":
    _ensure_data_files()

    is_http_mode = "--http" in sys.argv or os.environ.get("MCP_TRANSPORT") == "streamable-http"

    if is_http_mode:
        import socket

        def is_port_in_use(p: int) -> bool:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(("127.0.0.1", p)) == 0

        target_port = PORT
        while is_port_in_use(target_port) and target_port < PORT + 20:
            print(f"⚠️ Cổng {target_port} đang bận, tự động thử cổng tiếp theo ({target_port + 1})...")
            target_port += 1

        # Cập nhật cấu hình port vào FastMCP settings
        mcp.settings.host = HOST
        mcp.settings.port = target_port
        if mcp.auth:
            mcp.auth.issuer_url = f"http://localhost:{target_port}"
            mcp.auth.resource_server_url = f"http://localhost:{target_port}"

        print(f"🚀 Starting {SERVER_NAME} v{SERVER_VERSION} on Streamable HTTP transport...")
        print(f"📍 URL: http://{HOST}:{target_port}/mcp")
        print("🔐 Authentication: Bearer Token Enabled")
        print("   Valid tokens: 'dev-token-abc123', 'admin-token-secret888'")
        mcp.run(transport="streamable-http")
    else:
        # Default: stdio mode for Claude Code / Claude Desktop
        mcp.run()
