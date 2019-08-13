#!/usr/bin/env python3

"""Single threaded chat client for chat server application."""

import socket
import selectors
import sys


def usage():
    """Print out proper invocation of program."""
    print('usage: {} ipaddress port'.format(sys.argv[0]))
    sys.exit(1)


class ChatClient():
    """Create a chat client."""
    def __init__(self):
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
        self.ADDR = sys.argv[1]
        self.sel = selectors.DefaultSelector()

        # Set the server's listening port
        try:
            self.PORT = int(sys.argv[2])
        except ValueError:
            print('Error: port must be a number.')
            usage()

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
            self.select_loop()

        # Clean up
        self.sel.unregister(self.server)
        self.sel.unregister(sys.stdin)
        self.sel.close()
        self.server.close()

    def read_server(self, key, mask):
        """Read data from the server."""
        try:
            msg = self.server.recv(self.BUFSIZ).decode('utf8')
        except OSError as err:
            print('Error: {}'.format(err))

        print(msg)

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

        try:
            self.server.send(bytes(msg, 'utf8'))
        except OSError as err:
            print('Error: {}'.format(err))
            sys.exit(1)

        if msg == '{quit}':
            self.exit_flag = True

    def select_loop(self):
        """Select between reading from server socket and standard input."""
        events = self.sel.select()
        for key, mask in events:
            callback = key.data
            callback(key.fileobj, mask)


def main():
    """Main function."""
    if len(sys.argv) != 3:
        usage()

    ChatClient().run()


# __main__? Program entry point
if __name__ == '__main__':
    sys.exit(main())
