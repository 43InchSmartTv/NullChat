import pytest

from nullchat.storage.user_store import UserStore, UserStoreError, WrongPassphrase


@pytest.fixture
def store(tmp_path):
    return UserStore(base_dir=tmp_path)


def test_create_and_unlock(store):
    profile, key = store.create_user("a" * 64, "dudebro", "correct horse")
    profile2, key2 = store.unlock("correct horse")
    assert key == key2
    assert profile2.user_id == profile.user_id
    assert profile2.display_name == "dudebro"


def test_wrong_passphrase_rejected(store):
    store.create_user("a" * 64, "dudebro", "correct horse")
    with pytest.raises(WrongPassphrase):
        store.unlock("battery staple")

def test_cannot_create_twice(store):
    store.create_user("a" * 64, "dudebro", "pw")
    with pytest.raises(UserStoreError):
        store.create_user("b" * 64, "other", "pw")


def test_rooms_persist(store):
    profile, _ = store.create_user("a" * 64, "dudebro", "pw")
    profile.add_room("room-1", "study group")
    store.save_profile(profile)
    loaded = store.load_profile()
    assert loaded.get_room("room-1").display_name == "study group"


def test_unlock_without_profile(store):
    with pytest.raises(UserStoreError):
        store.unlock("pw")