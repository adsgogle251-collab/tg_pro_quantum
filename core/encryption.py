"""TG PRO QUANTUM - Encryption Manager"""
import base64
from cryptography.fernet import Fernet
from .utils import log, log_error

class EncryptionManager:
    def __init__(self):
        import os
        key = os.getenv("ENCRYPTION_KEY", "DefaultKey32CharactersLong12345!").encode()[:32].ljust(32, b'=')
        self.cipher = Fernet(base64.urlsafe_b64encode(key))

    def encrypt(self, data: bytes) -> str:
        try:
            return self.cipher.encrypt(data).decode('latin-1')
        except Exception as e:
            log_error(f"Encryption failed: {e}")
            return ""

    def decrypt(self, encrypted: str):
        try:
            return self.cipher.decrypt(encrypted.encode('latin-1'))
        except Exception as e:
            log_error(f"Decryption failed: {e}")
            return None

encryption_manager = EncryptionManager()
__all__ = ["EncryptionManager", "encryption_manager"]