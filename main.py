from mcp.server.fastmcp import FastMCP
import json

from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from datetime import datetime
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
    """获取睡眠摘要：入睡时间、总时长、深睡时间"""
    sleep_data = health_data.get("sleep", [])
    if not sleep_data:
        return json.dumps({"error": "无睡眠数据"}, ensure_ascii=False)

    try:
        parsed = []
        for item in sleep_data:
            start = item.get("start_date")
            end = item.get("end_date")
            stage = item.get("stage")
            if start and end and stage:
                # UTC时间字符串转换
                s = datetime.fromisoformat(start.replace("Z", "+00:00"))
                e = datetime.fromisoformat(end.replace("Z", "+00:00"))
                duration_min = (e - s).total_seconds() / 60
                parsed.append({
                    "start": s,
                    "end": e,
                    "duration_min": duration_min,
                    "stage": stage
                })

        if not parsed:
            return json.dumps({"error": "无法解析睡眠时间"}, ensure_ascii=False)

        # 入睡时间：所有阶段的最早开始时间
        bedtime = min(p["start"] for p in parsed)

        # 总睡眠时长：排除清醒/过渡阶段 (stage == "1")
        sleep_minutes = sum(p["duration_min"] for p in parsed if p["stage"] != "1")

        # 深睡时间：stage == "4"
        deep_minutes = sum(p["duration_min"] for p in parsed if p["stage"] == "4")

        summary = {
            "bedtime": bedtime.isoformat(),
            "total_sleep_min": round(sleep_minutes, 1),
            "deep_sleep_min": round(deep_minutes, 1)
        }
        return json.dumps(summary, ensure_ascii=False, indent=2)

    except Exception:
        logging.exception("睡眠摘要计算失败")
        return json.dumps({"error": "内部错误"}, ensure_ascii=False)


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
