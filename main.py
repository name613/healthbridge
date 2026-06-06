from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.resources import Resource
import json

health_data = {}

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

# 自定义路由接收健康数据
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse

async def receive_health(request: Request):
    data = await request.json()
    health_data.update(data)
    return JSONResponse({"status": "ok"})

app = mcp.streamable_http_app()
print(type(app))
print(dir(app))
app.routes.append(Route("/health", receive_health, methods=["POST"]))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
