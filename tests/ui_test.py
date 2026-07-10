import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from nullchat.protocol.consumer import MessageConsumer
from nullchat.protocol.room_registry import RoomRegistry
from nullchat.ui.chat_window import ChatWindow
from nullchat.autocomplete.engine import AutocompleteEngine
from nullchat.autocomplete.ngrams import load_counts_table
from nullchat.network.node_manager import NodeManager

class AxlBusAdapter:
    def __init__(self, bridge):
        self.bridge = bridge

    def send(self, peer_id, payload): # transmit data
        print(f"[live send] to {peer_id}...")
        if isinstance(payload, str):
            payload = payload.encode('utf-8')
        
        try:
            self.bridge.send_to_peer(peer_id, payload)
            print("Message accepted.")
        except Exception as e:
            print(f"Failed: {e}")

    def recv(self, timeout=None): # receive/get data
        start_time = time.monotonic()
        while True:
            try:
                msg = self.bridge.poll_inbound()
                if msg is not None:
                    return msg
            except Exception as e:
                print(f"Receive error: {e}")
            
            if timeout is not None and (time.monotonic() - start_time) >= timeout:
                return None
                
            time.sleep(0.1)
        
if __name__ == "__main__":
    root_dir = Path(__file__).parent.parent

    # start the AXL node process
    from nullchat.network.node_manager import NodeManagerConfig
    config = NodeManagerConfig(node_binary=root_dir / "axl" / "node.exe")
    manager = NodeManager(config)
    
    try:
        my_peer_id = manager.start()
    except Exception as e:
        print(f"\nError starting node: {e}")
        sys.exit(1)

    try:
        # live network
        bus = AxlBusAdapter(manager.bridge)
        consumer = MessageConsumer(bus)
        consumer.start()
        registry = RoomRegistry()

        # autocomplete engine
        vocab_path = root_dir / "nullchat" / "autocomplete" / "vocab.tsv.gz"
        counts = load_counts_table(vocab_path) # load vocabulary
        engine = AutocompleteEngine.from_counts(counts)
        
        app = ChatWindow(consumer, engine, bus, my_peer_id, registry) # launch UI
        app.mainloop()

    finally:
        manager.stop() # shut down