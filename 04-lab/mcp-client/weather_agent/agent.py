"""
Weather Agent - Connects to Remote MCP Server on Cloud Run or Local FastMCP Server
Uses Google ADK with McpToolset and Streamable HTTP transport.
"""
import logging
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
    if "GOOGLE_API_KEY" not in os.environ and "GEMINI_API_KEY" in os.environ:
        os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]
    elif "GEMINI_API_KEY" not in os.environ and "GOOGLE_API_KEY" in os.environ:
        os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]
except ImportError:
    pass

from google.adk import Agent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StreamableHTTPConnectionParams

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8085/mcp")

logger.info(f"🌐 Initializing weather agent with MCP server")
logger.info(f"📡 MCP Server: {MCP_SERVER_URL}")

SYSTEM_INSTRUCTION = (
    "Bạn là trợ lý thời tiết AI thông minh, thân thiện và nhiệt tình. "
    "QUY TẮC BẮT BUỘC:\n"
    "1. LUÔN LUÔN trả lời và giao tiếp với người dùng bằng TIẾNG VIỆT tự nhiên, chu đáo, rõ ràng. "
    "Dù dữ liệu trả về từ công cụ (tool) là tiếng Anh hay bất kỳ ngôn ngữ nào, bạn PHẢI luôn dịch và trình bày toàn bộ câu trả lời bằng tiếng Việt.\n"
    "2. Sử dụng các biểu tượng cảm xúc (emoji) thời tiết sinh động (☀️, 🌧️, ⛅, 💨, 💧, 🌡️, 🌂, ❄️, ⚡...).\n"
    "3. Khi người dùng hỏi thời tiết của một địa điểm, hãy gọi tool phù hợp (`get_current_weather` cho thời tiết hiện tại, `get_forecast` cho dự báo các ngày tới, `health_check` để kiểm tra kết nối).\n"
    "4. Luôn đưa ra lời khuyên thực tế chu đáo (ví dụ: cần mang ô/áo mưa khi có mưa, mang áo ấm khi trời lạnh, chống nắng khi chỉ số UV cao...)."
)

try:
    # Create connection parameters for the MCP server
    connection_params = StreamableHTTPConnectionParams(
        url=MCP_SERVER_URL,
        timeout=30.0,  # Timeout for server cold starts
    )
    
    # Create the MCP toolset - this will connect to the server
    logger.info("🔌 Connecting to MCP server...")
    weather_tools = McpToolset(
        connection_params=connection_params,
    )
    logger.info("✅ MCP toolset created successfully")
    
    # Create the agent with MCP tools
    root_agent = Agent(
        name="weather_agent",
        model="gemini-2.5-flash",
        instruction=SYSTEM_INSTRUCTION,
        tools=[weather_tools],
    )
    logger.info("✅ Weather agent initialized with MCP tools:")
    logger.info("   - get_current_weather(city)")
    logger.info("   - get_forecast(city, days)")
    logger.info("   - health_check()")
    logger.info("🎉 MCP connection successful!")
    
except Exception as e:
    logger.error(f"❌ Failed to connect to MCP server: {e}")
    logger.error(f"   Server URL: {MCP_SERVER_URL}")
    import traceback
    traceback.print_exc()
    
    # Create a fallback agent without tools
    logger.warning("⚠️  Creating fallback agent without MCP tools")
    root_agent = Agent(
        name="weather_agent",
        model="gemini-2.5-flash",
        instruction=SYSTEM_INSTRUCTION,
    )
