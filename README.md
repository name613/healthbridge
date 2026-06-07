# healthbridge
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
      "duration_seconds": 28800
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

Built with ❤️ for Bunny.
