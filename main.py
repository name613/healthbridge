from mcp.server.fastmcp import FastMCP
import json

from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from datetime import datetime, timezone, timedelta
import json
import logging

health_data = {}

mcp = FastMCP(
    "health-bridge",
    host="0.0.0.0",
    port=8080
)

# 北京时间（UTC+8）
BEIJING_TZ = timezone(timedelta(hours=8))


def _parse_iso(value):
    """解析 ISO-8601 时间戳（含结尾 Z）为带时区的 datetime。"""
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _record_time(item):
    """取一条记录的代表时刻（带时区 datetime），无法解析返回 None。

    瞬时采样（心率、血氧）用 "time"，区间分桶（步数、距离、卡路里）用
    "start_time"。
    """
    if not isinstance(item, dict):
        return None
    for key in ("time", "start_time"):
        value = item.get(key)
        if value:
            try:
                return _parse_iso(value)
            except Exception:
                return None
    return None


def _beijing_date(dt):
    """带时区 datetime 对应的北京日历日期。"""
    return dt.astimezone(BEIJING_TZ).date()


def _parse_date_arg(date_str):
    """解析 'YYYY-MM-DD' 参数为 date；为空或非法时返回 None。"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        return None


def _latest_date(*record_lists):
    """给定多个记录列表中出现过的最近北京日期。"""
    dates = []
    for records in record_lists:
        for item in records or []:
            dt = _record_time(item)
            if dt is not None:
                dates.append(_beijing_date(dt))
    return max(dates) if dates else None


def _on_date(item, target):
    """记录是否落在目标北京日期当天。"""
    dt = _record_time(item)
    return dt is not None and _beijing_date(dt) == target


def _hilo(records, key):
    """返回 (最高记录, 最低记录)，按 key 字段比较。"""
    return (
        max(records, key=lambda i: i[key]),
        min(records, key=lambda i: i[key]),
    )


@mcp.tool()
def get_health_summary(date: str = "") -> str:
    """获取健康数据聚合摘要。

    date: 北京时间日期 'YYYY-MM-DD'，只统计当天；留空则取数据中最近的一天。
    """
    steps = health_data.get("steps", [])
    heart_rates = health_data.get("heart_rate", [])
    resting = health_data.get("resting_heart_rate", [])
    distance = health_data.get("distance", [])
    calories = health_data.get("active_calories", [])
    oxygen = health_data.get("oxygen_saturation", [])

    target = _parse_date_arg(date)
    if target is None:
        target = _latest_date(
            steps, heart_rates, resting, distance, calories, oxygen
        )

    summary = {}
    if target is None:
        return json.dumps(summary, ensure_ascii=False, indent=2)

    summary["date"] = target.isoformat()

    # 步数
    day_steps = [i for i in steps if _on_date(i, target)]
    if day_steps:
        try:
            summary["steps"] = {
                "total": sum(i.get("count", 0) for i in day_steps)
            }
        except Exception:
            pass

    # 心率（含最高/最低时刻，北京时间）
    day_hr = [
        i for i in heart_rates
        if i.get("bpm") is not None and _on_date(i, target)
    ]
    if day_hr:
        try:
            bpms = [i["bpm"] for i in day_hr]
            hi, lo = _hilo(day_hr, "bpm")
            summary["heart_rate"] = {
                "avg": round(sum(bpms) / len(bpms), 1),
                "max": {
                    "bpm": hi["bpm"],
                    "time": _beijing_time_str(hi),
                },
                "min": {
                    "bpm": lo["bpm"],
                    "time": _beijing_time_str(lo),
                },
            }
        except Exception:
            pass

    # 静息心率
    day_resting = [
        i for i in resting
        if i.get("bpm") is not None and _on_date(i, target)
    ]
    if day_resting:
        try:
            vals = [i["bpm"] for i in day_resting]
            summary["resting_heart_rate"] = round(sum(vals) / len(vals), 1)
        except Exception:
            pass

    # 距离
    day_distance = [i for i in distance if _on_date(i, target)]
    if day_distance:
        try:
            summary["distance_m"] = round(
                sum(i.get("meters", 0) for i in day_distance), 1
            )
        except Exception:
            pass

    # 活跃卡路里
    day_calories = [i for i in calories if _on_date(i, target)]
    if day_calories:
        try:
            summary["active_calories"] = round(
                sum(i.get("calories", 0) for i in day_calories), 1
            )
        except Exception:
            pass

    # 血氧（含最高/最低时刻，北京时间）
    day_oxygen = [
        i for i in oxygen
        if i.get("percentage") is not None and _on_date(i, target)
    ]
    if day_oxygen:
        try:
            pcts = [i["percentage"] for i in day_oxygen]
            hi, lo = _hilo(day_oxygen, "percentage")
            summary["oxygen_saturation"] = {
                "avg": round(sum(pcts) / len(pcts), 1),
                "max": {
                    "percentage": hi["percentage"],
                    "time": _beijing_time_str(hi),
                },
                "min": {
                    "percentage": lo["percentage"],
                    "time": _beijing_time_str(lo),
                },
            }
        except Exception:
            pass

    return json.dumps(summary, ensure_ascii=False, indent=2)


def _beijing_time_str(item):
    """记录时刻的北京时间 HH:MM 字符串。"""
    return _record_time(item).astimezone(BEIJING_TZ).strftime("%H:%M")


def _session_wakeday(session):
    """睡眠 session 的起床日（北京日期），按最晚的 stage 结束时间判定。"""
    stages = session.get("stages") if isinstance(session, dict) else None
    ends = []
    for stage in (stages if stages else [session]):
        try:
            ends.append(_parse_iso(stage["end_time"]))
        except Exception:
            continue
    return _beijing_date(max(ends)) if ends else None


@mcp.tool()
def get_sleep_summary(date: str = "") -> str:
    """获取睡眠摘要。

    date: 北京时间日期 'YYYY-MM-DD'，只统计该起床日的那一晚；
    留空则取最近一晚。
    """
    sleep_records = health_data.get("sleep", [])

    if not sleep_records:
        return json.dumps(
            {"error": "no sleep data"},
            ensure_ascii=False,
            indent=2
        )

    # 按起床日筛选到目标那一晚（默认最近一晚）
    target = _parse_date_arg(date)
    if target is None:
        days = [
            d for d in (_session_wakeday(s) for s in sleep_records)
            if d is not None
        ]
        target = max(days) if days else None
    if target is not None:
        sleep_records = [
            s for s in sleep_records if _session_wakeday(s) == target
        ]

    deep = 0.0
    light = 0.0
    rem = 0.0
    awake = 0.0

    bedtimes = []
    waketimes = []

    # Each sleep record is a session that may contain a nested "stages"
    # list holding the actual stage entries. Flatten to stage records;
    # fall back to treating the record itself as a stage if not nested.
    stage_records = []
    for record in sleep_records:
        stages = record.get("stages") if isinstance(record, dict) else None
        if stages:
            stage_records.extend(stages)
        else:
            stage_records.append(record)

    for item in stage_records:
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
                light += duration_hours
            elif stage == "5":
                deep += duration_hours
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

    # 转成北京时间（UTC+8）显示
    bedtime = min(bedtimes).astimezone(BEIJING_TZ)
    wake_time = max(waketimes).astimezone(BEIJING_TZ)

    summary = {
        "date": target.isoformat() if target is not None else None,
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
