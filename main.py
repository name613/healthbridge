from mcp.server.fastmcp import FastMCP
import json

health_data = {}

mcp = FastMCP("health-bridge")

# tools ...

from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

async def receive_health(request: Request):
data = await request.json()
health_data.update(data)
return JSONResponse({"status": "ok"})

app = mcp.streamable_http_app()

print(type(app))
print(dir(app))

app.routes.append(
Route("/health", receive_health, methods=["POST"])
)

app.add_middleware(
TrustedHostMiddleware,
allowed_hosts=["*"]
)

if **name** == "**main**":
import uvicorn
uvicorn.run(app, host="0.0.0.0", port=8080)
