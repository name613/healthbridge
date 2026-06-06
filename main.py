from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request
from starlette.responses import JSONResponse
import uvicorn
import json

# 存健康数据
health_data = {}

# MCP服务
mcp = FastMCP("health-bridge")

@mcp.tool()
def get_health_data() -> str:
    """获取bunny的完整健康数据"""
    return json.dumps(health_data, ensure_ascii=False, indent=2)

@mcp.tool()
def get_sleep() -> str:
    """获取睡眠数据"""
    return json.dumps(health_data.get("sleep", []), ensure_ascii=False, indent=2)

@mcp.tool()
def get_steps() -> str:
    """获取步数"""
    return json.dumps(health_data.get("steps", []), ensure_ascii=False, indent=2)

# 接收HC Webhook推来的数据
async def receive_health(request: Request):
    data = await request.json()
    health_data.update(data)
    return JSONResponse({"status": "ok"})

# 组合应用
mcp_app = mcp.streamable_http_app()

app = Starlette(routes=[
    Route("/health", receive_health, methods=["POST"]),
    Mount("/", mcp_app),
])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
