from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from typing import Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

MASTER_KEY_LEN = 32
KDF_ITERATIONS = 600_000

PEER_ID_HEX = re.compile(r"^[0-9a-fA-F]{64}$")


class InvalidUserId(ValueError):
    pass

def normalize_user_id(user_id: str) -> str:
    normalized = user_id.strip().lower()
    if not PEER_ID_HEX.fullmatch(normalized):
        raise InvalidUserId("id must be a 64 char hex axl peer key")
    return normalized

def derive_master_key(passphrase: str, salt: bytes,
                      iterations: int = KDF_ITERATIONS) -> bytes:
    # ! easy call in add_room to wrap the key
    if len(salt) < 16:
        raise ValueError("salt must be 16+ bytes")
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=MASTER_KEY_LEN,
                     salt=salt, iterations=iterations)
    return kdf.derive(passphrase.encode("utf-8"))

def wrap_room_key(master_key: bytes, room_key: bytes) -> str:
    nonce = os.urandom(12)
    ciphertext = AESGCM(master_key).encrypt(nonce, room_key, None)
    return (nonce + ciphertext).hex()


def unwrap_room_key(master_key: bytes, wrapped: str) -> bytes:
    raw = bytes.fromhex(wrapped)
    if len(raw) < 28:
        raise ValueError("Wrapped room key is too short to be valid.")
    nonce, ciphertext = raw[:12], raw[12:]
    return AESGCM(master_key).decrypt(nonce, ciphertext, None)


@dataclass
class RoomRef:
    room_id: str
    display_name: str
    joined_at: float = field(default_factory=time.time)
    wrapped_key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"room_id": self.room_id, "display_name": self.display_name,
                "joined_at": self.joined_at, "wrapped_key": self.wrapped_key}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RoomRef:
        return cls(room_id=data["room_id"],
                   display_name=data.get("display_name", data["room_id"]),
                   joined_at=float(data.get("joined_at", 0.0)),
                   wrapped_key=data.get("wrapped_key"))

@dataclass
class UserProfile:
    user_id: str
    display_name: str
    created_at: float = field(default_factory=time.time)
    rooms: list[RoomRef] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.user_id = normalize_user_id(self.user_id)

    def is_self(self, peer_id: str) -> bool:
        return self.user_id == peer_id.strip().lower()

    def add_room(self, room_id: str, display_name: str | None = None,
                 wrapped_key: str | None = None) -> RoomRef:
        # !! create/join function but make sure wrap the chat key first
        # ALSO always follow with store.save_profile(profile) from user_store or the join is lost on close
        existing = self.get_room(room_id)
        if existing is not None:
            if wrapped_key is not None:
                existing.wrapped_key = wrapped_key
            return existing
        ref = RoomRef(room_id=room_id, display_name=display_name or room_id,
                      wrapped_key=wrapped_key)
        self.rooms.append(ref)
        return ref

    def room_key(self, room_id: str, master_key: bytes) -> bytes | None:
        # !! call after unlock(), when a user clicks a room on the side
        ref = self.get_room(room_id)
        if ref is None or ref.wrapped_key is None:
            return None
        return unwrap_room_key(master_key, ref.wrapped_key)

    def remove_room(self, room_id: str) -> bool:
        before = len(self.rooms)
        self.rooms = [r for r in self.rooms if r.room_id != room_id]
        return len(self.rooms) < before

    def get_room(self, room_id: str) -> RoomRef | None:
        return next((r for r in self.rooms if r.room_id == room_id), None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "display_name": self.display_name,
            "created_at": self.created_at,
            "rooms": [r.to_dict() for r in self.rooms],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserProfile:
        return cls(
            user_id=data["user_id"],
            display_name=data.get("display_name", "anonymous"),
            created_at=float(data.get("created_at", 0.0)),
            rooms=[RoomRef.from_dict(r) for r in data.get("rooms", [])],
        )
