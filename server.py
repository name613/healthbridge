import json
from fastapi import FastAPI, Request
from mcp.server.fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware
import uvicorn

# 存储健康数据
health_data = {}

# MCP
mcp = FastMCP(
    "Health Bridge",
    host="0.0.0.0",
    port=8000,
)

# ========= MCP TOOLS =========

@mcp.tool()
async def get_health_data() -> str:
    """获取全部健康数据"""
    return json.dumps(health_data, ensure_ascii=False)

@mcp.tool()
async def get_steps() -> str:
    """获取步数"""
    return json.dumps(
        health_data.get("steps", []),
        ensure_ascii=False
    )

@mcp.tool()
async def get_sleep() -> str:
    """获取睡眠数据"""
    return json.dumps(
        health_data.get("sleep", []),
        ensure_ascii=False
    )

# ========= WEBHOOK =========

app = FastAPI()

@app.post("/health")
async def receive_health(request: Request):
    global health_data

    data = await request.json()
    health_data.update(data)

    return {"status": "ok"}

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "has_data": bool(health_data)
    }

# ========= MCP =========

mcp_app = mcp.streamable_http_app()

app.mount("/mcp", mcp_app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
    )
