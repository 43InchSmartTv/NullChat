from unittest.mock import MagicMock, patch

import pytest
import requests

from nullchat.network.axl_bridge import (
    AxlBridge,
    BridgeRequestError,
    BridgeUnreachable,
    InvalidPeerId,
)
from tests.network.data import rand_bytes


def fake_resp(code, json_data=None, content=b"", headers=None):
    r = MagicMock()
    r.status_code = code
    r.text = "err"
    r.content = content
    r.headers = headers or {}
    if json_data is not None:
        r.json.return_value = json_data
    return r


@patch("nullchat.network.axl_bridge.requests.request")
def test_fetch_topology(mock_req, topology):
    topo, me_key, _, _ = topology
    mock_req.return_value = fake_resp(200, json_data=topo)
    snap = AxlBridge().fetch_topology()
    assert snap.public_key_o == me_key
    assert snap.ipv6_o == topo["our_ipv6"]


@patch("nullchat.network.axl_bridge.requests.request")
def test_send(mock_req, peer_id, payload_bytes):
    mock_req.return_value = fake_resp(200, headers={"X-Sent-Bytes": str(len(payload_bytes))})
    receipt = AxlBridge().send_to_peer(peer_id, payload_bytes)
    assert receipt.byte_count == len(payload_bytes)


@patch("nullchat.network.axl_bridge.requests.request")
def test_recv_empty(mock_req):
    mock_req.return_value = fake_resp(204)
    assert AxlBridge().poll_inbound() is None


@patch("nullchat.network.axl_bridge.requests.request")
def test_recv_message(mock_req, peer_id):
    data = rand_bytes(6)
    mock_req.return_value = fake_resp(200, content=data, headers={"X-From-Peer-Id": peer_id})
    msg = AxlBridge().poll_inbound()
    assert msg.sender_peer_id == peer_id
    assert msg.payload == data


def test_bad_peer_id():
    with pytest.raises(InvalidPeerId):
        AxlBridge.normalize_peer_id("lol")


@patch("nullchat.network.axl_bridge.requests.request")
def test_bridge_down(mock_req):
    mock_req.side_effect = requests.ConnectionError
    with pytest.raises(BridgeUnreachable):
        AxlBridge().fetch_topology()


@patch("nullchat.network.axl_bridge.requests.request")
def test_send_fails(mock_req, peer_id, payload_bytes):
    mock_req.return_value = fake_resp(502, content=b"nope")
    with pytest.raises(BridgeRequestError) as err:
        AxlBridge().send_to_peer(peer_id, payload_bytes)
    assert err.value.status_code == 502
