from __future__ import annotations
import json
from pathlib import Path

class RoomRegistry: # connects users to rooms
    def __init__(self):
        self._room_to_peers: dict[str, list[str]] = {}
        self._key_to_room: dict[str, str] = {}  
        self._rooms = set() 
        self._key_file = Path.home() / ".nullchat" / "keys.json"


    def add_member(self, room_id: str, peer_public_key: str) -> None:
        self._room_to_peers.setdefault(room_id, [])
        if peer_public_key not in self._room_to_peers[room_id]:
            self._room_to_peers[room_id].append(peer_public_key)
            self.save_keys()

    def members_of(self, room_id: str) -> list[str]:
        return list(self._room_to_peers.get(room_id, []))

    def is_known_room(self, room_id: str) -> bool:
        return room_id in self._room_to_peers
    
    def map_chat_key(self, chat_key, room_id):
        self._key_to_room[chat_key] = room_id
        self.save_keys()

    def save_keys(self):
        data = {
            "keys": self._key_to_room,
            "members": self._room_to_peers,
        }
        self._key_file.parent.mkdir(parents=True, exist_ok=True)
        self._key_file.write_text(json.dumps(data))

    def load_keys(self):
        if not self._key_file.exists():
            return
        data = json.loads(self._key_file.read_text())
        self._key_to_room = data.get("keys", {})
        self._room_to_peers = data.get("members", {})

    def lookup_room_id(self, chat_key):
        return self._key_to_room.get(chat_key)
    
    def add_room(self, room_id: str):
        self._rooms.add(room_id)

    def get_all_rooms(self):
        return list(self._rooms)
