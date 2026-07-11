import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from nullchat.crypto.room import RoomCrypto, derive_room_key
from nullchat.protocol.consumer import MessageConsumer
from nullchat.protocol.room_registry import RoomRegistry
from nullchat.ui.chat_window import ChatWindow
from nullchat.autocomplete.engine import AutocompleteEngine
from nullchat.autocomplete.ngrams import load_counts_table
from nullchat.network.node_manager import NodeManager
from nullchat.storage.chat_store import ChatStore
from nullchat.network.axl_bridge import InboundMessage
from nullchat.network.node_manager import NodeManagerConfig
from nullchat.storage.user_store import UserStore

class AxlBusAdapter:
    def __init__(self, bridge):
        self.bridge = bridge

    def send(self, peer_id, payload): # transmit data
        if isinstance(payload, str):
            payload = payload.encode('utf-8')
        
        self.bridge.send_to_peer(peer_id, payload)

    def recv(self, timeout=None):
        start_time = time.monotonic()
        while True:
            try:
                raw = self.bridge.poll_inbound()
                if raw is not None:
                    return InboundMessage(
                        sender_peer_id=raw.sender_peer_id,
                        payload=raw.payload
                    )
            except Exception as e:
                print(f"Receive error: {e}")

            if timeout is not None and (time.monotonic() - start_time) >= timeout:
                return None

            time.sleep(0.1)


        
if __name__ == "__main__":
    root_dir = Path(__file__).parent.parent

    # start the AXL node process
    config = NodeManagerConfig()
    manager = NodeManager(config)
    
    try:
        my_peer_id = manager.start()
    except Exception as e:
        print(f"\nError starting node: {e}")
        sys.exit(1)

    try:
        # live network
        bus = AxlBusAdapter(manager.bridge)
        registry = RoomRegistry()
        registry.load_keys()

        consumer = MessageConsumer(bus, registry=registry)
        consumer.start()

        # Restore crypto keys
        for chat_key, room_id in registry._key_to_room.items():
            crypto = RoomCrypto(derive_room_key(chat_key.encode("utf-8"), room_id))
            consumer.register_room(room_id, crypto)
            registry.add_room(room_id)
    
        # Load saved rooms from disk
        history_dir = Path.home() / ".nullchat" / "chats"
        if history_dir.exists():
            for file in history_dir.glob("*.jsonl"):
                room_id = file.stem
                registry.add_room(room_id)

        # autocomplete engine
        vocab_path = root_dir / "nullchat" / "autocomplete" / "vocab.tsv.gz"
        counts = load_counts_table(vocab_path) # load vocabulary
        engine = AutocompleteEngine.from_counts(counts)
        chat_store = ChatStore()

        # profiles
        store = UserStore()
        if not store.exists: # user nicknames
            profile, master_key = store.create_user(
                user_id=my_peer_id,
                display_name="Me",
                passphrase="your-passphrase-here"
            )
        else:
            # unlock existing user
            profile, master_key = store.unlock("your-passphrase-here")
        app = ChatWindow(consumer, engine, bus, my_peer_id, registry, chat_store,
        profile, master_key, store, vocab_counts=counts) # launch UI
        app.mainloop()

    finally:
        manager.stop() # shut down
