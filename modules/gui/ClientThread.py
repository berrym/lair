"""ClientThread.py

Client thread class for qt gui client.
"""

from PyQt5 import QtCore

from modules.crypto.AESCipher import aes_cipher
from modules.gui.utility import *


class ClientThread(QtCore.QThread):
    """Create a client thread for networking communications."""

    def __init__(self, parent):
        """Initialize the thread."""
        QtCore.QThread.__init__(self, parent)
        self.parent = parent

    def __del__(self):
        """Thread cleanup."""
        self.wait()

    def quit(self):
        """Exit the program."""
        exit(self.parent.quit())

    def recveive(self):
        """Read data from server."""
        BUFSIZ = 4096
        global ANNOUNCE_EXIT

        try:
            data = self.parent.sock.recv(BUFSIZ)
        except OSError as e:
            critical_error(self.parent, f'recv: {e}')
            exit(self.quit())

        # Make sure the other thread hasn't called quit yet
        # If it has, stop executing this frame
        if ANNOUNCE_EXIT:
            exit(0)

        # Decrypt and decode the data
        decrypted = aes_cipher.decrypt(data)
        if decrypted is None:
            critical_error(self.parent, 'unable to decrypt message')
            exit(self.quit())

        msg = decrypted.decode('utf-8', 'ignore')

        # Add received text to chat field
        self.parent.chat_view.append(format_text(color='blue', text=msg))

        # The server closed, do NOT set ANNOUNCE_EXIT
        if msg == 'The lair is closed.':
            exit(self.quit())

    def run(self):
        """Run the client thread."""
        try:
            self.parent.sock.connect(self.parent.conn[0])
        except OSError as e:
            critical_error(self.parent, e)
            return self.quit()

        # Receive loop
        while not ANNOUNCE_EXIT:
            self.recveive()
