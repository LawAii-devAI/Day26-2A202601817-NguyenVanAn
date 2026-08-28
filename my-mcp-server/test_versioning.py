"""Automated Test Suite for MCP Versioning & Backward Compatibility (Hard Level).

Kiểm tra:
  1. Server công bố metadata qua resource `server://info`
  2. Client mới đọc metadata và gọi tool mới `get_order_v2` với payload mở rộng
  3. Client cũ vẫn gọi tool `get_order` (v1) hoạt động bình thường, không bị break
  4. Client thông minh tự động kiểm tra capability và fallback nếu cần thiết.

Cách chạy:
  python test_versioning.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def run_versioning_tests() -> None:
    server_script = Path(__file__).resolve().parent / "server.py"
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_script)],
        env=os.environ.copy(),
    )

    print("=" * 75)
    print("🧪 KIỂM THỬ VERSIONING & BACKWARD COMPATIBILITY (MỨC ĐỘ KHÓ)")
    print("=" * 75)

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # ── 1. Đọc metadata từ resource server://info ────────────────
            print("\n[BƯỚC 1] Client đọc metadata từ resource 'server://info'...")
            info_res = await session.read_resource("server://info")
            metadata = json.loads(info_res.contents[0].text)

            server_ver = metadata.get("version")
            tools_meta = metadata.get("tools", {})
            print(f"  ✅ Server Version: {server_ver}")
            print(f"  ✅ Tools Metadata:")
            for tool_name, tool_info in tools_meta.items():
                status = "⚠️ DEPRECATED" if tool_info.get("deprecated") else "✨ ACTIVE"
                print(f"     • {tool_name} (v{tool_info.get('version')}): {status}")

            assert server_ver == "2.0.0", f"Expected version 2.0.0, got {server_ver}"
            assert "get_order" in tools_meta, "get_order v1 must be listed"
            assert "get_order_v2" in tools_meta, "get_order_v2 must be listed"

            # ── 2. Client cũ gọi tool v1 (get_order) ─────────────────────
            print("\n[BƯỚC 2] Kiểm thử Client cũ gọi tool v1 'get_order'...")
            v1_res = await session.call_tool("get_order", {"order_id": "ORD-2026-001"})
            v1_data = json.loads(v1_res.content[0].text)
            print(f"  ✅ Kết quả v1 nhận về đúng format cũ:")
            print(f"     {json.dumps(v1_data, ensure_ascii=False, indent=6)}")

            # Kiểm tra schema v1 giữ nguyên các field cũ
            assert "id" in v1_data, "v1 must contain 'id'"
            assert "status" in v1_data, "v1 must contain 'status'"
            assert "total" in v1_data, "v1 must contain 'total'"
            assert "audit_trail" not in v1_data, "v1 should not have audit_trail"

            # ── 3. Client mới gọi tool v2 (get_order_v2) ─────────────────
            print("\n[BƯỚC 3] Kiểm thử Client mới gọi tool v2 'get_order_v2'...")
            v2_res = await session.call_tool(
                "get_order_v2",
                {"order_id": "ORD-2026-001", "include_audit_trail": True},
            )
            v2_data = json.loads(v2_res.content[0].text)
            print(f"  ✅ Kết quả v2 nhận về format mở rộng chi tiết:")
            print(f"     {json.dumps(v2_data, ensure_ascii=False, indent=6)}")

            # Kiểm tra schema v2 có các field mới
            assert v2_data.get("api_version") == "2.0.0", "v2 must have api_version 2.0.0"
            assert "customer" in v2_data and isinstance(v2_data["customer"], dict)
            assert "items" in v2_data and len(v2_data["items"]) > 0
            assert "audit_trail" in v2_data and len(v2_data["audit_trail"]) > 0

            # ── 4. Client thông minh tự động chọn tool dựa trên metadata ─
            print("\n[BƯỚC 4] Mô phỏng Smart Client: Chọn tool theo capability & fallback...")

            async def smart_fetch_order(order_id: str) -> dict:
                # 1. Đọc metadata để check capability
                meta_res = await session.read_resource("server://info")
                server_meta = json.loads(meta_res.contents[0].text)
                available_tools = server_meta.get("tools", {})

                # 2. Quyết định tool phù hợp
                if "get_order_v2" in available_tools and not available_tools["get_order_v2"].get(
                    "deprecated"
                ):
                    print(f"  ⚡ Smart Client: Tìm thấy 'get_order_v2' -> Sử dụng v2")
                    call_res = await session.call_tool(
                        "get_order_v2",
                        {"order_id": order_id, "include_audit_trail": False},
                    )
                    return json.loads(call_res.content[0].text)
                else:
                    print(f"  🔄 Smart Client: Fallback về 'get_order' v1")
                    call_res = await session.call_tool("get_order", {"order_id": order_id})
                    return json.loads(call_res.content[0].text)

            smart_result = await smart_fetch_order("ORD-2026-003")
            print(f"  ✅ Smart Client lấy dữ liệu đơn ORD-2026-003 thành công:")
            print(f"     Status: {smart_result.get('status')}, Total: {smart_result.get('total_amount', smart_result.get('total'))}")

    print("\n" + "=" * 75)
    print("🎉 TẤT CẢ CÁC BÀI TEST VERSIONING & BACKWARD COMPATIBILITY ĐỀU ĐẠT CHUẨN MỨC ĐỘ KHÓ!")
    print("=" * 75)


if __name__ == "__main__":
    asyncio.run(run_versioning_tests())
