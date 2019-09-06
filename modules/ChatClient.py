"""Single threaded cli chat client for The Lair chat server application."""

import socket
import selectors
import sys
from modules.AESCipher import cipher


class ChatClient():
    """Create a chat client."""
    def __init__(self, addr, port):
        """Create a chat client connection.

        Variables of importance:
            exit_flag: Boolean value signaling wether the client should close
            ADDR: Server's address
            PORT: Server's listening port
            BUFSIZ: Buffer size for packet sending/recieving
            server: Socket connection to the server
            sel: Default I/O multiplexing selector
        """
        self.exit_flag = False
        self.ADDR = addr
        self.PORT = port
        self.sel = selectors.DefaultSelector()
        self.BUFSIZ = 4096

        # Connect to the server
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.connect((self.ADDR, self.PORT))
        except OSError as err:
            print('Error: {}'.format(err))
            sys.exit(1)

        # Register some select events
        self.sel.register(self.server, selectors.EVENT_READ, self.read_server)
        self.sel.register(sys.stdin, selectors.EVENT_READ, self.user_input)

    def run(self):
        """Run a client session."""
        while not self.exit_flag:
            self.event_loop()

        # Clean up
        self.sel.unregister(self.server)
        self.sel.unregister(sys.stdin)
        self.sel.close()
        self.server.shutdown(socket.SHUT_RDWR)
        self.server.close()

    def read_server(self, key, mask):
        """Read data from the server."""
        try:
            msg = self.server.recv(self.BUFSIZ)
        except OSError as err:
            print('Error: {}'.format(err))
            return

        # Print the message
        msg = cipher.decrypt(msg)
        msg = msg.decode('utf-8', 'ignore')
        print(msg)

        # Check if the server closed
        if msg == 'The lair is closed.':
            self.exit_flag = True

    def user_input(self, key, mask):
        """Read input from the user."""
        msg = input('')
        if msg == '{help}':
            print('{:*^40}'.format(' Available Commands '))
            print('{help}:\tThis help message')
            print('{who}:\tA list of connected users')
            print('{quit}:\tExit this client session')
            return

        # Encrypt the message
        msg = cipher.encrypt(msg)

        # Send the message
        try:
            self.server.send(msg)
        except OSError as err:
            print('Error: {}'.format(err))
            sys.exit(1)

        # Decrypt the message
        msg = cipher.decrypt(msg)

        # Decode the message and check if the user wants to quit
        if msg.decode('utf-8', 'ignore') == '{quit}':
            self.exit_flag = True
            return

    def event_loop(self):
        """Select between reading from server socket and standard input."""
        events = self.sel.select()
        for key, mask in events:
            callback = key.data
            callback(key.fileobj, mask)
