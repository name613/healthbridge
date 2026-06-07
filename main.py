from mcp.server.fastmcp import FastMCP
import json

from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

health_data = {}

mcp = FastMCP(
    "health-bridge",
    host="0.0.0.0",
    port=8080
)


@mcp.tool()
def get_health_data() -> str:
    return json.dumps(
        health_data,
        ensure_ascii=False,
        indent=2
    )


@mcp.tool()
def get_sleep() -> str:
    return json.dumps(
        health_data.get("sleep", []),
        ensure_ascii=False,
        indent=2
    )


@mcp.tool()
def get_steps() -> str:
    return json.dumps(
        health_data.get("steps", []),
        ensure_ascii=False,
        indent=2
    )


async def receive_health(request: Request):
    data = await request.json()
    health_data.update(data)
    return JSONResponse({"status": "ok"})


app = mcp.streamable_http_app()

app.routes.append(
    Route(
        "/health",
        receive_health,
        methods=["POST"]
    )
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080
    )
