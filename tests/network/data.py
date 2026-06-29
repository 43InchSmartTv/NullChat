# sample axl /topology response shape for tests
# real response looks like:
#   our_ipv6, our_public_key, peers[], tree[]

import subprocess


def rand_peer():
    return subprocess.check_output(["openssl", "rand", "-hex", "32"], text=True).strip()


def rand_bytes(n=8):
    hex_str = subprocess.check_output(["openssl", "rand", "-hex", str(n)], text=True).strip()
    return bytes.fromhex(hex_str)


def make_topology(me_key, peer_key, root_key):
    return {
        "our_ipv6": "202:3490:755b:7b07:e38a:a043:4bb0:5aa5",
        "our_public_key": me_key,
        "peers": [
            {
                "uri": "tls://34.46.48.224:9001",
                "up": True,
                "inbound": False,
                "public_key": peer_key,
                "root": "",
                "port": 1,
                "coords": None,
            },
            {
                "uri": "tls://136.111.135.206:9001",
                "up": False,
                "inbound": False,
                "public_key": root_key,
                "root": "",
                "port": 2,
                "coords": None,
            },
        ],
        "tree": [
            {"public_key": peer_key, "parent": root_key, "sequence": 26969},
            {"public_key": me_key, "parent": root_key, "sequence": 15},
            {"public_key": root_key, "parent": root_key, "sequence": 49709},
        ],
    }
