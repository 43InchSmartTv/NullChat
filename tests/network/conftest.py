import pytest

from tests.network.data import make_topology, rand_bytes, rand_peer


@pytest.fixture
def peer_id():
    return rand_peer()


@pytest.fixture
def payload_bytes():
    return rand_bytes(8)


@pytest.fixture
def topology():
    me, peer, root = rand_peer(), rand_peer(), rand_peer()
    return make_topology(me, peer, root), me, peer, root
