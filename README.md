# Health Bridge

一个轻量级 MCP（Model Context Protocol）服务器，用于将手机健康数据同步给 Claude。

支持：

* 步数（Steps）
* 睡眠（Sleep）
* 健康数据汇总（Health Data）

部署于 Zeabur，通过 Claude Custom Connector 接入。

---

## 功能

### get_health_data

获取全部健康数据。

### get_steps

获取步数数据。

### get_sleep

获取睡眠数据。

### get_sleep_summary

获取睡眠摘要：入睡 / 起床时间、各睡眠阶段时长、睡眠效率。

* 可选参数 `date`（北京时间 `YYYY-MM-DD`）：只统计该起床日的那一晚；**留空则取最近一晚**。
* `bedtime` / `wake_time` 以**北京时间（UTC+8）**显示。
* 睡眠阶段编码（`stage`）对应关系：

  | stage | 含义 |
  | ----- | ---- |
  | 1     | 清醒（Awake） |
  | 4     | 浅睡（Light） |
  | 5     | 深睡（Deep）  |
  | 6     | REM          |

  睡眠记录按整晚 session 组织，实际阶段数据位于每个 session 的 `stages` 数组内。

### get_health_summary

获取健康数据聚合摘要（步数、心率、距离、卡路里、血氧等）。

* 可选参数 `date`（北京时间 `YYYY-MM-DD`）：只统计当天；**留空则取数据中最近的一天**。
  （`health_data` 不按日期分组，常含多天数据，故按天过滤后再聚合，避免把历史混入。）
* 心率、血氧的 `max` / `min` 会带上发生时刻（北京时间），例如：

  ```json
  "heart_rate": {
    "avg": 82.8,
    "max": { "bpm": 122, "time": "12:12" },
    "min": { "bpm": 62, "time": "06:50" }
  }
  ```

---

## API

### 接收健康数据

```http
POST /health
```

请求示例：

```json
{
  "steps": [
    {
      "count": 5000
    }
  ],
  "sleep": [
    {
      "session_end_time": "2026-06-08T00:25:00Z",
      "duration_seconds": 28800,
      "stages": [
        {
          "stage": "5",
          "start_time": "2026-06-07T16:50:00Z",
          "end_time": "2026-06-07T18:50:00Z",
          "duration_seconds": 7200
        }
      ]
    }
  ]
}
```

---

## MCP Endpoint

```text
https://your-domain.com/mcp
```

Claude Connector 中填写：

```text
https://your-domain.com/mcp
```

---

## 部署

### requirements.txt

```txt
mcp[cli]>=1.0.0
fastapi>=0.115.0
uvicorn>=0.30.0
starlette>=0.40.0
httpx>=0.27.0
```

### Zeabur

开启 Public Domain。

部署完成后确认：

```text
https://your-domain.com/mcp
```

可访问。

---

## 重要配置

FastMCP 必须显式指定 host 和 port：

```python
mcp = FastMCP(
    "health-bridge",
    host="0.0.0.0",
    port=8080
)
```

否则 Claude Connector 可能出现：

```text
Couldn't register with healthbridge's sign-in service
```

日志中表现为：

```text
421 Misdirected Request
```

---

## 调试

查看运行日志：

```text
POST /mcp
```

如果返回：

```text
200 OK
```

表示 MCP 正常工作。

如果返回：

```text
421 Misdirected Request
```

请检查 FastMCP 初始化配置。

---

## 已验证环境

* Claude Custom Connector
* Zeabur
* FastMCP
* Streamable HTTP Transport
* Health Connect 数据同步

---

Built with ❤️ by 柒.
