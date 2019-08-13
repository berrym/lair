#!/usr/bin/env python3

"""Server for multithreaded (asynchronous) chat application."""

import threading
import selectors
import socket
import sys


def usage():
    """Print out proper invocation of program."""
    print('usage: {} ipaddress port'.format(sys.argv[0]))
    sys.exit(1)


class ChatServer():
    """A simple chatroom server."""
    def __init__(self):
        """Initialize the chat server.

        Important variables set:
            exit_flag: Boolean value, when true the server should exit
            clients: Dictionary of client connections
            addresses: Dictionary of addresses for connections
            MAX_QUEUE: Maximum number of queued connectiions to be established
            HOST: Server's address, should be set at invocation
            PORT: Server's listening port, should be set at invocation
            ADDR: Tuple value of (HOST, PORT)
            BUFSIZ: Buffer size for packets being sent/recieved
            server: Socket used for communications
            sel: Default I/O multiplexing selector
        """
        self.exit_flag = False
        self.clients = {}
        self.addresses = {}
        self.MAX_QUEUE = 5
        self.HOST = sys.argv[1]
        self.sel = selectors.DefaultSelector()

        # Set the listening port number
        try:
            self.PORT = int(sys.argv[2])
        except ValueError:
            print('Error: port must be a number.')
            usage()

        self.ADDR = (self.HOST, self.PORT)
        self.BUFSIZ = 4096

        # Create the server socket
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind(self.ADDR)
        except OSError as err:
            print('Error: {}'.format(err))
            sys.exit(1)

        # Register some select events
        self.sel.register(self.server, selectors.EVENT_READ, self.spawn_client)
        self.sel.register(sys.stdin, selectors.EVENT_READ, self.admin_input)

    def run(self):
        """Run the chat server."""
        try:
            self.server.listen(self.MAX_QUEUE)
        except OSError as err:
            print('Error: {}'.format(err))

        print('Waiting for connections...')

        # Start the main thread
        accept_thread = threading.Thread(target=self.accept_connections)
        accept_thread.start()
        accept_thread.join()

    def accept_connections(self):
        """Accept incoming client connections."""
        while not self.exit_flag:
            self.select_loop()

    def admin_input(self, key, mask):
        """Read from sys.stdin for administrative commands."""
        command = input('')
        if command == 'quit':
            self.close_server()
        elif command == 'who':
            self.who()
        else:
            print('Error: unknown command {}'.format(command))

    def select_loop(self):
        """Select between reading from server socket and standard input."""
        events = self.sel.select()
        for key, mask in events:
            callback = key.data
            callback(key.fileobj, mask)

    def close_server(self):
        """Shutdown the chat server."""
        self.broadcast_to_all(bytes('The lair is closed.', 'utf8'))

        try:
            self.server.shutdown(socket.SHUT_RDWR)
            self.server.close()
        except OSError as err:
            print('Error: {}'.format(err))
        finally:
            self.sel.unregister(self.server)
            self.sel.unregister(sys.stdin)
            self.sel.close()
            self.exit_flag = True

    def who(self):
        """Print a list of all connected clients."""
        print('{:*^60}'.format(' The lair dwellers! '))
        for nick, addr in zip(self.clients.values(),
                              self.addresses.values()):
            print('{} at {}:{}'.format(nick, *addr))

    def spawn_client(self, client, mask):
        """Spawn a new client thread."""
        try:
            client, client_address = self.server.accept()
            print('{}:{} has connected.'.format(*client_address))
            client.send(bytes('You have entered the lair!\n', 'utf8'))
            client.send(bytes('Enter your name!', 'utf8'))
            self.addresses[client] = client_address
        except OSError as err:
            print('Error: {}'.format(err))
            return

        threading.Thread(target=self.handle_client, args=(client,)).start()

    def handle_client(self, client):
        """Handles a single client connection."""
        # Get a unique nickname from the client
        nick = self.get_nick(client)
        self.clients[client] = nick

        msg = 'Welcome to the lair {}! Type {{help}} for commands.'.format(nick)
        try:
            client.send(bytes(msg, 'utf8'))
        except OSError as err:
            print('Error: {}'.format(err))
            return

        # Inform other clients that a new one has connected
        msg = '{} has entered the lair!'.format(nick)
        self.broadcast_to_all(bytes(msg, 'utf8'), client)

        # Start sending/recieving messages with client thread
        self.client_thread_loop(client, nick)

    def get_nick(self, client):
        """Get a unique nickname from the client."""
        while True:
            nick = client.recv(self.BUFSIZ).decode('utf8')
            if nick in self.clients.values():
                msg = '{} is already taken, choose another name.'.format(nick)
                try:
                    client.send(bytes(msg, 'utf8'))
                except OSError as err:
                    print('Error: {}'.format(err))
            else:
                return nick

    def broadcast_to_all(self, msg, omit_client=None, prefix=''):
        """Broadcast a message to clients."""
        for sock in self.clients:
            if omit_client and sock == omit_client:
                continue

            try:
                sock.send(bytes(prefix, 'utf8') + msg)
            except OSError as err:
                print('Error: {}'.format(err))

    def broadcast_to_client(self, msg, client, prefix=''):
        """Broadcast a message to a single client."""
        try:
            client.send(bytes(prefix, 'utf8') + msg)
        except OSError as err:
            print('Error: {}'.format(err))

    def client_thread_loop(self, client, nick):
        """Send/Receive loop for client thread."""
        while True:
            try:
                msg = client.recv(self.BUFSIZ).decode('utf8')
            except OSError as err:
                print('Error: {}'.format(err))
                break

            if msg == '':
                break
            elif msg == '{quit}':
                self.remove_client(client, nick)
                break
            elif msg == '{who}':
                self.tell_who(client)
            else:
                self.broadcast_to_all(bytes(msg, 'utf8'), client, nick + ': ')

    def remove_client(self, client, nick):
        """Remove a client connection."""
        print('{}:{} has disconnected.'.format(*self.addresses[client]))
        del self.addresses[client]
        del self.clients[client]
        msg = '{} has left the lair.'.format(nick)
        self.broadcast_to_all(bytes(msg, 'utf8'), client)
        client.close()

    def tell_who(self, client):
        """Send a list of connected users to a client."""
        for nick, addr in zip(self.clients.values(),
                              self.addresses.values()):
            msg = '{} at {}\n'.format(nick, addr[0])
            self.broadcast_to_client(bytes(msg, 'utf8'), client)


def main():
    """Main Function."""
    if len(sys.argv) != 3:
        usage()

    ChatServer().run()


# __main__? Program entry point
if __name__ == '__main__':
    sys.exit(main())
