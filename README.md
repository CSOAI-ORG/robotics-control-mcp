[![robotics-control-mcp MCP server](https://glama.ai/mcp/servers/CSOAI-ORG/robotics-control-mcp/badges/score.svg)](https://glama.ai/mcp/servers/CSOAI-ORG/robotics-control-mcp)
[![MCP Registry](https://img.shields.io/badge/MCP_Registry-Published-green)](https://registry.modelcontextprotocol.io)
[![PyPI](https://img.shields.io/pypi/v/robotics-control-mcp)](https://pypi.org/project/robotics-control-mcp/)

[![robotics-control-mcp MCP server](https://glama.ai/mcp/servers/CSOAI-ORG/robotics-control-mcp/badges/card.svg)](https://glama.ai/mcp/servers/CSOAI-ORG/robotics-control-mcp)

<div align="center">

# Robotics Control MCP

**MCP server for robotics control mcp operations**

[![PyPI](https://img.shields.io/pypi/v/meok-robotics-control-mcp)](https://pypi.org/project/meok-robotics-control-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MEOK AI Labs](https://img.shields.io/badge/MEOK_AI_Labs-MCP_Server-purple)](https://meok.ai)

</div>

## Overview

Robotics Control MCP provides AI-powered tools via the Model Context Protocol (MCP).

## Tools

| Tool | Description |
|------|-------------|
| `list_devices` | List all available devices. Auto-discovers serial ports (USB, Arduino, |
| `send_command` | Send a text command to a device and get its response. |
| `read_sensor` | Read a sensor value from a connected device. Sends a READ command |
| `set_servo` | Set a servo motor to a specific angle. |
| `run_gcode` | Send G-code commands to a CNC machine, 3D printer, or robot arm. |
| `emergency_stop` | Activate or release emergency stop. When active, ALL commands to ALL |

## Installation

```bash
pip install meok-robotics-control-mcp
```

## Usage with Claude Desktop

Add to your Claude Desktop MCP config:

```json
{
  "mcpServers": {
    "robotics-control-mcp": {
      "command": "python",
      "args": ["-m", "meok_robotics_control_mcp.server"]
    }
  }
}
```

## License

MIT © [MEOK AI Labs](https://meok.ai)
<!-- mcp-name: io.github.CSOAI-ORG/robotics-control-mcp -->
