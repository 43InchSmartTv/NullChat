import os

import pytest

from nullchat.crypto.room import RoomCrypto, derive_room_key
from nullchat.protocol.consumer import PlaintextEvent
from nullchat.storage.chat_store import ChatStore, ChatStoreError


@pytest.fixture
def master_key():
    return os.urandom(32)


@pytest.fixture
def crypto(master_key):
    return RoomCrypto(derive_room_key(master_key, "room-1"))


@pytest.fixture
def store(tmp_path):
    return ChatStore(base_dir=tmp_path)


def make_event(text, ts, room_id="room-1"):
    return PlaintextEvent(room_id=room_id, sender_id="a" * 64, timestamp=ts, text=text)


def test_append_and_load_roundtrip(store, crypto):
    store.append(crypto, make_event("hello", 1.0))
    store.append(crypto, make_event("world", 2.0))
    history = store.load_history(crypto, "room-1")
    assert [e.text for e in history] == ["hello", "world"]
    assert history[0].room_id == "room-1"

def test_wrong_key_raises(store, crypto, master_key):
    store.append(crypto, make_event("hi", 1.0))
    wrong = RoomCrypto(derive_room_key(os.urandom(32), "room-1"))
    with pytest.raises(ChatStoreError):
        store.load_history(wrong, "room-1")

def test_list_rooms_and_delete_all(store, crypto, master_key):
    other = RoomCrypto(derive_room_key(master_key, "room-2"))
    store.append(crypto, make_event("a", 1.0))
    store.append(other, make_event("b", 1.0, room_id="room-2"))
    assert store.list_rooms() == ["room-1", "room-2"]
    assert store.delete_all() == 2
    assert store.list_rooms() == []