# Robotics Control MCP Server
**By MEOK AI Labs** | [meok.ai](https://meok.ai)

IoT and robotics interface for AI agents. Control hardware devices over serial ports and HTTP -- Arduino, Raspberry Pi, 3D printers, CNC machines, servo controllers, and custom robots. Part of the HARVI Humanoid Robotics project.

## Tools

| Tool | Description |
|------|-------------|
| `list_devices` | Auto-discover serial ports + list registered HTTP devices |
| `send_command` | Send a text command to any device (serial or HTTP) |
| `read_sensor` | Read sensor values with automatic key=value parsing |
| `set_servo` | Set a servo to a specific angle (0-180) on a channel |
| `run_gcode` | Send G-code to CNC machines, 3D printers, or robot arms |
| `emergency_stop` | Software + hardware emergency stop (blocks all commands) |

## Installation

```bash
# Core
pip install mcp pyserial

# Optional: for HTTP device communication
pip install httpx
```

## Usage

### Run the server

```bash
python server.py
```

### Claude Desktop config

```json
{
  "mcpServers": {
    "robotics": {
      "command": "python",
      "args": ["/path/to/robotics-control-mcp/server.py"]
    }
  }
}
```

### Example calls

**Discover connected devices:**
```
Tool: list_devices
Output: {"discovered_serial": [{"port": "/dev/cu.usbmodem1401", "description": "Arduino Mega 2560", "manufacturer": "Arduino"}], "discovered_count": 1}
```

**Send a command to an Arduino:**
```
Tool: send_command
Input: {"device": "/dev/cu.usbmodem1401", "command": "GET_STATUS", "baudrate": 9600}
Output: {"status": "ok", "response": ["STATUS: READY", "TEMP: 23.5", "BATTERY: 87%"]}
```

**Read a sensor:**
```
Tool: read_sensor
Input: {"device": "/dev/cu.usbmodem1401", "sensor_id": "temperature"}
Output: {"status": "ok", "response": ["temperature=23.5"], "parsed_values": {"temperature": 23.5}}
```

**Control a servo:**
```
Tool: set_servo
Input: {"device": "/dev/cu.usbmodem1401", "channel": 0, "angle": 90.0, "speed": 50}
Output: {"status": "ok", "servo": {"channel": 0, "angle": 90.0, "speed": 50}}
```

**Send G-code to a 3D printer:**
```
Tool: run_gcode
Input: {"device": "/dev/ttyUSB0", "gcode": "G28\nG1 X50 Y50 Z10 F3000\nG1 X100 Y100 F1500", "baudrate": 115200}
Output: {"total_lines": 3, "successful": 3, "failed": 0}
```

**Send commands to an HTTP device (ESP32, Raspberry Pi):**
```
Tool: send_command
Input: {"device": "http://192.168.1.100/api/command", "command": "LED_ON"}
Output: {"status": "ok", "response": {"led": "on", "brightness": 255}}
```

**Emergency stop:**
```
Tool: emergency_stop
Input: {"device": "/dev/ttyUSB0"}
Output: {"status": "activated", "emergency_stop": true, "message": "EMERGENCY STOP ACTIVATED. All commands blocked."}
```

**Release emergency stop:**
```
Tool: emergency_stop
Input: {"release": true}
Output: {"status": "released", "emergency_stop": false, "message": "Emergency stop released. Commands enabled."}
```

## Safety Features

- **Emergency stop**: Software-level kill switch blocks ALL commands to ALL devices when active
- **Hardware E-stop**: Sends M112 (serial) or ESTOP (HTTP) to the physical device
- **G-code validation**: Only valid G-code characters are accepted
- **G-code line limit**: Free tier max 50 lines per call to prevent runaway jobs
- **Servo bounds**: Angle validated to 0-180 degrees, channel to 0-31
- **Timeouts**: All serial/HTTP calls have configurable timeouts
- **No persistent connections**: Each command opens and closes its own connection

## Supported Devices

| Device Type | Connection | Example |
|-------------|-----------|---------|
| Arduino / Teensy | Serial USB | /dev/cu.usbmodem*, COM3 |
| 3D Printer (Marlin) | Serial USB | /dev/ttyUSB0, 115200 baud |
| CNC Machine (GRBL) | Serial USB | /dev/ttyUSB0, 115200 baud |
| ESP32 / ESP8266 | HTTP WiFi | http://192.168.1.x/api |
| Raspberry Pi | HTTP | http://pi.local:5000/cmd |
| Servo Controllers | Serial | PCA9685, Pololu Maestro |
| Custom Robots | Serial/HTTP | Any text-based protocol |

## HARVI Integration

This server is part of MEOK AI Labs' HARVI humanoid robotics project. HARVI uses SO-101 servo arms with LeRobot ML inference, connected through this MCP server for AI-driven teleoperation and autonomous control.

## Pricing

| Tier | Limit | Price |
|------|-------|-------|
| Free | 50 calls/day, 50 G-code lines/call | $0 |
| Pro | Unlimited + persistent connections + batch G-code | $12/mo |
| Enterprise | Custom + multi-device orchestration + safety certs | Contact us |

## License

MIT
