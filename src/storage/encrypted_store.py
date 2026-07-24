import asyncio
import base64
import binascii
import hashlib
import hmac
import json
import os
import tempfile
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any, TypeVar

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

try:
    import fcntl
except ImportError as error:  # pragma: no cover - deployment is Linux/macOS.
    raise RuntimeError("Encrypted file storage requires POSIX file locking") from error

Document = dict[str, Any]
Result = TypeVar("Result")
_MAGIC = b"COMEM1\x00"


class EncryptedFileError(RuntimeError):
    pass


class EncryptedUserStore:
    """Atomic AES-256-GCM envelopes, one opaque file per authenticated user."""

    def __init__(self, root: str, encoded_master_key: str) -> None:
        try:
            key = base64.b64decode(encoded_master_key, validate=True)
        except (binascii.Error, ValueError) as error:
            raise EncryptedFileError("Storage key is not valid base64") from error
        if len(key) != 32:
            raise EncryptedFileError("Storage key must contain exactly 32 bytes")
        self._root = Path(root).expanduser().resolve()
        self._key = key

    @property
    def root(self) -> Path:
        return self._root

    def user_path(self, user_identifier: str) -> Path:
        return self._root / f"{self._file_id(user_identifier)}.enc"

    async def initialize(self) -> None:
        await asyncio.to_thread(self._initialize_sync)

    async def health_check(self) -> bool:
        try:
            await self.initialize()
            return os.access(self._root, os.R_OK | os.W_OK | os.X_OK)
        except OSError:
            return False

    async def read_user(self, user_identifier: str) -> Document:
        return await asyncio.to_thread(self._read_user_sync, user_identifier)

    async def mutate_user(
        self,
        user_identifier: str,
        mutation: Callable[[Document], Result],
    ) -> Result:
        return await asyncio.to_thread(
            self._mutate_user_sync, user_identifier, mutation
        )

    async def find_thread_owner(self, thread_id: str) -> str | None:
        return await asyncio.to_thread(self._find_thread_owner_sync, thread_id)

    async def find_user_by_id(self, user_id: str) -> str | None:
        return await asyncio.to_thread(self._find_user_by_id_sync, user_id)

    async def all_user_identifiers(self) -> list[str]:
        return await asyncio.to_thread(self._all_user_identifiers_sync)

    def public_location(self, user_identifier: str) -> str:
        return str(self.user_path(user_identifier))

    def _initialize_sync(self) -> None:
        self._root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self._root, 0o700)

    def _file_id(self, user_identifier: str) -> str:
        return hmac.new(
            self._key,
            user_identifier.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _path_from_file_id(self, file_id: str) -> Path:
        return self._root / f"{file_id}.enc"

    def _lock_path(self, file_id: str) -> Path:
        return self._root / f".{file_id}.lock"

    def _file_key(self, file_id: str) -> bytes:
        return hmac.new(
            self._key,
            f"envelope:{file_id}".encode(),
            hashlib.sha256,
        ).digest()

    def _empty_document(self, user_identifier: str) -> Document:
        return {
            "version": 1,
            "user": {
                "id": "",
                "identifier": user_identifier,
                "metadata": {},
                "createdAt": None,
            },
            "threads": {},
            "memories": [],
            "preferences": {
                "memory_enabled": True,
                "automatic_memory_enabled": True,
                "allow_global_memory": True,
                "allow_thread_memory": True,
            },
            "summaries": {},
            "audits": [],
        }

    def _read_user_sync(self, user_identifier: str) -> Document:
        self._initialize_sync()
        file_id = self._file_id(user_identifier)
        path = self._path_from_file_id(file_id)
        if not path.exists():
            return self._empty_document(user_identifier)
        return self._decrypt(path.read_bytes(), file_id)

    def _mutate_user_sync(
        self,
        user_identifier: str,
        mutation: Callable[[Document], Result],
    ) -> Result:
        self._initialize_sync()
        file_id = self._file_id(user_identifier)
        lock_path = self._lock_path(file_id)
        lock_path.touch(mode=0o600, exist_ok=True)
        os.chmod(lock_path, 0o600)
        with lock_path.open("rb") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            document = self._read_user_sync(user_identifier)
            result = mutation(document)
            self._atomic_write(file_id, document)
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        return result

    def _atomic_write(self, file_id: str, document: Document) -> None:
        plaintext = json.dumps(
            document,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
        payload = self._encrypt(plaintext, file_id)
        descriptor, temporary = tempfile.mkstemp(
            dir=self._root,
            prefix=f".{file_id}.",
            suffix=".tmp",
        )
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self._path_from_file_id(file_id))
            directory = os.open(self._root, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def _encrypt(self, plaintext: bytes, file_id: str) -> bytes:
        nonce = os.urandom(12)
        associated = f"chainlit-user:{file_id}:v1".encode()
        ciphertext = AESGCM(self._file_key(file_id)).encrypt(
            nonce, plaintext, associated
        )
        return _MAGIC + nonce + bytes(ciphertext)

    def _decrypt(self, payload: bytes, file_id: str) -> Document:
        if not payload.startswith(_MAGIC) or len(payload) < len(_MAGIC) + 28:
            raise EncryptedFileError("Encrypted user file has an invalid envelope")
        nonce_start = len(_MAGIC)
        nonce = payload[nonce_start : nonce_start + 12]
        ciphertext = payload[nonce_start + 12 :]
        associated = f"chainlit-user:{file_id}:v1".encode()
        try:
            plaintext = AESGCM(self._file_key(file_id)).decrypt(
                nonce, ciphertext, associated
            )
            document = json.loads(plaintext)
        except Exception as error:
            raise EncryptedFileError(
                "Encrypted user file failed authentication"
            ) from error
        if not isinstance(document, dict) or document.get("version") != 1:
            raise EncryptedFileError("Unsupported encrypted user file version")
        return deepcopy(document)

    def _iter_documents(self) -> list[Document]:
        self._initialize_sync()
        documents: list[Document] = []
        for path in self._root.glob("*.enc"):
            documents.append(self._decrypt(path.read_bytes(), path.stem))
        return documents

    def _find_thread_owner_sync(self, thread_id: str) -> str | None:
        for document in self._iter_documents():
            if thread_id in document.get("threads", {}):
                identifier = document.get("user", {}).get("identifier")
                return identifier if isinstance(identifier, str) else None
        return None

    def _find_user_by_id_sync(self, user_id: str) -> str | None:
        for document in self._iter_documents():
            user = document.get("user", {})
            if user.get("id") == user_id:
                identifier = user.get("identifier")
                return identifier if isinstance(identifier, str) else None
        return None

    def _all_user_identifiers_sync(self) -> list[str]:
        identifiers: list[str] = []
        for document in self._iter_documents():
            value = document.get("user", {}).get("identifier")
            if isinstance(value, str):
                identifiers.append(value)
        return identifiers
