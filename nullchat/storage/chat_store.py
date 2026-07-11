from __future__ import annotations

import json
from pathlib import Path

from nullchat.crypto.room import RoomCrypto
from nullchat.protocol.consumer import PlaintextEvent


class ChatStoreError(Exception):
    pass

class ChatStore:
    def __init__(self, base_dir: str | Path | None = None):
        default = Path.home() / ".nullchat" / "chats"
        self._base = Path(base_dir) if base_dir is not None else default
        self._base.mkdir(parents=True, exist_ok=True)

    def _room_path(self, room_id: str) -> Path:
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in room_id)
        if not safe:
            raise ChatStoreError("room_id produces an empty filename")
        return self._base / f"{safe}.jsonl"

    def append(self, crypto: RoomCrypto, event: PlaintextEvent) -> None:
        # !! call every send/reciever
        body = json.dumps({
            "sender_id": event.sender_id,
            "timestamp": event.timestamp,
            "text": event.text,
        })
        nonce, ciphertext = crypto.encrypt(body)
        record = json.dumps({"nonce": nonce, "ciphertext": ciphertext})
        with open(self._room_path(event.room_id), "a", encoding="utf-8") as f:
            f.write(record + "\n")

    def load_history(self, crypto: RoomCrypto, room_id: str) -> list[PlaintextEvent]:
        path = self._room_path(room_id)
        if not path.exists():
            return []
        events: list[PlaintextEvent] = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    body = crypto.decrypt(record["nonce"], record["ciphertext"])
                    data = json.loads(body)
                except (json.JSONDecodeError, KeyError):
                    continue  # in case of one bad line
                except Exception:
                    continue # skip corrupted lines
                events.append(PlaintextEvent(
                    room_id=room_id,
                    sender_id=data["sender_id"],
                    timestamp=data["timestamp"],
                    text=data["text"],
                ))
        events.sort(key=lambda e: e.timestamp)
        return events

    def list_rooms(self) -> list[str]:
        return sorted(p.stem for p in self._base.glob("*.jsonl"))

    def has_history(self, room_id: str) -> bool:
        return self._room_path(room_id).exists()

    def delete_room(self, room_id: str) -> bool:
        path = self._room_path(room_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    def delete_all(self) -> int:
        return sum(self.delete_room(room) for room in self.list_rooms())
