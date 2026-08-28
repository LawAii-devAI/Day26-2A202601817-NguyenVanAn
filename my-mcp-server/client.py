"""MCP Client tương tác với incident-log-order-server.

Hỗ trợ kết nối qua stdio (subprocess) hoặc Streamable HTTP.
Thực hiện:
  1. Khám phá danh sách tools (list_tools)
  2. Đọc tài nguyên server://info (read_resource)
  3. Gọi tool tìm kiếm log (search_logs)
  4. Gọi tool lấy lỗi gần nhất (get_recent_errors)
  5. Gọi tool tra cứu đơn hàng v1 và v2 (get_order, get_order_v2)
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


async def run_stdio_client() -> None:
    """Chạy MCP Client kết nối tới server.py qua stdio."""
    server_script = Path(__file__).resolve().parent / "server.py"
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_script)],
        env=os.environ.copy(),
    )

    print("=" * 70)
    print("🔌 Kết nối tới MCP Server qua stdio transport...")
    print("=" * 70)

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            print("✅ MCP Session initialized thành công!\n")

            # 1. Khám phá danh sách tools
            tools_response = await session.list_tools()
            print(f"📋 Tìm thấy {len(tools_response.tools)} tools được công bố:")
            for tool in tools_response.tools:
                print(f"  • {tool.name}: {tool.description.splitlines()[0]}")
            print()

            # 2. Đọc Resource server://info
            print("📖 Đọc tài nguyên 'server://info'...")
            try:
                info_resource = await session.read_resource("server://info")
                info_data = json.loads(info_resource.contents[0].text)
                print(f"  → Tên server: {info_data.get('name')}")
                print(f"  → Phiên bản: {info_data.get('version')}")
                print(f"  → Tools catalog: {list(info_data.get('tools', {}).keys())}")
            except Exception as e:
                print(f"  ⚠️ Đọc resource: {e}")
            print()

            # 3. Gọi tool get_log_statistics
            print("📊 Gọi tool 'get_log_statistics'...")
            stats_result = await session.call_tool("get_log_statistics", arguments={"hours": 24})
            print(f"  → Kết quả:\n{stats_result.content[0].text}\n")

            # 4. Gọi tool get_recent_errors
            print("🚨 Gọi tool 'get_recent_errors' (limit=3)...")
            errors_result = await session.call_tool(
                "get_recent_errors", arguments={"limit": 3, "service": "ALL"}
            )
            print(f"  → Kết quả:\n{errors_result.content[0].text}\n")

            # 5. Gọi tool search_logs
            print("🔍 Gọi tool 'search_logs' với keyword='timeout'...")
            search_result = await session.call_tool(
                "search_logs", arguments={"keyword": "timeout", "level": "ALL", "limit": 5}
            )
            print(f"  → Kết quả:\n{search_result.content[0].text}\n")

            # 6. So sánh get_order (v1) và get_order_v2 (v2)
            print("🛒 Gọi tool 'get_order' [v1 Legacy] cho đơn ORD-2026-001...")
            v1_result = await session.call_tool("get_order", arguments={"order_id": "ORD-2026-001"})
            print(f"  → v1 Response: {v1_result.content[0].text}")

            print("\n🛒 Gọi tool 'get_order_v2' [v2 Rich] cho đơn ORD-2026-001 (kèm audit trail)...")
            v2_result = await session.call_tool(
                "get_order_v2",
                arguments={"order_id": "ORD-2026-001", "include_audit_trail": True},
            )
            print(f"  → v2 Response:\n{v2_result.content[0].text}")

    print("\n" + "=" * 70)
    print("🎉 Hoàn thành kiểm tra toàn bộ tính năng MCP Client!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_stdio_client())
