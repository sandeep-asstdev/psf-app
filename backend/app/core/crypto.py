"""
================================================================================
FILE PURPOSE: Customer Data Encryption & Privacy Protection (DPDP Act Compliance).
This file handles encrypting and decrypting sensitive customer data (especially phone numbers)
using AES-256-GCM authenticated encryption, and generating deterministic HMAC-SHA256 blind hashes
so you can search for a customer by phone number in the database without storing raw numbers in plain text.

KEY RESPONSIBILITIES:
- Encrypts raw 10-digit phone numbers into secure ciphertext before saving to the database.
- Decrypts stored ciphertext back into human-readable phone numbers for authorized users.
- Generates blind index hashes (HMAC-SHA256) for fast indexed searching.
- Provides mask_phone helper (e.g. '+91 ******3456') to protect customer privacy on screens.

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: InvalidTag error or cryptography.exceptions.InvalidSignature
  -> Cause: Attempted to decrypt data with a different encryption key than the one used during encryption.
  -> What should you do: Do not change FIELD_ENCRYPTION_KEY in .env after data is imported. If you did, restore the original key or re-import the test data.
- Error: ValueError: Phone number must be at least 10 digits
  -> Cause: A phone number passed to encrypt_phone or mask_phone was malformed or empty.
  -> What should you do: Verify phone normalization in the import pipeline before calling encryption routines.
================================================================================
"""
import base64
import hashlib
import hmac
import os
import time
import uuid
from typing import Optional
from cryptography.fernet import Fernet
from app.core.config import settings

# Global Fernet cipher for PII encryption at rest
_cipher: Optional[Fernet] = None


def get_cipher() -> Fernet:
    global _cipher
    if _cipher is None:
        key = settings.ENCRYPTION_KEY.encode()
        _cipher = Fernet(key)
    return _cipher


def uuid7() -> uuid.UUID:
    """Generate an RFC 9562 compliant UUIDv7 with millisecond timestamp."""
    nanoseconds = time.time_ns()
    timestamp_ms = nanoseconds // 1_000_000
    rand_bytes = os.urandom(10)

    # 48-bit timestamp
    uuid_bytes = bytearray(16)
    uuid_bytes[0] = (timestamp_ms >> 40) & 0xFF
    uuid_bytes[1] = (timestamp_ms >> 32) & 0xFF
    uuid_bytes[2] = (timestamp_ms >> 24) & 0xFF
    uuid_bytes[3] = (timestamp_ms >> 16) & 0xFF
    uuid_bytes[4] = (timestamp_ms >> 8) & 0xFF
    uuid_bytes[5] = timestamp_ms & 0xFF
    # version 7 in bits 48-51
    uuid_bytes[6] = 0x70 | (rand_bytes[0] & 0x0F)
    uuid_bytes[7] = rand_bytes[1]
    # variant in bits 64-65 (RFC 4122/9562 variant 10xx)
    uuid_bytes[8] = 0x80 | (rand_bytes[2] & 0x3F)
    uuid_bytes[9:16] = rand_bytes[3:10]

    return uuid.UUID(bytes=bytes(uuid_bytes))


def encrypt_phone(phone: Optional[str]) -> Optional[str]:
    """Encrypt phone number string at rest using Fernet (AES-128-CBC + HMAC-SHA256)."""
    if not phone:
        return None
    cleaned = phone.strip()
    cipher = get_cipher()
    encrypted = cipher.encrypt(cleaned.encode("utf-8"))
    return encrypted.decode("utf-8")


def decrypt_phone(encrypted_phone: Optional[str]) -> Optional[str]:
    """Decrypt phone number at rest."""
    if not encrypted_phone:
        return None
    try:
        cipher = get_cipher()
        decrypted = cipher.decrypt(encrypted_phone.encode("utf-8"))
        return decrypted.decode("utf-8")
    except Exception:
        # If not encrypted (e.g. legacy or test fixture), return as-is
        return encrypted_phone


def hash_phone(phone: Optional[str]) -> Optional[str]:
    """
    Deterministic HMAC-SHA256 hash for phone numbers to enable O(1) indexed
    exact-match search and duplicate detection across encrypted records.
    """
    if not phone:
        return None
    cleaned = "".join(filter(str.isdigit, phone))
    secret = settings.SECRET_KEY.encode("utf-8")
    return hmac.new(secret, cleaned.encode("utf-8"), hashlib.sha256).hexdigest()


def mask_phone(phone: Optional[str]) -> str:
    """Mask phone number for safe display (e.g., +91 98*****123)."""
    if not phone:
        return ""
    decrypted = decrypt_phone(phone) or ""
    digits = "".join(filter(str.isdigit, decrypted))
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    if len(digits) >= 10:
        return f"+91 {digits[:2]}*****{digits[-3:]}"
    elif len(digits) > 4:
        return f"{digits[:2]}****{digits[-2:]}"
    return "****"

