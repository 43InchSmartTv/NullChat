from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING

from nullchat.network.message_bus import MessageBus
from nullchat.network.axl_bridge import InboundMessage
from nullchat.crypto.room import RoomCrypto
from nullchat.protocol.messages import Message, MSG_TYPE_JOIN

if TYPE_CHECKING:
    from nullchat.protocol.room_registry import RoomRegistry

@dataclass
class PlaintextEvent:
    room_id: str
    sender_id: str
    timestamp: float
    text: str


class MessageConsumer:
    def __init__(self, bus: MessageBus, registry: RoomRegistry | None = None, out_queue_size: int = 256):
        self._bus = bus
        self._registry = registry
        self._room_keys: dict[str, RoomCrypto] = {}
        self._room_keys_lock = threading.Lock()
        self._out: queue.Queue[PlaintextEvent] = queue.Queue(maxsize=out_queue_size)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._seen: set[tuple[str, float]] = set()  # (sender_id, timestamp) to prevent relay loops

    def register_room(self, room_id: str, crypto: RoomCrypto) -> None:
        with self._room_keys_lock:
            self._room_keys[room_id] = crypto

    def unregister_room(self, room_id: str) -> None:
        with self._room_keys_lock:
            self._room_keys.pop(room_id, None)

    def start(self) -> None: # starts a background thread
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._consume_loop, name="nullchat-consumer", daemon=True
        )
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)
            self._thread = None

    def poll_ui_events(self) -> list[PlaintextEvent]:
        events = []
        while True:
            try:
                events.append(self._out.get_nowait())
            except queue.Empty:
                break
        return events

    def get_crypto(self, room_id: str) -> RoomCrypto | None:
        with self._room_keys_lock:
            return self._room_keys.get(room_id)

    def _consume_loop(self) -> None: # background loop
        while not self._stop_event.is_set():
            inbound = self._bus.recv(timeout=0.1)
            if inbound is None:
                continue
            self._handle(inbound)

    def _handle(self, inbound: InboundMessage) -> None: 
        try:
            msg = Message.from_wire(inbound.payload) # decode the bytes into a messsage object
        except Exception:
            return

        # axl derives peer ID from IPv6, which only recovers ~26 chars of the key
        msg_prefix = msg.sender_id.lower()[:26]
        hdr_prefix = inbound.sender_peer_id.lower()[:26]
        if msg_prefix != hdr_prefix:
            return

        with self._room_keys_lock:
            crypto = self._room_keys.get(msg.room_id) # get the encryption keys
        if crypto is None:
            return 

        try:
            plaintext = msg.decrypt(crypto) # decrypt the message
        except Exception:
            return  

        msg_key = (msg.sender_id, msg.timestamp)
        if msg_key in self._seen:
            return
        self._seen.add(msg_key)
        
        # auto add anyone who can encrypt for this room
        if self._registry is not None:
            self._registry.add_member(msg.room_id, msg.sender_id)
            
            # relay to other members who might not know this sender
            for peer_id in self._registry.members_of(msg.room_id):
                if peer_id.lower() != msg.sender_id.lower():
                    try:
                        self._bus.send(peer_id, inbound.payload)
                    except Exception:
                        pass

        if msg.msg_type == MSG_TYPE_JOIN:
            return

        event = PlaintextEvent(msg.room_id, msg.sender_id, msg.timestamp, plaintext)
        try:
            self._out.put_nowait(event)
        except queue.Full:
            pass
