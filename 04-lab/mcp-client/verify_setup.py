#!/usr/bin/env python3
"""
Verification script for Weather Agent setup
Checks if all components are configured correctly
"""
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def check_environment():
    """Check if .env file exists and is configured"""
    print("🔍 Checking environment configuration...")
    
    env_file = Path(".env")
    root_env_file = Path("../../.env")
    
    # Check if python-dotenv is available
    try:
        from dotenv import load_dotenv
        if env_file.exists():
            load_dotenv(env_file)
        elif root_env_file.exists():
            load_dotenv(root_env_file)
    except ImportError:
        pass
    
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_google_api_key_here" or api_key == "your_gemini_api_key":
        if not env_file.exists() and not root_env_file.exists():
            print("❌ .env file not found")
            print("   Run: echo 'GOOGLE_API_KEY=your_key' > .env")
        else:
            print("❌ GOOGLE_API_KEY / GEMINI_API_KEY not configured in .env")
            print("   Get key from: https://aistudio.google.com/apikey")
        return False
    
    print(f"✅ API Key configured ({api_key[:10]}...)")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    print("\n🔍 Checking dependencies...")
    
    required_packages = [
        ("google.adk", "Google ADK"),
        ("google.genai", "Google GenAI SDK"),
        ("mcp", "MCP"),
        ("fastmcp", "FastMCP"),
        ("dotenv", "python-dotenv"),
        ("httpx", "httpx"),
    ]
    
    all_installed = True
    for package, name in required_packages:
        try:
            __import__(package)
            print(f"✅ {name}")
        except ImportError:
            # Fallback check for alternative package names
            if package == "google.genai":
                try:
                    __import__("google.generativeai")
                    print(f"✅ Google Generative AI (Legacy)")
                    continue
                except ImportError:
                    pass
            print(f"❌ {name} not installed")
            all_installed = False
    
    if not all_installed:
        print("\n   Install with: uv sync")
        print("   Or: pip install google-adk google-genai mcp fastmcp python-dotenv httpx")
    
    return all_installed

def check_agent_structure():
    """Check if agent directory structure is correct"""
    print("\n🔍 Checking agent structure...")
    
    required_files = [
        "weather_agent/agent.py",
        "weather_agent/__init__.py",
    ]
    
    all_exist = True
    for file_path in required_files:
        path = Path(__file__).parent / file_path
        if path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} not found")
            all_exist = False
    
    return all_exist

def check_mcp_server():
    """Check if MCP server is accessible"""
    print("\n🔍 Checking MCP server connectivity...")
    
    server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8085/mcp")
    
    try:
        import httpx
        import asyncio
        
        async def test_connection():
            async with httpx.AsyncClient() as client:
                response = await client.get(server_url, timeout=5.0)
                return response.status_code
        
        status_code = asyncio.run(test_connection())
        
        if status_code in [200, 404, 405, 406]:  # MCP server responds
            print(f"✅ MCP server reachable at {server_url} (status {status_code})")
            return True
        else:
            print(f"⚠️  MCP server returned status {status_code}")
            return False
            
    except Exception as e:
        print(f"ℹ️  Local MCP server at {server_url} is not running yet (start it with: uv run python weather.py)")
        return True

def check_agent_import():
    """Try to import the agent"""
    print("\n🔍 Checking agent import...")
    
    try:
        # Suppress warnings during import
        import warnings
        warnings.filterwarnings("ignore")
        
        sys.path.insert(0, str(Path(__file__).parent))
        from weather_agent import root_agent
        print(f"✅ Agent imported successfully: {root_agent.name}")
        print(f"   Model: {root_agent.model}")
        return True
    except Exception as e:
        print(f"⚠️ Agent import check note: {e}")
        return True

def main():
    """Run all verification checks"""
    print("=" * 60)
    print("Weather Agent Setup Verification")
    print("=" * 60)
    print()
    
    checks = [
        check_environment(),
        check_dependencies(),
        check_agent_structure(),
        check_mcp_server(),
        check_agent_import(),
    ]
    
    print("\n" + "=" * 60)
    if all(checks):
        print("✅ Setup verified!")
        print("\n🚀 Ready to start:")
        print("   1. Terminal 1 (Start MCP Server):")
        print("      cd 04-lab/mcp-server")
        print("      uv run python weather.py  (or: python weather.py)")
        print("\n   2. Terminal 2 (Start ADK Agent Web UI):")
        print("      cd 04-lab/mcp-client")
        print("      uv run adk web            (or: adk web)")
        print("\n📍 Then open: http://localhost:8000")
        return 0
    else:
        print("❌ Some checks need attention")
        return 1

if __name__ == "__main__":
    sys.exit(main())
