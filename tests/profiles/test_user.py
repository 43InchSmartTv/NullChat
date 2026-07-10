import pytest

from nullchat.profiles.user import (
    InvalidUserId,
    UserProfile,
    derive_master_key,
    normalize_user_id,
)

PEER_ID = "3f" * 32  # fake valid hex


def test_derive_master_key_deterministic():
    salt = b"0123456789abcdef"
    k1 = derive_master_key("passphrase", salt, iterations=1_000)
    k2 = derive_master_key("passphrase", salt, iterations=1_000)
    assert k1 == k2 and len(k1) == 32
    assert derive_master_key("other", salt, iterations=1_000) != k1


def test_derive_rejects_short_salt():
    with pytest.raises(ValueError):
        derive_master_key("pw", b"short")


def test_normalize_user_id_lowercases_and_strips():
    assert normalize_user_id(f"  {PEER_ID.upper()}  ") == PEER_ID


@pytest.mark.parametrize("bad", ["", "abc", "z" * 64, "3f" * 31, "3f" * 33])
def test_normalize_rejects_non_peer_ids(bad):
    with pytest.raises(InvalidUserId):
        normalize_user_id(bad)


def test_profile_normalizes_user_id_on_construction():
    profile = UserProfile(user_id=PEER_ID.upper(), display_name="dudebro")
    assert profile.user_id == PEER_ID


def test_profile_rejects_invalid_user_id():
    with pytest.raises(InvalidUserId):
        UserProfile(user_id="not-a-peer-key", display_name="dudebro")

def test_wrap_and_unwrap_room_key():
    from nullchat.profiles.user import unwrap_room_key, wrap_room_key
    master_key = bytes(range(32))
    room_key = bytes.fromhex("771c0dbece96e66ba0609cf95e6383c027a3e87c1a9d206fadcf90b3c6" + "aabbcc")[:32]
    wrapped = wrap_room_key(master_key, room_key)
    assert unwrap_room_key(master_key, wrapped) == room_key
    assert room_key.hex() not in wrapped

def test_unwrap_with_wrong_master_key_fails():
    import pytest as _pytest
    from nullchat.profiles.user import unwrap_room_key, wrap_room_key
    wrapped = wrap_room_key(b"a" * 32, b"k" * 32)
    with _pytest.raises(Exception):
        unwrap_room_key(b"b" * 32, wrapped)