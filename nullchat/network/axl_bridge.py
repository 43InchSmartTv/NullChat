# send/recv/topology helpers for the local axl node
# started from gensyn's example client:
# https://github.com/gensyn-ai/axl/blob/main/examples/python-client/client.py

import re
from dataclasses import dataclass
from typing import Any

import requests

PEER_ID_HEX = re.compile(r"^[0-9a-fA-F]{64}$")


@dataclass
class BridgeConfig:
    host: str = "127.0.0.1"
    port: int = 9002
    timeout_secs: float = 5.0

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


@dataclass
class TopologySnapshot:
    ipv6_o: str
    public_key_o: str
    peers: tuple[dict[str, Any], ...]
    tree: tuple[dict[str, Any], ...]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> TopologySnapshot:
        return cls(
            ipv6_o=payload["our_ipv6"],
            public_key_o=payload["our_public_key"],
            peers=tuple(payload.get("peers", [])),
            tree=tuple(payload.get("tree", [])),
        )

    def connected_peers(self) -> tuple[dict[str, Any], ...]:
        return tuple(peer for peer in self.peers if peer.get("up"))


@dataclass
class InboundMessage:
    sender_peer_id: str
    payload: bytes


@dataclass
class SendReceipt:
    byte_count: int


class AxlBridgeError(Exception):
    pass


class BridgeUnreachable(AxlBridgeError):
    pass


class InvalidPeerId(AxlBridgeError):
    pass


class BridgeRequestError(AxlBridgeError):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")


class AxlBridge:
    def __init__(self, config: BridgeConfig | None = None) -> None:
        self._config = config or BridgeConfig()

    @property
    def config(self) -> BridgeConfig:
        return self._config

    def _url(self, path: str) -> str:
        return f"{self._config.base_url}{path}"

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        kwargs.setdefault("timeout", self._config.timeout_secs)
        try:
            return requests.request(method, self._url(path), **kwargs)
        except requests.RequestException as exc:
            raise BridgeUnreachable(
                f"could not reach axl bridge at {self._config.base_url}"
            ) from exc

    @staticmethod
    def normalize_peer_id(peer_id: str) -> str:
        normalized = peer_id.strip().lower()
        if not PEER_ID_HEX.fullmatch(normalized):
            raise InvalidPeerId("peer id must be 64 hex chars")
        return normalized

    def fetch_topology(self) -> TopologySnapshot:
        response = self._request("GET", "/topology")
        if response.status_code != 200:
            raise BridgeRequestError(response.status_code, response.text)
        return TopologySnapshot.from_payload(response.json())

    def send_to_peer(self, peer_id: str, payload: bytes) -> SendReceipt:
        destination = self.normalize_peer_id(peer_id)
        response = self._request(
            "POST",
            "/send",
            data=payload,
            headers={
                "X-Destination-Peer-Id": destination,
                "Content-Type": "application/octet-stream",
            },
        )
        if response.status_code == 200:
            sent = response.headers.get("X-Sent-Bytes", str(len(payload)))
            return SendReceipt(byte_count=int(sent))
        if response.status_code == 400:
            raise InvalidPeerId(response.text.strip() or "invalid destination peer id")
        raise BridgeRequestError(response.status_code, response.text)

    def poll_inbound(self) -> InboundMessage | None:
        response = self._request("GET", "/recv")
        if response.status_code == 204:
            return None
        if response.status_code == 200:
            sender = response.headers.get("X-From-Peer-Id", "")
            return InboundMessage(sender_peer_id=sender, payload=response.content)
        raise BridgeRequestError(response.status_code, response.text)
