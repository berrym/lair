"""ChatClient.py

The Lair: Client class for The Lair chat application.
"""


import socket
import selectors
import sys
from modules.AESCipher import cipher


class ChatClient():
    """Create a chat client."""
    def __init__(self, host, port):
        """Create a chat client connection.

        Variables of importance:
            self.exit_flag: Boolean value, if true the client should close
            self.BUFSIZ: Buffer size for packet sending/recieving
            self.server: Socket connection to the server
            self.sel: Default I/O multiplexing selector
            ADDR: Tuple value of server's (host, port)

        Class Methods:
            run: Run a client session
            event_loop: Select between registered events
            read_server: Read messages from the chat server
            user_input: Read input from the user
        """
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

    def event_loop(self):
        """Select between reading from server socket and standard input."""
        events = self.sel.select()
        for key, mask in events:
            callback = key.data
            callback(key.fileobj, mask)

    def read_server(self, key, mask):
        """Read messages from the chat server."""
        try:
            msg = self.server.recv(self.BUFSIZ)
        except OSError as e:
            print(f'Error: {e}')
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
            self.server.sendall(msg)
        except OSError as e:
            print(f'Error: {e}')
            sys.exit(1)

        # Decrypt the message
        msg = cipher.decrypt(msg)

        # Decode the message and check if the user wants to quit
        if msg.decode('utf-8', 'ignore') == '{quit}':
            self.exit_flag = True
            return
