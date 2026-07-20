"""End-to-end test wiring the config and core subsystems together."""

from __future__ import annotations

from mellivor_kernel.config import load_config
from mellivor_kernel.core import Kernel, KernelState


def test_kernel_boots_from_loaded_configuration() -> None:
    config = load_config({"MELLIVOR_ENVIRONMENT": "test", "MELLIVOR_LOG_LEVEL": "DEBUG"})
    kernel = Kernel(config)

    kernel.start()

    state_after_start = kernel.state
    assert state_after_start == KernelState.RUNNING
    assert kernel.health().healthy is True

    kernel.shutdown()

    state_after_shutdown = kernel.state
    assert state_after_shutdown == KernelState.STOPPED
