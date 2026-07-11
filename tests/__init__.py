import sys
import time
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from nullchat.crypto.room import RoomCrypto, derive_room_key
from nullchat.protocol.consumer import MessageConsumer
from nullchat.protocol.room_registry import RoomRegistry
from nullchat.protocol.messages import Message
from nullchat.ui.chat_window import ChatWindow
from nullchat.autocomplete.engine import AutocompleteEngine
from nullchat.autocomplete.ngrams import load_counts_table
from nullchat.storage.chat_store import ChatStore
from nullchat.network.axl_bridge import InboundMessage
from nullchat.storage.user_store import UserStore


class DummyBusAdapter:
    def __init__(self, get_crypto, responder_name="dummy", delay_seconds=1.0):
        self.get_crypto = get_crypto  
        self.responder_name = responder_name
        self.delay_seconds = delay_seconds
        self.my_display_name = "you"  
        self._inbox = []
        self._lock = threading.Lock()

    def send(self, peer_id, payload):
        print(f"[dummy send] to {peer_id}: {len(payload)} bytes")

        try:
            msg = Message.from_wire(payload)
        except Exception as e:
            print(f"[dummy] could not parse outgoing message, skipping reply: {e}")
            return

        crypto = self.get_crypto(msg.room_id)
        if crypto is None:
            print(f"[dummy] no crypto registered for room {msg.room_id}, skipping reply")
            return

        try:
            plaintext = msg.decrypt(crypto)
        except Exception as e:
            print(f"[dummy] could not decrypt outgoing message: {e}")
            return

        def _reply():
            time.sleep(self.delay_seconds)
            reply_text = f"Hey {self.my_display_name}, got your message: '{plaintext}'"
            reply_msg = Message.encrypt(crypto, msg.room_id, self.responder_name, reply_text)
            with self._lock:
                self._inbox.append(
                    InboundMessage(
                        sender_peer_id=self.responder_name,
                        payload=reply_msg.to_wire(),
                    )
                )
            print(f"[dummy recv queued] {reply_text!r}")

        threading.Thread(target=_reply, daemon=True).start()

    def recv(self, timeout=None):
        start_time = time.monotonic()
        while True:
            with self._lock:
                if self._inbox:
                    return self._inbox.pop(0)

            if timeout is not None and (time.monotonic() - start_time) >= timeout:
                return None

            time.sleep(0.1)


if __name__ == "__main__":
    root_dir = Path(__file__).parent.parent

    my_peer_id = "a" * 64  # fake peer id

    dummy_peer_id = "b" * 64
    dummy_peer_profile_dir = Path.home() / ".nullchat_dummy_peer"
    dummy_peer_store = UserStore(base_dir=dummy_peer_profile_dir)
    if not dummy_peer_store.exists:
        dummy_peer_profile, _ = dummy_peer_store.create_user(
            user_id=dummy_peer_id,
            display_name="Dummy Bot",
            passphrase="dummy-passphrase",
        )
    else:
        dummy_peer_profile, _ = dummy_peer_store.unlock("dummy-passphrase")

    registry = RoomRegistry()
    registry.load_keys()

    consumer_holder = {}
    bus = DummyBusAdapter(
        get_crypto=lambda room_id: consumer_holder["consumer"].get_crypto(room_id),
        responder_name=dummy_peer_profile.display_name,
    )

    consumer = MessageConsumer(bus, registry=registry)
    consumer_holder["consumer"] = consumer
    consumer.start()

    # restore crypto keys
    for chat_key, room_id in registry._key_to_room.items():
        crypto = RoomCrypto(derive_room_key(chat_key.encode("utf-8"), room_id))
        consumer.register_room(room_id, crypto)
        registry.add_room(room_id)

    # load saved rooms from disk
    history_dir = Path.home() / ".nullchat" / "chats"
    if history_dir.exists():
        for file in history_dir.glob("*.jsonl"):
            room_id = file.stem
            registry.add_room(room_id)

    # autocomplete engine
    vocab_path = root_dir / "nullchat" / "autocomplete" / "vocab.tsv.gz"
    counts = load_counts_table(vocab_path)  # load vocabulary
    engine = AutocompleteEngine.from_counts(counts)
    chat_store = ChatStore()

    dummy_profile_dir = Path.home() / ".nullchat_dummy"
    store = UserStore(base_dir=dummy_profile_dir)
    if not store.exists:  # user profiles
        profile, master_key = store.create_user(
            user_id=my_peer_id,
            display_name="Me",
            passphrase="your-passphrase-here"
        )
    else:
        profile, master_key = store.unlock("your-passphrase-here")

    bus.my_display_name = profile.display_name 

    app = ChatWindow(consumer, engine, bus, my_peer_id, registry, chat_store,
                      profile, master_key, store)  # launch UI
    app.mainloop()
