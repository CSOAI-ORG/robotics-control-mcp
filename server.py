#!/usr/bin/env python3
"""
Robotics Control MCP Server
==============================
IoT and robotics interface for AI agents. List connected devices, send commands
over serial/HTTP, read sensors, control servos, send G-code, and trigger
emergency stops. Designed for hobbyist and research robotics.

By MEOK AI Labs | https://meok.ai
Part of the HARVI Humanoid Robotics project.

Install: pip install mcp pyserial
Run:     python server.py
"""


import sys, os
sys.path.insert(0, os.path.expanduser('~/clawd/meok-labs-engine/shared'))
from auth_middleware import check_access

import json
import os
import re
import time
import threading
from datetime import datetime, timedelta
from typing import Any, Optional
from collections import defaultdict
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------
FREE_DAILY_LIMIT = 50
_usage: dict[str, list[datetime]] = defaultdict(list)


def _check_rate_limit(caller: str = "anonymous") -> Optional[str]:
    now = datetime.now()
    cutoff = now - timedelta(days=1)
    _usage[caller] = [t for t in _usage[caller] if t > cutoff]
    if len(_usage[caller]) >= FREE_DAILY_LIMIT:
        return f"Free tier limit reached ({FREE_DAILY_LIMIT}/day). Upgrade to Pro: https://mcpize.com/robotics-control-mcp/pro"
    _usage[caller].append(now)
    return None


# ---------------------------------------------------------------------------
# Safety: Emergency stop state
# ---------------------------------------------------------------------------
_emergency_stop_active = False
_emergency_stop_lock = threading.Lock()


def _check_emergency_stop() -> Optional[str]:
    with _emergency_stop_lock:
        if _emergency_stop_active:
            return "EMERGENCY STOP ACTIVE. All commands blocked. Call emergency_stop(release=True) to resume."
    return None


# ---------------------------------------------------------------------------
# Device registry
# ---------------------------------------------------------------------------
_devices: dict[str, dict] = {}


def _register_device(name: str, device_type: str, connection: str, config: dict = None) -> dict:
    """Register a device for communication."""
    _devices[name] = {
        "name": name,
        "type": device_type,  # serial, http, mock
        "connection": connection,  # /dev/ttyUSB0 or http://192.168.1.100
        "config": config or {},
        "registered_at": datetime.now().isoformat(),
        "last_command": None,
        "last_response": None,
    }
    return _devices[name]


def _get_device(name: str) -> dict:
    if name not in _devices:
        raise KeyError(f"Device '{name}' not registered. Use list_devices or register with send_command.")
    return _devices[name]


# ---------------------------------------------------------------------------
# Communication backends
# ---------------------------------------------------------------------------

def _send_serial(port: str, command: str, baudrate: int = 9600, timeout: float = 2.0) -> dict:
    """Send a command over serial port."""
    try:
        import serial
    except ImportError:
        return {"error": "Install pyserial: pip install pyserial"}

    try:
        with serial.Serial(port, baudrate, timeout=timeout) as ser:
            # Send command
            cmd = command.strip()
            if not cmd.endswith("\n"):
                cmd += "\n"
            ser.write(cmd.encode())
            ser.flush()

            # Read response
            time.sleep(0.1)
            response_lines = []
            deadline = time.time() + timeout
            while time.time() < deadline:
                if ser.in_waiting > 0:
                    line = ser.readline().decode(errors="replace").strip()
                    if line:
                        response_lines.append(line)
                    if line.startswith("ok") or line.startswith("error"):
                        break
                else:
                    time.sleep(0.05)

            return {
                "status": "ok",
                "port": port,
                "command": command,
                "response": response_lines,
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        return {"error": f"Serial error on {port}: {e}"}


def _send_http(url: str, command: str, method: str = "POST") -> dict:
    """Send a command to an HTTP-based device."""
    try:
        import urllib.request
        import urllib.error

        if method.upper() == "GET":
            # Append command as query parameter
            separator = "&" if "?" in url else "?"
            full_url = f"{url}{separator}cmd={urllib.parse.quote(command)}"
            req = urllib.request.Request(full_url)
        else:
            payload = json.dumps({"command": command}).encode()
            req = urllib.request.Request(
                url, data=payload,
                headers={"Content-Type": "application/json"},
                method="POST")

        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode(errors="replace")
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                data = {"raw": body}

            return {
                "status": "ok",
                "url": url,
                "command": command,
                "response": data,
                "http_status": resp.status,
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        return {"error": f"HTTP error for {url}: {e}"}


def _auto_discover_serial() -> list[dict]:
    """Discover serial devices."""
    devices = []

    # Check common serial ports
    common_ports = [
        "/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyACM0", "/dev/ttyACM1",
        "/dev/tty.usbserial-*", "/dev/tty.usbmodem*",
        "/dev/cu.usbserial-*", "/dev/cu.usbmodem*",
    ]

    # Try pyserial's list_ports
    try:
        from serial.tools import list_ports
        for port in list_ports.comports():
            devices.append({
                "port": port.device,
                "description": port.description,
                "manufacturer": port.manufacturer or "Unknown",
                "vid_pid": f"{port.vid:04x}:{port.pid:04x}" if port.vid else "N/A",
                "serial_number": port.serial_number or "N/A",
                "type": "serial",
            })
    except ImportError:
        # Fallback: check if common ports exist
        import glob
        for pattern in common_ports:
            for port in glob.glob(pattern):
                devices.append({
                    "port": port,
                    "description": "Detected serial port",
                    "type": "serial",
                })

    return devices


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------

def _list_devices() -> dict:
    """List all registered and discovered devices."""
    serial_devices = _auto_discover_serial()
    registered = list(_devices.values())

    return {
        "registered_devices": registered,
        "registered_count": len(registered),
        "discovered_serial": serial_devices,
        "discovered_count": len(serial_devices),
        "note": "Use send_command to communicate with any device. Serial ports and HTTP endpoints are auto-detected.",
    }


def _send_command(device: str, command: str, connection_type: str = "auto",
                  baudrate: int = 9600, timeout: float = 2.0) -> dict:
    """Send a command to a device."""
    estop = _check_emergency_stop()
    if estop:
        return {"error": estop}

    # Determine connection type
    if connection_type == "auto":
        if device.startswith("http://") or device.startswith("https://"):
            connection_type = "http"
        elif device.startswith("/dev/") or device.startswith("COM"):
            connection_type = "serial"
        else:
            # Check registered devices
            if device in _devices:
                dev = _devices[device]
                conn = dev["connection"]
                if conn.startswith("http"):
                    connection_type = "http"
                else:
                    connection_type = "serial"
                device = conn
            else:
                return {"error": f"Cannot determine connection type for '{device}'. Use /dev/... for serial or http://... for HTTP."}

    if connection_type == "serial":
        result = _send_serial(device, command, baudrate, timeout)
    elif connection_type == "http":
        result = _send_http(device, command)
    else:
        return {"error": f"Unknown connection type: {connection_type}"}

    # Update device registry
    device_name = device.split("/")[-1] if "/" in device else device
    if device_name in _devices:
        _devices[device_name]["last_command"] = command
        _devices[device_name]["last_response"] = result

    return result


def _read_sensor(device: str, sensor_id: str = "", connection_type: str = "auto",
                 baudrate: int = 9600) -> dict:
    """Read a sensor value from a device."""
    estop = _check_emergency_stop()
    if estop:
        return {"error": estop}

    # Build read command based on common protocols
    if sensor_id:
        command = f"READ {sensor_id}"
    else:
        command = "READ"

    result = _send_command(device, command, connection_type, baudrate, timeout=3.0)

    if result.get("status") == "ok":
        # Try to parse numeric sensor values from response
        response = result.get("response", [])
        parsed_values = {}
        for line in (response if isinstance(response, list) else [str(response)]):
            if isinstance(line, str):
                # Try to extract key=value or key:value pairs
                for match in re.finditer(r'(\w+)\s*[=:]\s*([-+]?\d*\.?\d+)', line):
                    key, val = match.groups()
                    try:
                        parsed_values[key] = float(val)
                    except ValueError:
                        parsed_values[key] = val

        result["parsed_values"] = parsed_values
        result["sensor_id"] = sensor_id

    return result


def _set_servo(device: str, channel: int, angle: float, speed: int = 0,
               connection_type: str = "auto", baudrate: int = 9600) -> dict:
    """Set a servo position."""
    estop = _check_emergency_stop()
    if estop:
        return {"error": estop}

    # Validate angle
    if angle < 0 or angle > 180:
        return {"error": f"Angle must be 0-180 degrees, got {angle}"}

    if channel < 0 or channel > 31:
        return {"error": f"Channel must be 0-31, got {channel}"}

    # Build servo command (compatible with common servo controllers)
    if speed > 0:
        command = f"SERVO {channel} {angle:.1f} {speed}"
    else:
        command = f"SERVO {channel} {angle:.1f}"

    result = _send_command(device, command, connection_type, baudrate)

    if result.get("status") == "ok":
        result["servo"] = {
            "channel": channel,
            "angle": angle,
            "speed": speed,
        }

    return result


def _run_gcode(device: str, gcode: str, connection_type: str = "auto",
               baudrate: int = 115200) -> dict:
    """Send G-code commands to a CNC/3D printer/robot."""
    estop = _check_emergency_stop()
    if estop:
        return {"error": estop}

    # Validate G-code basic format
    lines = [line.strip() for line in gcode.strip().split("\n") if line.strip() and not line.strip().startswith(";")]

    if len(lines) > 50:
        return {"error": f"Free tier limited to 50 G-code lines per call. Got {len(lines)}. Upgrade to Pro for unlimited."}

    results = []
    for line in lines:
        # Validate line format
        if not re.match(r'^[GMTSFXYZIJKEF\d\s.\-]+$', line.upper()):
            results.append({"line": line, "status": "skipped", "reason": "Invalid G-code format"})
            continue

        result = _send_command(device, line, connection_type, baudrate, timeout=10.0)
        results.append({
            "line": line,
            "status": result.get("status", "error"),
            "response": result.get("response", result.get("error", "")),
        })

        # Small delay between commands for device processing
        time.sleep(0.05)

    ok_count = sum(1 for r in results if r["status"] == "ok")
    return {
        "status": "ok" if ok_count > 0 else "error",
        "total_lines": len(lines),
        "successful": ok_count,
        "failed": len(lines) - ok_count,
        "results": results,
    }


def _emergency_stop(device: str = "", release: bool = False) -> dict:
    """Activate or release emergency stop."""
    global _emergency_stop_active

    with _emergency_stop_lock:
        if release:
            _emergency_stop_active = False
            status = "released"
        else:
            _emergency_stop_active = True
            status = "activated"

    result = {
        "status": status,
        "emergency_stop": not release,
        "timestamp": datetime.now().isoformat(),
        "message": "EMERGENCY STOP ACTIVATED. All commands blocked." if not release else "Emergency stop released. Commands enabled.",
    }

    # If a device is specified, also send hardware estop command
    if device and not release:
        try:
            hw_result = _send_serial(device, "M112\n", baudrate=115200, timeout=1.0) if device.startswith("/dev/") else _send_http(device, "ESTOP")
            result["hardware_stop"] = hw_result
        except Exception:
            result["hardware_stop"] = {"status": "attempted", "note": "Software stop is active regardless"}

    return result


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "Robotics Control MCP",
    instructions="IoT and robotics interface: list devices, send serial/HTTP commands, read sensors, control servos, send G-code, and emergency stop. Part of MEOK AI Labs' HARVI project.")


@mcp.tool()
def list_devices(api_key: str = "") -> dict:
    """List all available devices. Auto-discovers serial ports (USB, Arduino,
    3D printers) and shows previously registered HTTP devices.

    Returns port names, descriptions, manufacturer info, and VID/PID for USB devices.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    err = _check_rate_limit()
    if err:
        return {"error": err}
    try:
        return _list_devices()
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def send_command(device: str, command: str, connection_type: str = "auto",
                 baudrate: int = 9600, timeout: float = 2.0, api_key: str = "") -> dict:
    """Send a text command to a device and get its response.

    The device can be:
    - A serial port path: /dev/ttyUSB0, /dev/cu.usbmodem1401
    - An HTTP URL: http://192.168.1.100/api/command
    - A registered device name

    Connection type is auto-detected from the device string.

    Args:
        device: Serial port, HTTP URL, or registered device name
        command: Text command to send
        connection_type: 'serial', 'http', or 'auto' (default)
        baudrate: Serial baud rate (default: 9600)
        timeout: Response timeout in seconds (default: 2.0)
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    err = _check_rate_limit()
    if err:
        return {"error": err}
    try:
        return _send_command(device, command, connection_type, baudrate, timeout)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def read_sensor(device: str, sensor_id: str = "", connection_type: str = "auto",
                baudrate: int = 9600, api_key: str = "") -> dict:
    """Read a sensor value from a connected device. Sends a READ command
    and parses key=value pairs from the response.

    Args:
        device: Serial port, HTTP URL, or registered device name
        sensor_id: Optional sensor identifier (e.g. 'temperature', 'distance')
        connection_type: 'serial', 'http', or 'auto'
        baudrate: Serial baud rate (default: 9600)
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    err = _check_rate_limit()
    if err:
        return {"error": err}
    try:
        return _read_sensor(device, sensor_id, connection_type, baudrate)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def set_servo(device: str, channel: int, angle: float, speed: int = 0,
              connection_type: str = "auto", baudrate: int = 9600, api_key: str = "") -> dict:
    """Set a servo motor to a specific angle.

    Args:
        device: Serial port, HTTP URL, or registered device name
        channel: Servo channel number (0-31)
        angle: Target angle in degrees (0-180)
        speed: Movement speed (0 = max speed, higher = slower)
        connection_type: 'serial', 'http', or 'auto'
        baudrate: Serial baud rate (default: 9600)
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    err = _check_rate_limit()
    if err:
        return {"error": err}
    try:
        return _set_servo(device, channel, angle, speed, connection_type, baudrate)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def run_gcode(device: str, gcode: str, connection_type: str = "auto",
              baudrate: int = 115200, api_key: str = "") -> dict:
    """Send G-code commands to a CNC machine, 3D printer, or robot arm.
    Multiple lines can be sent at once (newline-separated).
    Lines starting with ; are treated as comments and skipped.

    Free tier: max 50 lines per call.

    Args:
        device: Serial port or HTTP URL of the machine
        gcode: G-code commands (newline-separated)
        connection_type: 'serial', 'http', or 'auto'
        baudrate: Serial baud rate (default: 115200 for most CNC/printers)
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    err = _check_rate_limit()
    if err:
        return {"error": err}
    try:
        return _run_gcode(device, gcode, connection_type, baudrate)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def emergency_stop(device: str = "", release: bool = False, api_key: str = "") -> dict:
    """Activate or release emergency stop. When active, ALL commands to ALL
    devices are blocked at the software level.

    If a device is specified, also sends a hardware emergency stop command
    (M112 for serial/G-code devices, ESTOP for HTTP devices).

    Args:
        device: Optional device to send hardware stop command to
        release: Set True to release the emergency stop and resume operations
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    # Emergency stop bypasses rate limiting
    try:
        return _emergency_stop(device, release)
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    mcp.run()
