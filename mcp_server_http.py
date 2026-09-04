#!/usr/bin/env python3
"""MCP server entry point for FreeCAD AI (HTTP mode).

Starts FreeCAD with GUI and exposes all built-in tools via the MCP
protocol over HTTP — Streamable HTTP at /mcp and the legacy HTTP+SSE
pair — so you can watch FreeCAD update in real-time while an AI client
calls tools.

Usage:
    # Start FreeCAD with this script as an argument:
    /path/to/FreeCAD.AppImage /path/to/freecad-ai/mcp_server_http.py

    # Or from inside a running FreeCAD via macro / exec:
    exec(open("/path/to/freecad-ai/mcp_server_http.py").read())

MCP configuration (Streamable HTTP — preferred):
{
    "freecad": {
      "type": "http",
      "url": "http://127.0.0.1:3000/mcp",
      "headers": {"Authorization": "Bearer <token from token file>"}
    }
}

The legacy HTTP+SSE endpoint stays available at http://127.0.0.1:3000/sse for
clients that only speak it. That transport was deprecated in the 2026-07-28
protocol revision with a removal window, so prefer /mcp for new configurations.

Environment variables:
    MCP_HOST  — listen address  (default: 127.0.0.1)
    MCP_PORT  — listen port     (default: 3000)
    MCP_ALLOWED_HOSTS — comma-separated Host headers the server answers to
                        (default: loopback only). Needed when binding a
                        non-loopback address: clients send the address they
                        dialled, so it must be named here. "*" is refused —
                        only explicit private-network hosts are supported.
    MCP_TOKEN_FILE — optional custom token file. It must already exist and
                     have private owner-only permissions.
"""

import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")

# __file__ is undefined when this script is run via exec(open(...).read())
# (a documented usage); guard so that path raises no NameError. In that mode
# the freecad-ai package is already importable from FreeCAD's Mod directory.
_script_path = globals().get("__file__")
if _script_path:
    script_dir = os.path.dirname(os.path.abspath(_script_path))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

import FreeCAD

if not FreeCAD.ActiveDocument:
    FreeCAD.newDocument("Unnamed")

# Config is a fallback for environment overrides and carries the authentication
# policy. Failure to load it must prevent an accidentally underconfigured
# listener from starting.
from freecad_ai.config import get_config
from freecad_ai.mcp.gui_server import (
    get_server_controller,
    resolve_allowed_hosts,
    resolve_server_address,
)

_cfg = get_config()

host, port = resolve_server_address(_cfg)
allowed_hosts = resolve_allowed_hosts(_cfg)

# start() binds before returning, so this line can no longer announce a
# server that never came up.
controller = get_server_controller()
url = controller.start(
    host, port, allowed_hosts=allowed_hosts, cfg=_cfg)

print(
    f"MCP server running on {url}; token file: {controller.token_file_path}",
    flush=True)
