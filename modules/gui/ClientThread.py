"""ClientThread.py

Client thread class for qt gui client.
"""

from PyQt5 import QtCore

from modules.crypto.AESCipher import aes_cipher
from modules.gui.GuiCommon import *


class Communicate(QtCore.QObject):
    """Communication breakdown!  Signal for communicating with main thread."""

    close_app = QtCore.pyqtSignal()


class ClientThread(QtCore.QThread):
    """Create a client thread for networking communications."""

    def __init__(self, main_win: QtWidgets.QMainWindow):
        """Initialize the thread."""
        QtCore.QThread.__init__(self, main_win)
        self.parent = main_win
        self.communicator = Communicate()

    def __del__(self):
        """Thread cleanup."""
        self.wait()

    def quit(self):
        """Exit the program."""
        self.parent.quit()

    def recveive(self):
        """Read data from server."""
        buf_size = 4096

        try:
            data = self.parent.sock.recv(buf_size)
        except OSError as e:
            critical_error(self.parent, f'recv: {e}')
            self.quit()

        # Decrypt and decode the data
        decrypted = aes_cipher.decrypt(data)
        if decrypted is None:
            critical_error(self.parent, 'unable to decrypt message')
            self.quit()

        msg = decrypted.decode('utf-8', 'ignore')

        # Add received text to chat field
        self.parent.chat_view.append(format_text(color='blue', text=msg))

        # The server closed, do NOT set ANNOUNCE_EXIT
        if msg == 'The lair is closed.':
            self.quit()

    def run(self):
        """Run the client thread."""
        try:
            self.parent.sock.connect(self.parent.conn[0])
        except OSError as e:
            critical_error(self.parent, e)
            return self.quit()

        # Receive loop
        while True:
            self.recveive()
