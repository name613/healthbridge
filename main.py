from mcp.server.fastmcp import FastMCP
import json

from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from datetime import datetime
import json
import logging

health_data = {}

mcp = FastMCP(
    "health-bridge",
    host="0.0.0.0",
    port=8080
)

@mcp.tool()
def get_health_summary() -> str:
    """获取健康数据聚合摘要"""
    summary = {}

    # 步数
    steps = health_data.get("steps", [])
    if steps:
        try:
            total_steps = sum(item.get("count", 0) for item in steps)
            summary["steps"] = {"total": total_steps}
        except Exception:
            pass

    # 心率
    heart_rates = health_data.get("heart_rate", [])
    if heart_rates:
        try:
            values = [item.get("bpm", 0) for item in heart_rates if item.get("bpm") is not None]
            if values:
                summary["heart_rate"] = {
                    "avg": round(sum(values) / len(values), 1),
                    "max": max(values),
                    "min": min(values)
                }
        except Exception:
            pass

    # 静息心率
    resting = health_data.get("resting_heart_rate", [])
    if resting:
        try:
            values = [item.get("bpm", 0) for item in resting if item.get("bpm") is not None]
            if values:
                summary["resting_heart_rate"] = round(sum(values) / len(values), 1)
        except Exception:
            pass

    # 距离
    distance = health_data.get("distance", [])
    if distance:
        try:
            total_distance = sum(item.get("meters", 0) for item in distance)
            summary["distance_m"] = round(total_distance, 1)
        except Exception:
            pass

    # 活跃卡路里
    calories = health_data.get("active_calories", [])
    if calories:
        try:
            total_calories = sum(item.get("calories", 0) for item in calories)
            summary["active_calories"] = round(total_calories, 1)
        except Exception:
            pass

    # 血氧
    oxygen = health_data.get("oxygen_saturation", [])
    if oxygen:
        try:
            values = [
                item.get("percentage", 0)
                for item in oxygen
                if item.get("percentage") is not None
            ]
            if values:
                summary["oxygen_saturation"] = {
                    "avg": round(sum(values) / len(values), 1),
                    "max": max(values),
                    "min": min(values)
                }
        except Exception:
            pass

    return json.dumps(summary, ensure_ascii=False, indent=2)


@mcp.tool()
def get_sleep_summary() -> str:
    """获取睡眠摘要"""
    sleep_records = health_data.get("sleep", [])

    if not sleep_records:
        return json.dumps(
            {"error": "no sleep data"},
            ensure_ascii=False,
            indent=2
        )

    deep = 0.0
    light = 0.0
    rem = 0.0
    awake = 0.0

    bedtimes = []
    waketimes = []

    for item in sleep_records:
        try:
            start = datetime.fromisoformat(
                item["start_time"].replace("Z", "+00:00")
            )

            end = datetime.fromisoformat(
                item["end_time"].replace("Z", "+00:00")
            )

            duration_hours = (
                end - start
            ).total_seconds() / 3600

            stage = str(item.get("stage", ""))

            bedtimes.append(start)
            waketimes.append(end)

            if stage == "4":
                deep += duration_hours
            elif stage == "5":
                light += duration_hours
            elif stage == "6":
                rem += duration_hours
            elif stage == "1":
                awake += duration_hours

        except Exception:
            continue

    if not bedtimes or not waketimes:
        return json.dumps(
            {"error": "no valid sleep data"},
            ensure_ascii=False,
            indent=2
        )

    total_sleep = deep + light + rem
    total_in_bed = total_sleep + awake

    sleep_efficiency = 0
    if total_in_bed > 0:
        sleep_efficiency = round(
            total_sleep / total_in_bed * 100,
            1
        )

    bedtime = min(bedtimes)
    wake_time = max(waketimes)

    summary = {
        "bedtime": bedtime.strftime("%H:%M"),
        "wake_time": wake_time.strftime("%H:%M"),
        "total_sleep_hours": round(total_sleep, 2),
        "deep_sleep_hours": round(deep, 2),
        "light_sleep_hours": round(light, 2),
        "rem_sleep_hours": round(rem, 2),
        "awake_hours": round(awake, 2),
        "sleep_efficiency": sleep_efficiency
    }

    return json.dumps(
        summary,
        ensure_ascii=False,
        indent=2
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
