"""Built-in demonstration tools.

These exist only to validate the tool runtime end-to-end. They are not a
starting point for real product tools, and none of them call any external
API.
"""

from __future__ import annotations

from mellivor_kernel.tools.builtin.echo_tool import EchoTool
from mellivor_kernel.tools.builtin.health_check_tool import HealthCheckTool
from mellivor_kernel.tools.builtin.version_tool import VersionTool

__all__ = ["EchoTool", "HealthCheckTool", "VersionTool"]
