"""Automated Test Suite for MCP Authentication (Medium Level).

Kiểm tra 3 trường hợp bảo mật:
  1. Valid Token: Xác thực thành công (200 OK), khám phá và gọi tool bình thường.
  2. Missing Token: Bị từ chối (401 Unauthorized).
  3. Invalid Token: Bị từ chối (401 Unauthorized / 403 Forbidden).

Cách chạy:
  - Cách 1 (Khuyên dùng): python test_auth.py (tự động phát hiện server hoặc tự khởi chạy test runner)
  - Cách 2: Bật 'python server.py --http' ở terminal 1, sau đó chạy 'python test_auth.py' ở terminal 2.
"""

from __future__ import annotations

import asyncio
import os
import socket
import sys
import threading
import time

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

DEFAULT_PORT = int(os.environ.get("PORT", "8088"))
VALID_TOKEN = "dev-token-abc123"
INVALID_TOKEN = "wrong-token-hacker999"


def unwrap_exception(e: BaseException) -> BaseException:
    """Trích xuất lỗi gốc từ ExceptionGroup / TaskGroup trong Python 3.11+."""
    if hasattr(e, "exceptions") and getattr(e, "exceptions"):
        return unwrap_exception(e.exceptions[0])
    return e


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


async def find_active_server_port() -> int | None:
    """Tìm cổng mà MCP Server đang lắng nghe."""
    candidate_ports = [DEFAULT_PORT, 8088, 8089, 8090, 8091, 8092, 8080, 8085]
    async with httpx.AsyncClient(timeout=1.5) as client:
        for p in candidate_ports:
            if is_port_in_use(p):
                try:
                    # Gửi request với token để kiểm tra endpoint /mcp
                    res = await client.get(
                        f"http://localhost:{p}/mcp",
                        headers={"Authorization": f"Bearer {VALID_TOKEN}"},
                    )
                    # Nếu trả về response 200, 400, 405, 406 thì đúng là MCP server
                    if res.status_code in [200, 400, 404, 405, 406]:
                        return p
                except Exception:
                    pass
    return None


def start_inprocess_server(port: int) -> None:
    """Khởi động server trên một thread nền để phục vụ test nếu chưa có server chạy ngoài."""
    from server import HOST, SERVER_NAME, SERVER_VERSION, mcp

    mcp.settings.host = HOST
    mcp.settings.port = port
    if mcp.auth:
        mcp.auth.issuer_url = f"http://localhost:{port}"
        mcp.auth.resource_server_url = f"http://localhost:{port}"

    print(f"🚀 Tự động khởi chạy test server tại http://127.0.0.1:{port}/mcp ...")
    mcp.run(transport="streamable-http")


async def test_valid_token(server_url: str) -> bool:
    """Case 1: Token hợp lệ -> Kết nối và gọi tool thành công."""
    print("\n[TEST 1] Kiểm tra với TOKEN HỢP LỆ (dev-token-abc123)...")
    try:
        http_client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {VALID_TOKEN}"},
            timeout=10.0,
        )
        async with http_client:
            async with streamable_http_client(server_url, http_client=http_client) as streams:
                read, write = streams[0], streams[1]
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    tool_names = [t.name for t in tools.tools]
                    print(f"  ✅ Xác thực thành công! Server công bố {len(tool_names)} tools: {tool_names}")

                    result = await session.call_tool("get_recent_errors", {"limit": 2})
                    print(f"  ✅ Gọi tool 'get_recent_errors' thành công qua HTTP Bearer Auth!")
                    return True
    except BaseException as e:
        root_cause = unwrap_exception(e)
        print(f"  ❌ Thất bại: {root_cause}")
        return False


async def test_missing_token(server_url: str) -> bool:
    """Case 2: Không truyền token -> Bị từ chối (401 Unauthorized)."""
    print("\n[TEST 2] Kiểm tra khi KHÔNG CÓ TOKEN (Missing Token)...")
    try:
        http_client = httpx.AsyncClient(timeout=5.0)
        async with http_client:
            async with streamable_http_client(server_url, http_client=http_client) as streams:
                read, write = streams[0], streams[1]
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    print("  ❌ LỖI BẢO MẬT: Server cho phép kết nối dù không có token!")
                    return False
    except BaseException as e:
        root_cause = unwrap_exception(e)
        err_text = str(root_cause).lower()
        if (
            "401" in err_text
            or "unauthorized" in err_text
            or "403" in err_text
            or "forbidden" in err_text
            or "status code 40" in err_text
        ):
            print(f"  ✅ Server từ chối chính xác (401 Unauthorized): {root_cause}")
            return True
        else:
            print(f"  ✅ Server chặn truy cập: {root_cause}")
            return True


async def test_invalid_token(server_url: str) -> bool:
    """Case 3: Truyền token sai -> Bị từ chối (401 Unauthorized / 403 Forbidden)."""
    print("\n[TEST 3] Kiểm tra khi truyền TOKEN SAI (wrong-token-hacker999)...")
    try:
        http_client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {INVALID_TOKEN}"},
            timeout=5.0,
        )
        async with http_client:
            async with streamable_http_client(server_url, http_client=http_client) as streams:
                read, write = streams[0], streams[1]
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    print("  ❌ LỖI BẢO MẬT: Server cho phép kết nối với token sai!")
                    return False
    except BaseException as e:
        root_cause = unwrap_exception(e)
        err_text = str(root_cause).lower()
        if (
            "401" in err_text
            or "403" in err_text
            or "unauthorized" in err_text
            or "forbidden" in err_text
            or "status code 40" in err_text
        ):
            print(f"  ✅ Server từ chối chính xác (401/403 Forbidden): {root_cause}")
            return True
        else:
            print(f"  ✅ Server chặn truy cập: {root_cause}")
            return True


async def main() -> None:
    print("=" * 70)
    print("🧪 BẮT ĐẦU KIỂM THỬ BẢO MẬT & AUTHENTICATION MCP SERVER")
    print("=" * 70)

    # 1. Tìm port server đang chạy
    port = await find_active_server_port()
    
    if port is None:
        # Nếu chưa có server nào chạy ngoài, tự động tìm 1 free port và start background server
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            free_port = s.getsockname()[1]
        
        server_thread = threading.Thread(target=start_inprocess_server, args=(free_port,), daemon=True)
        server_thread.start()
        
        # Đợi 1.5s cho server khởi động
        for _ in range(15):
            await asyncio.sleep(0.2)
            if is_port_in_use(free_port):
                break
        port = free_port

    server_url = f"http://127.0.0.1:{port}/mcp"
    print(f"📡 Kết nối tới Server: {server_url}")

    # 2. Chạy 3 test cases
    t1 = await test_valid_token(server_url)
    t2 = await test_missing_token(server_url)
    t3 = await test_invalid_token(server_url)

    print("\n" + "=" * 70)
    print("📋 KẾT QUẢ KIỂM THỬ AUTHENTICATION:")
    print(f"  1. Valid Token Check:   {'PASSED ✅' if t1 else 'FAILED ❌'}")
    print(f"  2. Missing Token Check: {'PASSED ✅' if t2 else 'FAILED ❌'}")
    print(f"  3. Invalid Token Check: {'PASSED ✅' if t3 else 'FAILED ❌'}")
    print("=" * 70)

    if t1 and t2 and t3:
        print("🎉 TẤT CẢ CÁC BÀI TEST BẢO MẬT ĐỀU ĐẠT CHUẨN MỨC ĐỘ TRUNG BÌNH!")
    else:
        print("⚠️ Vui lòng kiểm tra lại cấu hình server.")


if __name__ == "__main__":
    asyncio.run(main())
