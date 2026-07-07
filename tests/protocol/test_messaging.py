import os
import queue
import threading
import time

import pytest

from nullchat.crypto.room import RoomCrypto, derive_room_key
from nullchat.protocol.messages import Message, build_message, read_message
from nullchat.protocol.consumer import MessageConsumer



class FakeInboundMessage:
    def __init__(self, sender_peer_id: str, payload: bytes):
        self.sender_peer_id = sender_peer_id
        self.payload = payload


class FakeMessageBus:
    def __init__(self):
        self._q: queue.Queue = queue.Queue()

    def push(self, inbound: FakeInboundMessage):
        self._q.put(inbound)

    def recv(self, timeout=None):
        try:
            return self._q.get(timeout=timeout)
        except queue.Empty:
            return None


def test_message_roundtrip():
    key = os.urandom(32)
    crypto = RoomCrypto(key)

    msg = build_message(crypto, room_id="room-1", sender_id="peer-a", plaintext="hello")
    wire = msg.to_wire()

    received = Message.from_wire(wire)
    plaintext = read_message(crypto, received)

    assert plaintext == "hello"


def test_derive_room_key_is_deterministic():
    master = os.urandom(32)
    k1 = derive_room_key(master, "room-1")
    k2 = derive_room_key(master, "room-1")
    k3 = derive_room_key(master, "room-2")

    assert k1 == k2 # same room, same key every time
    assert k1 != k3         
    assert len(k1) == 32


def test_decrypt_fails_with_wrong_key():
    crypto_a = RoomCrypto(os.urandom(32))
    crypto_b = RoomCrypto(os.urandom(32))

    msg = build_message(crypto_a, room_id="room-1", sender_id="peer-a", plaintext="secret")

    with pytest.raises(Exception):
        read_message(crypto_b, msg)


def test_consumer_delivers_plaintext_event():
    key = os.urandom(32)
    crypto = RoomCrypto(key)
    bus = FakeMessageBus()
    consumer = MessageConsumer(bus)
    consumer.register_room("room-1", crypto)

    msg = build_message(crypto, room_id="room-1", sender_id="peer-a", plaintext="hi there")
    bus.push(FakeInboundMessage(sender_peer_id="peer-a", payload=msg.to_wire()))

    consumer.start()
    time.sleep(0.3)  # let the poll loop pick it up
    events = consumer.poll_ui_events()
    consumer.stop()

    assert len(events) == 1
    assert events[0].text == "hi there"
    assert events[0].room_id == "room-1"


def test_consumer_rejects_sender_mismatch():
    key = os.urandom(32)
    crypto = RoomCrypto(key)
    bus = FakeMessageBus()
    consumer = MessageConsumer(bus)
    consumer.register_room("room-1", crypto)

    msg = build_message(crypto, room_id="room-1", sender_id="peer-a", plaintext="spoofed?")
    bus.push(FakeInboundMessage(sender_peer_id="peer-mallory", payload=msg.to_wire()))

    consumer.start()
    time.sleep(0.3)
    events = consumer.poll_ui_events()
    consumer.stop()

    assert events == []


def test_consumer_ignores_unregistered_room():
    key = os.urandom(32)
    crypto = RoomCrypto(key)
    bus = FakeMessageBus()
    consumer = MessageConsumer(bus)

    msg = build_message(crypto, room_id="room-unknown", sender_id="peer-a", plaintext="hi")
    bus.push(FakeInboundMessage(sender_peer_id="peer-a", payload=msg.to_wire()))

    consumer.start()
    time.sleep(0.3)
    events = consumer.poll_ui_events()
    consumer.stop()

    assert events == []


def test_consumer_drops_malformed_payload():
    bus = FakeMessageBus()
    consumer = MessageConsumer(bus)
    bus.push(FakeInboundMessage(sender_peer_id="peer-a", payload=b"not json at all"))

    consumer.start()
    time.sleep(0.3)
    events = consumer.poll_ui_events()
    consumer.stop()

    assert events == [] 


def test_concurrent_register_room_while_consuming():
    bus = FakeMessageBus()
    consumer = MessageConsumer(bus)
    consumer.start()

    room_count = 20
    messages_per_room = 10
    cryptos = {f"room-{i}": RoomCrypto(os.urandom(32)) for i in range(room_count)}

    def register_rooms():
        for room_id, crypto in cryptos.items():
            consumer.register_room(room_id, crypto)
            time.sleep(0.001)

    def send_messages():
        for room_id, crypto in cryptos.items():
            for j in range(messages_per_room):
                msg = build_message(crypto, room_id=room_id, sender_id="peer-a", plaintext=f"msg-{j}")
                bus.push(FakeInboundMessage(sender_peer_id="peer-a", payload=msg.to_wire()))
                time.sleep(0.001)

    t1 = threading.Thread(target=register_rooms)
    t2 = threading.Thread(target=send_messages)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    time.sleep(0.5)  # drain remaining queue
    events = consumer.poll_ui_events()
    consumer.stop()

    assert len(events) > 0 # something got through
    room_ids_seen = {e.room_id for e in events}
    assert room_ids_seen.issubset(cryptos.keys())  # nothing malformed leaked through