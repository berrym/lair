"""ChatClient.py

The Lair: Client class for The Lair chat application.
"""

import selectors
import socket
import sys

from modules.crypto.AESCipher import aes_cipher


class ChatClient():
    """Create a chat client."""

    def __init__(self, host: str, port: int) -> None:
        """Create a chat client connection."""
        self.exit_flag = False
        self.BUFSIZ = 4096
        self.sel = selectors.DefaultSelector()
        ADDR = (host, port)

        # Connect to the server
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.connect(ADDR)
        except OSError as e:
            print(f'Error: {e}')
            sys.exit(1)

        # Register some select events
        self.sel.register(self.server, selectors.EVENT_READ, self.read_server)
        self.sel.register(sys.stdin, selectors.EVENT_READ, self.user_input)

    def run(self) -> None:
        """Run a client session."""
        while not self.exit_flag:
            self.event_loop()

        # Clean up
        self.sel.unregister(self.server)
        self.sel.unregister(sys.stdin)
        self.sel.close()
        self.server.shutdown(socket.SHUT_RDWR)
        self.server.close()

    def event_loop(self) -> None:
        """Select between reading from server socket and standard input."""
        events = self.sel.select()
        for key, mask in events:
            callback = key.data
            callback(key.fileobj, mask)

    def read_server(self, key: selectors.SelectorKey, mask) -> None:
        """Read messages from the chat server."""
        try:
            data = self.server.recv(self.BUFSIZ)
        except OSError as e:
            print(f'Error: {e}')
            return

        # Print the message
        decrypted = aes_cipher.decrypt(data)
        if decrypted is None:
            return
        msg = decrypted.decode('utf-8', 'ignore')
        print(msg)

        # Check if the server closed
        if msg == 'The lair is closed.':
            self.exit_flag = True

    def user_input(self, key: selectors.SelectorKey, mask) -> None:
        """Read input from the user."""
        msg = input('')
        if msg == '{help}':
            print('{:*^40}'.format(' Available Commands '))
            print('{help}:\tThis help message')
            print('{who}:\tA list of connected users')
            print('{quit}:\tExit this client session')
            return

        # Encrypt the message
        b_msg = aes_cipher.encrypt(msg)
        if b_msg is None:
            return

        # Send the message
        try:
            self.server.sendall(b_msg)
        except OSError as e:
            print(f'Error: {e}')
            sys.exit(1)

        # Decrypt the message
        d_msg = aes_cipher.decrypt(b_msg)

        # Decode the message and check if the user wants to quit
        if d_msg.decode('utf-8', 'ignore') == '{quit}':
            self.exit_flag = True
            return
