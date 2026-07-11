import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from nullchat.network.axl_bridge import AxlBridge, BridgeConfig, BridgeUnreachable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
NODE_BINARY_NAME = "node.exe" if sys.platform == "win32" else "node"


@dataclass
class NodeManagerConfig:
    node_binary: Path = field(default_factory=lambda: PROJECT_ROOT / "axl" / NODE_BINARY_NAME)
    config_path: Path = field(default_factory=lambda: PROJECT_ROOT / "axl" / "node-config.json")
    bridge: BridgeConfig = field(default_factory=BridgeConfig)
    startup_timeout_secs: float = 30.0
    poll_interval_secs: float = 0.25


class NodeManagerError(Exception):
    """Base error for AXL node lifecycle operations."""


class NodeConfigNotFound(NodeManagerError):
    """The node config file does not exist."""


class NodeStartupTimeout(NodeManagerError):
    """The AXL node did not become ready in time."""


class NodeManager:
    """Start, monitor, and stop the local AXL Go node process."""

    def __init__(self, config: NodeManagerConfig | None = None) -> None:
        self._config = config or NodeManagerConfig()
        self._bridge = AxlBridge(self._config.bridge)
        self._process: subprocess.Popen[bytes] | None = None
        self._public_key_o: str | None = None

    @property
    def bridge(self) -> AxlBridge:
        return self._bridge

    @property
    def is_ready(self) -> bool:
        return self._public_key_o is not None and self.is_running

    @property
    def public_key_o(self) -> str | None:
        return self._public_key_o

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def start(self) -> str:
        if self.is_running and self._public_key_o is not None:
            return self._public_key_o

        if self.is_running:
            return self._wait_for_ready()

        self._validate_paths()
        self._process = subprocess.Popen(
            [
                str(self._config.node_binary),
                "-config",
                str(self._config.config_path),
            ],
            cwd=self._config.config_path.parent,
        )
        return self._wait_for_ready()

    def stop(self) -> None:
        if self._process is None:
            return

        if self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()

        self._process = None
        self._public_key_o = None

    def refresh_identity(self) -> str:
        snapshot = self._bridge.fetch_topology()
        self._public_key_o = snapshot.public_key_o
        return self._public_key_o

    def _validate_paths(self) -> None:
        if not self._config.config_path.is_file():
            raise NodeConfigNotFound(f"Config not found: {self._config.config_path}")
        if not self._config.node_binary.is_file():
            raise NodeManagerError(f"Node binary not found: {self._config.node_binary}")

    def _wait_for_ready(self) -> str:
        deadline = time.monotonic() + self._config.startup_timeout_secs

        while time.monotonic() < deadline:
            if self._process and self._process.poll() is not None:
                raise NodeManagerError("AXL node process exited during startup")

            try:
                return self.refresh_identity()
            except BridgeUnreachable:
                time.sleep(self._config.poll_interval_secs)

        self.stop()
        raise NodeStartupTimeout(
            f"AXL node did not become ready within {self._config.startup_timeout_secs}s"
        )
