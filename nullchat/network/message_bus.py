
import queue
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from nullchat.network.axl_bridge import (
    AxlBridge,
    AxlBridgeError,
    BridgeUnreachable,
    InboundMessage,
    SendReceipt,
)


@dataclass
class MessageBusConfig:
    poll_interval_secs: float = 0.05
    inbound_queue_size: int = 256


class MessageBusError(Exception):
    """Base error for message bus operations."""


class MessageBus:
    """Background poller for inbound traffic and a simple outbound send API."""

    def __init__(
        self,
        bridge: AxlBridge,
        config: MessageBusConfig | None = None,
        on_message: Callable[[InboundMessage], None] | None = None,
    ) -> None:
        self._bridge = bridge
        self._config = config or MessageBusConfig()
        self._on_message = on_message
        self._inbound: queue.Queue[InboundMessage] = queue.Queue(
            maxsize=self._config.inbound_queue_size
        )
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_error: Exception | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def last_error(self) -> Exception | None:
        return self._last_error

    def start(self) -> None:
        if self.is_running:
            return

        self._stop_event.clear()
        self._last_error = None
        self._thread = threading.Thread(
            target=self._poll_loop,
            name="nullchat-message-bus",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        if not self.is_running:
            return

        self._stop_event.set()
        assert self._thread is not None
        self._thread.join(timeout=timeout)
        self._thread = None

    def send(self, peer_id: str, payload: bytes) -> SendReceipt:
        return self._bridge.send_to_peer(peer_id, payload)

    def recv(self, timeout: float | None = None) -> InboundMessage | None:
        try:
            if timeout is None:
                return self._inbound.get_nowait()
            return self._inbound.get(timeout=timeout)
        except queue.Empty:
            return None

    def drain(self) -> list[InboundMessage]:
        messages: list[InboundMessage] = []
        while True:
            message = self.recv()
            if message is None:
                break
            messages.append(message)
        return messages

    def _poll_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                message = self._bridge.poll_inbound()
            except BridgeUnreachable as exc:
                self._last_error = exc
                self._wait_or_stop()
                continue
            except AxlBridgeError as exc:
                self._last_error = exc
                self._wait_or_stop()
                continue

            if message is None:
                self._wait_or_stop()
                continue

            self._deliver(message)

    def _deliver(self, message: InboundMessage) -> None:
        if self._on_message is not None:
            try:
                self._on_message(message)
            except Exception as exc:
                self._last_error = exc

        try:
            self._inbound.put_nowait(message)
        except queue.Full:
            try:
                self._inbound.get_nowait()
            except queue.Empty:
                pass
            self._inbound.put_nowait(message)

    def _wait_or_stop(self) -> None:
        self._stop_event.wait(self._config.poll_interval_secs)
