from nullchat.network.topology import NetworkView


def test_parse_topology(topology):
    topo, me_key, peer_key, root_key = topology
    view = NetworkView.from_payload(topo)
    assert view.public_key_o == me_key
    assert view.ipv6_o == topo["our_ipv6"]
    assert len(view.peers) == 2


def test_up_peers(topology):
    topo, _, peer_key, _ = topology
    view = NetworkView.from_payload(topo)
    up = view.up_peers()
    assert len(up) == 1
    assert up[0].public_key == peer_key


def test_is_peer_up(topology):
    topo, _, peer_key, root_key = topology
    view = NetworkView.from_payload(topo)
    assert view.is_peer_up(peer_key)
    assert not view.is_peer_up(root_key)


def test_tree_position(topology):
    topo, me_key, _, root_key = topology
    pos = NetworkView.from_payload(topo).tree_position()
    assert pos.key_o == me_key
    assert pos.parent == root_key
    assert not pos.is_root
    assert pos.is_leaf
