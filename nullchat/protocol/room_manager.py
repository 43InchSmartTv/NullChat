from __future__ import annotations

import secrets
from nullchat.crypto.room import RoomCrypto, derive_room_key
from nullchat.protocol.room_registry import RoomRegistry


def create_room(chat_key: str, peer_public_key: str, registry: RoomRegistry) -> tuple[str, RoomCrypto]:
    room_id = secrets.token_hex(16)
    crypto = RoomCrypto(derive_room_key(chat_key.encode("utf-8"), room_id))
    registry.add_member(room_id, peer_public_key)
    return room_id, crypto


def join_room(room_id: str, chat_key: str, peer_public_key: str, registry: RoomRegistry) -> RoomCrypto:
    crypto = RoomCrypto(derive_room_key(chat_key.encode("utf-8"), room_id))
    registry.add_member(room_id, peer_public_key)
    return crypto