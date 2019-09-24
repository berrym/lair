"""AESCipher.py

AES Cipher class for encrypting and decrypting string data.
"""

import base64
import hashlib
import logging
import os
from typing import *

from Cryptodome.Cipher import AES
from Cryptodome.Random import get_random_bytes
from Cryptodome.Util.Padding import pad, unpad

logfilename = os.path.join(os.path.expanduser('~'), '.lair.log')

# Enable logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)-15s [%(threadName)-12s]'
           + '[%(levelname)-8s]  %(message)s',
    handlers=[logging.FileHandler(logfilename), logging.StreamHandler()])


def catch_common_exceptions(func):
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

    def __init__(self, key: str) -> None:
        """Make a fixed sha256 bit length key."""
        self.key = hashlib.sha256(key.encode('utf-8')).digest()

    @catch_common_exceptions
    def encrypt(self, rawdata: str) -> bytes:
        """Encrypt raw data."""
        raw_data = pad(rawdata.encode('utf-8'), AES.block_size)
        iv = get_random_bytes(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw_data))

    @catch_common_exceptions
    def decrypt(self, encdata: bytes) -> bytes:
        """Decrypt encoded data."""
        enc_data = base64.b64decode(encdata)
        iv = enc_data[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return unpad(cipher.decrypt(enc_data[AES.block_size:]), AES.block_size)


# Create an AESCipher object
aes_cipher = AESCipher('BewareTheBlackGuardian')
