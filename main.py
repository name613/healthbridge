import json
import anyio
import uvicorn
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse
from mcp.server.fastmcp import FastMCP

health_data = {}
_data_lock = anyio.Lock()

mcp = FastMCP("health-bridge")

@mcp.tool()
async def get_health_data() -> str:          # ← 加上 async
    async with _data_lock:
        return json.dumps(health_data, ensure_ascii=False, indent=2)

@mcp.tool()
async def get_sleep() -> str:                # ← 加上 async
    async with _data_lock:
        return json.dumps(health_data.get("sleep", []), ensure_ascii=False, indent=2)

@mcp.tool()
async def get_steps() -> str:                # ← 加上 async
    async with _data_lock:
        return json.dumps(health_data.get("steps", []), ensure_ascii=False, indent=2)

async def receive_health(request: Request):
    data = await request.json()
    async with _data_lock:
        health_data.update(data)
    return JSONResponse({"status": "ok"})

app = mcp.streamable_http_app()
app.routes.insert(0, Route("/health", receive_health, methods=["POST"]))

async def run_uvicorn():
    config = uvicorn.Config(app, host="0.0.0.0", port=8080, loop="asyncio")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    anyio.run(run_uvicorn)
