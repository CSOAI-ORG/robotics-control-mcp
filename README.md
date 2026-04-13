# Robotics Control MCP Server

> **By [MEOK AI Labs](https://meok.ai)** — Sovereign AI tools for everyone.

IoT and robotics interface for AI agents. Control hardware devices over serial ports and HTTP -- Arduino, Raspberry Pi, 3D printers, CNC machines, servo controllers, and custom robots.

[![MCPize](https://img.shields.io/badge/MCPize-Listed-blue)](https://mcpize.com/mcp/robotics-control)
[![MIT License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![MEOK AI Labs](https://img.shields.io/badge/MEOK_AI_Labs-255+_servers-purple)](https://meok.ai)

## Tools

| Tool | Description |
|------|-------------|
| `list_devices` | List all available devices with auto-discovery |
| `send_command` | Send a text command to a device and get its response |
| `read_sensor` | Read a sensor value from a connected device |
| `set_servo` | Set a servo motor to a specific angle |
| `run_gcode` | Send G-code commands to CNC machines, 3D printers, or robot arms |
| `emergency_stop` | Activate or release emergency stop on all devices |

## Quick Start

```bash
pip install mcp
git clone https://github.com/CSOAI-ORG/robotics-control-mcp.git
cd robotics-control-mcp
python server.py
```

## Claude Desktop Config

```json
{
  "mcpServers": {
    "robotics-control": {
      "command": "python",
      "args": ["server.py"],
      "cwd": "/path/to/robotics-control-mcp"
    }
  }
}
```

## Pricing

| Plan | Price | Requests |
|------|-------|----------|
| Free | $0/mo | 50 calls/day, 50 G-code lines/call |
| Pro | $12/mo | Unlimited + persistent connections + batch G-code |
| Enterprise | Contact us | Custom + multi-device orchestration |

[Get on MCPize](https://mcpize.com/mcp/robotics-control)

## Part of MEOK AI Labs

This is one of 255+ MCP servers by MEOK AI Labs. Browse all at [meok.ai](https://meok.ai) or [GitHub](https://github.com/CSOAI-ORG).

---
**MEOK AI Labs** | [meok.ai](https://meok.ai) | nicholas@meok.ai | United Kingdom
