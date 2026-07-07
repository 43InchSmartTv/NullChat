import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes


def derive_room_key(master_key: bytes, room_id: str) -> bytes: # derives a unique key for each room
    hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=room_id.encode("utf-8"))
    return hkdf.derive(master_key)


class RoomCrypto: # each RoomCrypto is tied to one and only one room_key
    def __init__(self, room_key: bytes):
        if len(room_key) != 32:
            raise ValueError("room_key must be 32 bytes for AES-256-GCM")
        self._aead = AESGCM(room_key)

    def encrypt(self, plaintext: str): # encrypts a plaintext UTF-8 string using AES-GCM
        nonce = os.urandom(12)
        ct = self._aead.encrypt(nonce, plaintext.encode("utf-8"), None)
        return nonce.hex(), ct.hex()

    def decrypt(self, nonce_hex: str, ciphertext_hex: str) -> str: # decrypts AES-GCM ciphertext into plaintext
        nonce = bytes.fromhex(nonce_hex)
        ct = bytes.fromhex(ciphertext_hex)
        return self._aead.decrypt(nonce, ct, None).decode("utf-8")