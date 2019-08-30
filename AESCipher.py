"""AES Cipher class for encryption and decryption."""

import base64
import hashlib
from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad


class AESCipher:
    """Implement AES Cipher encryption and decryption."""
    def __init__(self, key):
        """Make a fixed sha256 bit length key."""
        self.key = hashlib.sha256(key.encode('utf-8')).digest()

    def encrypt(self, raw_data):
        """Encrypt raw data."""
        raw_data = pad(raw_data.encode('utf-8'), AES.block_size)
        iv = get_random_bytes(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw_data))

    def decrypt(self, enc_data):
        """Decrypt encoded data."""
        enc_data = base64.b64decode(enc_data)
        iv = enc_data[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return unpad(cipher.decrypt(enc_data[AES.block_size:]), AES.block_size)


# Create an AESCipher object
cipher = AESCipher('BewareTheBlackGuardian')
