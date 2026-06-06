import json
import anyio
import uvicorn
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse
from mcp.server.fastmcp import FastMCP

# ---------- 健康数据存储（线程/协程安全锁）----------
health_data = {}
_data_lock = anyio.Lock()   # 保证并发写入安全

# ---------- MCP 服务器 ----------
mcp = FastMCP("health-bridge")

@mcp.tool()
def get_health_data() -> str:
    """获取完整的健康数据"""
    async with _data_lock:
        return json.dumps(health_data, ensure_ascii=False, indent=2)

@mcp.tool()
def get_sleep() -> str:
    """获取睡眠数据"""
    async with _data_lock:
        return json.dumps(health_data.get("sleep", []), ensure_ascii=False, indent=2)

@mcp.tool()
def get_steps() -> str:
    """获取步数"""
    async with _data_lock:
        return json.dumps(health_data.get("steps", []), ensure_ascii=False, indent=2)

# ---------- 自定义端点：接收健康数据 ----------
async def receive_health(request: Request):
    data = await request.json()
    async with _data_lock:
        health_data.update(data)
    return JSONResponse({"status": "ok"})

# ---------- 构建 ASGI 应用 ----------
app = mcp.streamable_http_app()
# 把 /health 路由插到最前面，避免被 MCP 的泛路由匹配
app.routes.insert(0, Route("/health", receive_health, methods=["POST"]))

# ---------- 启动入口（关键：用 anyio.run 提供任务组上下文）----------
async def run_uvicorn():
    config = uvicorn.Config(app, host="0.0.0.0", port=8080, loop="asyncio")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    anyio.run(run_uvicorn)
