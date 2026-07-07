from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nullchat.network.axl_bridge import TopologySnapshot


@dataclass
class PeerRecord:
    uri: str
    public_key: str
    up: bool
    inbound: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PeerRecord:
        return cls(
            uri=data["uri"],
            public_key=data["public_key"],
            up=bool(data.get("up")),
            inbound=bool(data.get("inbound")),
        )


@dataclass
class TreePosition:
    key_o: str
    parent: str | None
    children: set[str]
    is_root: bool
    is_leaf: bool


@dataclass
class NetworkView:
    ipv6_o: str
    public_key_o: str
    peers: tuple[PeerRecord, ...]
    tree: tuple[dict[str, Any], ...]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> NetworkView:
        return cls(
            ipv6_o=payload["our_ipv6"],
            public_key_o=payload["our_public_key"],
            peers=tuple(PeerRecord.from_dict(p) for p in payload.get("peers", [])),
            tree=tuple(payload.get("tree", [])),
        )

    @classmethod
    def from_snapshot(cls, snapshot: TopologySnapshot) -> NetworkView:
        return cls(
            ipv6_o=snapshot.ipv6_o,
            public_key_o=snapshot.public_key_o,
            peers=tuple(PeerRecord.from_dict(p) for p in snapshot.peers),
            tree=snapshot.tree,
        )

    def up_peers(self) -> tuple[PeerRecord, ...]:
        return tuple(peer for peer in self.peers if peer.up)

    def is_peer_up(self, peer_id: str) -> bool:
        normalized = peer_id.lower()
        return any(p.public_key.lower() == normalized and p.up for p in self.peers)

    def tree_position(self) -> TreePosition:
        tree_map = {
            entry["public_key"]: entry.get("parent") or None
            for entry in self.tree
        }
        key_o = self.public_key_o
        parent = tree_map.get(key_o)
        children = {k for k, p in tree_map.items() if p == key_o}

        return TreePosition(
            key_o=key_o,
            parent=parent,
            children=children,
            is_root=parent is None or parent == key_o,
            is_leaf=not children,
        )
