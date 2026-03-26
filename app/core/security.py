import re

from cryptography.fernet import Fernet

from app.config import settings


class SecretManager:
    """Encrypt/decrypt sensitive data like social account tokens."""

    def __init__(self, key: str | None = None):
        self.cipher = Fernet(key or settings.encryption_key)

    def encrypt(self, plaintext: str) -> str:
        return self.cipher.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        return self.cipher.decrypt(ciphertext.encode()).decode()


class PromptSecurity:
    """Detect and prevent prompt injection attacks."""

    INJECTION_PATTERNS = [
        r"ignore\s+(all\s+|previous\s+|above\s+)?instructions",
        r"you\s+are\s+now",
        r"new\s+instructions\s*:",
        r"system\s+prompt\s*:",
        r"reveal\s+your",
        r"disregard\s+(all\s+)?previous",
        r"override\s+system",
    ]

    @classmethod
    def check_injection(cls, text: str) -> bool:
        """Returns True if potential injection is detected."""
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    @classmethod
    def sanitize_for_prompt(cls, text: str) -> str:
        """Sanitize user input before inserting into prompts."""
        # Escape template delimiters
        text = text.replace("{", "{{").replace("}", "}}")
        # Remove control characters
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
        return text


secret_manager = SecretManager()


def encrypt_token(plaintext: str) -> str:
    """Shortcut to encrypt a social token."""
    return secret_manager.encrypt(plaintext)


def decrypt_token(ciphertext: str) -> str:
    """Shortcut to decrypt a social token."""
    return secret_manager.decrypt(ciphertext)
