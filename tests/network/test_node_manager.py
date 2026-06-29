from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nullchat.network.axl_bridge import BridgeUnreachable, TopologySnapshot
from nullchat.network.node_manager import NodeConfigNotFound, NodeManager, NodeManagerConfig, NodeStartupTimeout
from tests.network.data import rand_peer


def fake_config(tmp_path):
    binary = tmp_path / "node"
    cfg = tmp_path / "node-config.json"
    binary.write_text("")
    cfg.write_text("{}")
    return NodeManagerConfig(
        node_binary=binary,
        config_path=cfg,
        startup_timeout_secs=0.5,
        poll_interval_secs=0.05,
    )


def test_start(tmp_path):
    key = rand_peer()
    mgr = NodeManager(fake_config(tmp_path))
    snap = TopologySnapshot("202::1", key, (), ())
    proc = MagicMock()
    proc.poll.return_value = None

    with patch("nullchat.network.node_manager.subprocess.Popen", return_value=proc):
        with patch.object(mgr._bridge, "fetch_topology", return_value=snap):
            assert mgr.start() == key
    assert mgr.is_ready


def test_missing_config(tmp_path):
    cfg = fake_config(tmp_path)
    cfg.config_path = tmp_path / "nope.json"
    with pytest.raises(NodeConfigNotFound):
        NodeManager(cfg).start()


def test_startup_timeout(tmp_path):
    mgr = NodeManager(fake_config(tmp_path))
    proc = MagicMock()
    proc.poll.return_value = None

    with patch("nullchat.network.node_manager.subprocess.Popen", return_value=proc):
        with patch.object(mgr._bridge, "fetch_topology", side_effect=BridgeUnreachable("down")):
            with pytest.raises(NodeStartupTimeout):
                mgr.start()


def test_stop(tmp_path):
    key = rand_peer()
    mgr = NodeManager(fake_config(tmp_path))
    snap = TopologySnapshot("202::1", key, (), ())
    proc = MagicMock()
    proc.poll.return_value = None

    with patch("nullchat.network.node_manager.subprocess.Popen", return_value=proc):
        with patch.object(mgr._bridge, "fetch_topology", return_value=snap):
            mgr.start()
            mgr.stop()

    proc.terminate.assert_called_once()
    assert not mgr.is_running
