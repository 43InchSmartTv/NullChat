from nullchat.network.axl_bridge import InboundMessage, SendReceipt
from nullchat.network.message_bus import MessageBus, MessageBusConfig
from tests.network.data import rand_bytes


class FakeBridge:
    def __init__(self, msgs=None):
        self.msgs = list(msgs or [])
        self.sent = []

    def send_to_peer(self, peer_id, payload):
        self.sent.append((peer_id, payload))
        return SendReceipt(byte_count=len(payload))

    def poll_inbound(self):
        if not self.msgs:
            return None
        return self.msgs.pop(0)


def test_send(peer_id, payload_bytes):
    bridge = FakeBridge()
    bus = MessageBus(bridge)
    bus.send(peer_id, payload_bytes)
    assert bridge.sent == [(peer_id, payload_bytes)]


def test_recv_loop(peer_id):
    data = rand_bytes(5)
    bridge = FakeBridge([None, InboundMessage(peer_id, data)])
    bus = MessageBus(bridge, config=MessageBusConfig(poll_interval_secs=0.01))
    bus.start()
    try:
        msg = bus.recv(timeout=1.0)
        assert msg.payload == data
    finally:
        bus.stop()


def test_drain(peer_id):
    a, b = rand_bytes(3), rand_bytes(3)
    bus = MessageBus(FakeBridge())
    bus._deliver(InboundMessage(peer_id, a))
    bus._deliver(InboundMessage(peer_id, b))
    assert len(bus.drain()) == 2


def test_queue_full(peer_id):
    bus = MessageBus(FakeBridge(), config=MessageBusConfig(inbound_queue_size=1))
    bus._deliver(InboundMessage(peer_id, b"old"))
    bus._deliver(InboundMessage(peer_id, b"new"))
    assert bus.recv().payload == b"new"
