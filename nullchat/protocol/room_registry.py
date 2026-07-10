from __future__ import annotations

class RoomRegistry: # connects users to rooms
    def __init__(self):
        self._room_to_peers: dict[str, list[str]] = {}

    def add_member(self, room_id: str, peer_public_key: str) -> None:
        self._room_to_peers.setdefault(room_id, [])
        if peer_public_key not in self._room_to_peers[room_id]:
            self._room_to_peers[room_id].append(peer_public_key)

    def members_of(self, room_id: str) -> list[str]:
        return list(self._room_to_peers.get(room_id, []))

    def is_known_room(self, room_id: str) -> bool:
        return room_id in self._room_to_peers