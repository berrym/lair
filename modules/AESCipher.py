"""AESCipher.py

AES Cipher class for encrypting and decrypting string data.
"""


import os
import logging
import base64
import hashlib
from Cryptodome.Random import get_random_bytes
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad


logfilename = os.path.join(os.path.expanduser('~'), '.lair.log')

# Enable logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)-15s [%(threadName)-12s]'
    + '[%(levelname)-8s]  %(message)s',
    handlers=[logging.FileHandler(logfilename), logging.StreamHandler()])


def catch_common_errors(func):
    """Catch common exceptions."""
    def wrapper(*args, **kwargs):
        """Wrap around func and catch common exceptions."""
        try:
            result = func(*args, **kwargs)
            return result
        except (ValueError, AttributeError) as e:
            logging.info(f'AESCipher error: {e}')
            return None

    return wrapper


class AESCipher:
    """Implement AES Cipher Block Chaining encryption and decryption."""

    def __init__(self, key):
        """Make a fixed sha256 bit length key."""
        self.key = hashlib.sha256(key.encode('utf-8')).digest()

    @catch_common_errors
    def encrypt(self, raw_data):
        """Encrypt raw data."""
        raw_data = pad(raw_data.encode('utf-8'), AES.block_size)
        iv = get_random_bytes(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw_data))

    @catch_common_errors
    def decrypt(self, enc_data):
        """Decrypt encoded data."""
        enc_data = base64.b64decode(enc_data)
        iv = enc_data[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return unpad(cipher.decrypt(enc_data[AES.block_size:]), AES.block_size)


# Create an AESCipher object
cipher = AESCipher('BewareTheBlackGuardian')
