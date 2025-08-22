
import os, hashlib
from cryptography.fernet import Fernet, InvalidToken

# Load Fernet key from env or (preferred) Streamlit secrets
FERNET_KEY = os.environ.get("FERNET_KEY") or os.environ.get("STREAMLIT_FERNET_KEY")
if not FERNET_KEY:
    # For safety, do NOT auto-generate silently in production. Raise to avoid storing plaintext.
    raise RuntimeError("Missing FERNET_KEY in environment (or STREAMLIT_FERNET_KEY).")

fernet = Fernet(FERNET_KEY)

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def encrypt_bytes(b: bytes) -> bytes:
    return fernet.encrypt(b)

def decrypt_bytes(b: bytes) -> bytes:
    return fernet.decrypt(b)

def is_encrypted_sample(b: bytes) -> bool:
    # Fernet tokens always start with 'gAAAAA' (base64). This is heuristic.
    try:
        return b.startswith(b"gAAAA")
    except Exception:
        return False
