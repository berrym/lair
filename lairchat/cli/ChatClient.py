"""ChatClient.py

The Lair: Client class for The Lair chat application.
"""

import selectors
import sys
from socket import *

from lairchat.crypto.AESCipher import aes_cipher


class ChatClient:
    """Create a chat client."""

    def __init__(self, host: str, port: int) -> None:
        """Create a chat client connection."""
        self.exit_flag = False
        self.buf_size = 4096
        self.sel = selectors.DefaultSelector()

        # Connect to the server
        try:
            self.server = socket(AF_INET, SOCK_STREAM)
            self.server.connect((host, port))
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
        self.server.shutdown(SHUT_RDWR)
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
            data = self.server.recv(self.buf_size)
        except OSError as e:
            print(f'Error: {e}')
            return

        # Print the message
        decrypted_data = aes_cipher.decrypt(data)
        if decrypted_data is None:
            return
        message = decrypted_data.decode('utf-8', 'ignore')
        print(message)

        # Check if the server closed
        if message == 'The lair is closed.':
            self.exit_flag = True

    def user_input(self, key: selectors.SelectorKey, mask) -> None:
        """Read input from the user."""
        message = input('')
        if message == '{help}':
            print('{:*^40}'.format(' Available Commands '))
            print('{help}:\tThis help message')
            print('{who}:\tA list of connected users')
            print('{quit}:\tExit this client session')
            return

        # Encrypt the message
        encrypted_message = aes_cipher.encrypt(message)
        if encrypted_message is None:
            return

        # Send the message
        try:
            self.server.sendall(encrypted_message)
        except OSError as e:
            print(f'Error: {e}')
            sys.exit(1)

        # Decrypt the message
        decrypted_message = aes_cipher.decrypt(encrypted_message)

        # Decode the message and check if the user wants to quit
        if decrypted_message.decode('utf-8', 'ignore') == '{quit}':
            self.exit_flag = True
            return
