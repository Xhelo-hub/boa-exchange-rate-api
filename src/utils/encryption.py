"""
Encryption utilities for securing sensitive data
Uses Fernet symmetric encryption from cryptography library
"""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class EncryptionManager:
    """
    Manages encryption/decryption of sensitive data
    
    Uses Fernet (symmetric encryption) with a key derived from a secret
    """
    
    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize encryption manager
        
        Args:
            secret_key: Secret key for encryption. If None, uses environment variable.
        """
        if secret_key is None:
            secret_key = os.getenv('SECRET_KEY')
        
        if not secret_key:
            raise ValueError(
                "SECRET_KEY must be provided or set in environment. "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        
        # Derive a Fernet key from the secret key using PBKDF2
        # This allows using a human-readable secret key
        self._fernet = self._create_fernet(secret_key)
    
    def _create_fernet(self, secret_key: str) -> Fernet:
        """
        Create Fernet instance from secret key
        
        Args:
            secret_key: Secret key string
            
        Returns:
            Fernet instance
        """
        # Use PBKDF2 to derive a 32-byte key from the secret
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'boa_exchange_rate_salt',  # Static salt (for production, use dynamic salt per installation)
            iterations=100000,
            backend=default_backend()
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
        return Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Encrypted string (base64 encoded)
        """
        if not plaintext:
            return ""
        
        try:
            encrypted_bytes = self._fernet.encrypt(plaintext.encode())
            return encrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a string
        
        Args:
            ciphertext: Encrypted string (base64 encoded)
            
        Returns:
            Decrypted plaintext string
        """
        if not ciphertext:
            return ""
        
        try:
            decrypted_bytes = self._fernet.decrypt(ciphertext.encode())
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise
    
    def encrypt_dict(self, data: dict, keys_to_encrypt: list) -> dict:
        """
        Encrypt specific keys in a dictionary
        
        Args:
            data: Dictionary with data
            keys_to_encrypt: List of keys to encrypt
            
        Returns:
            Dictionary with specified keys encrypted
        """
        result = data.copy()
        for key in keys_to_encrypt:
            if key in result and result[key]:
                result[key] = self.encrypt(str(result[key]))
        return result
    
    def decrypt_dict(self, data: dict, keys_to_decrypt: list) -> dict:
        """
        Decrypt specific keys in a dictionary
        
        Args:
            data: Dictionary with encrypted data
            keys_to_decrypt: List of keys to decrypt
            
        Returns:
            Dictionary with specified keys decrypted
        """
        result = data.copy()
        for key in keys_to_decrypt:
            if key in result and result[key]:
                result[key] = self.decrypt(result[key])
        return result


# Global encryption manager instance
_encryption_manager: Optional[EncryptionManager] = None


def get_encryption_manager() -> EncryptionManager:
    """
    Get global encryption manager instance (singleton)
    
    Returns:
        EncryptionManager instance
    """
    global _encryption_manager
    
    if _encryption_manager is None:
        # Try to get key from settings first, then environment
        secret_key = None
        try:
            from config.settings import settings
            secret_key = settings.secret_key
            if secret_key:
                # Ensure it's in environment for backward compatibility
                import os
                os.environ['SECRET_KEY'] = str(secret_key)
        except Exception as e:
            logger.debug(f"Could not load secret_key from settings: {e}")
            # Fall back to environment variable
            import os
            secret_key = os.getenv('SECRET_KEY')
        
        _encryption_manager = EncryptionManager(secret_key=secret_key)
    
    return _encryption_manager


def encrypt_token(token: str) -> str:
    """
    Encrypt a token (convenience function)
    
    Args:
        token: Token to encrypt
        
    Returns:
        Encrypted token
    """
    return get_encryption_manager().encrypt(token)


def decrypt_token(encrypted_token: str) -> str:
    """
    Decrypt a token (convenience function)
    
    Args:
        encrypted_token: Encrypted token
        
    Returns:
        Decrypted token
    """
    return get_encryption_manager().decrypt(encrypted_token)


def generate_secret_key() -> str:
    """
    Generate a new secret key for encryption
    
    Returns:
        Base64-encoded secret key
    """
    return Fernet.generate_key().decode()


if __name__ == "__main__":
    # Test encryption
    print("Testing Encryption...")
    
    # Generate a test key
    test_key = generate_secret_key()
    print(f"Generated key: {test_key}")
    
    # Test encryption/decryption
    manager = EncryptionManager(test_key)
    
    test_data = "eyJhbGciOiJkaXIiLCJlbmMiOiJBMTI4Q0JDLUhTMjU2In0.test_access_token"
    print(f"\nOriginal: {test_data}")
    
    encrypted = manager.encrypt(test_data)
    print(f"Encrypted: {encrypted}")
    
    decrypted = manager.decrypt(encrypted)
    print(f"Decrypted: {decrypted}")
    
    print(f"\nMatch: {test_data == decrypted}")
