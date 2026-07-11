from __future__ import annotations

import json
import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from nullchat.profiles.user import UserProfile, derive_master_key

_VERIFIER_PLAINTEXT = b"nullchat-master-key-ok"


class UserStoreError(Exception):
    pass


class WrongPassphrase(UserStoreError):
    pass

class UserStore:
    def __init__(self, base_dir: str | Path | None = None):
        default = Path.home() / ".nullchat"
        self._base = Path(base_dir) if base_dir is not None else default
        self._base.mkdir(parents=True, exist_ok=True)
        self._profile_path = self._base / "profile.json"

    @property
    def exists(self) -> bool:
        return self._profile_path.exists()

    def create_user(self, user_id: str, display_name: str,
                    passphrase: str) -> tuple[UserProfile, bytes]:
        # !! first run ever, create user
        if self.exists:
            raise UserStoreError("a profile already exists, unlock it instead")
        if not passphrase:
            raise UserStoreError("passphrase must not be empty")

        salt = os.urandom(16)
        master_key = derive_master_key(passphrase, salt)

        # we can't store the key or a password hash
        nonce = os.urandom(12)
        verifier_ct = AESGCM(master_key).encrypt(nonce, _VERIFIER_PLAINTEXT, None)

        profile = UserProfile(user_id=user_id, display_name=display_name)
        self._write({
            "profile": profile.to_dict(),
            "kdf_salt": salt.hex(),
            "verifier_nonce": nonce.hex(),
            "verifier_ct": verifier_ct.hex(),
        })
        return profile, master_key

    def unlock(self, passphrase: str) -> tuple[UserProfile, bytes]:
        # !! call everytime app is opened
        data = self._read()
        salt = bytes.fromhex(data["kdf_salt"])
        master_key = derive_master_key(passphrase, salt)
        try:
            AESGCM(master_key).decrypt(
                bytes.fromhex(data["verifier_nonce"]),
                bytes.fromhex(data["verifier_ct"]),
                None,
            )
        except Exception as exc:
            raise WrongPassphrase("passphrase did not unlock this profile") from exc
        return UserProfile.from_dict(data["profile"]), master_key

    def load_profile(self) -> UserProfile:  # metadata only, no key material
        return UserProfile.from_dict(self._read()["profile"])

    def save_profile(self, profile: UserProfile) -> None:
        data = self._read()
        data["profile"] = profile.to_dict()
        self._write(data)

    def delete(self) -> bool:
        if not self.exists:
            return False
        self._profile_path.unlink()
        return True

    def _read(self) -> dict:
        if not self.exists:
            raise UserStoreError("no profile on disk, create a user first")
        try:
            return json.loads(self._profile_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise UserStoreError("profile file is corrupted") from exc

    def _write(self, data: dict) -> None:
        tmp = self._profile_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(self._profile_path)
