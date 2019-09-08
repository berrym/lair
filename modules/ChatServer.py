"""The Lair: Server for multithreaded (asynchronous) chat application."""

import logging
import threading
import selectors
import socket
import sys
import time
from modules.AESCipher import cipher


# Enable logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)-15s [%(threadName)-12s]'
    + '[%(levelname)-8s]  %(message)s',
    handlers=[logging.FileHandler('lair.log'), logging.StreamHandler()])


class ChatServer():
    """A simple chatroom server."""
    def __init__(self, host, port):
        """Initialize the chat server.

        Important variables set:
            exit_flag: Boolean value, when true the server should exit
            clients: Dictionary of client connections
            addresses: Dictionary of addresses for connections
            MAX_QUEUE: Maximum number of queued connectiions
            ADDR: Tuple value of (host, port)
            BUFSIZ: Buffer size for packets being sent/recieved
            server: Socket used for communications
            sel: Default I/O multiplexing selector
        """
        self.exit_flag = False
        self.clients = {}
        self.addresses = {}
        self.MAX_QUEUE = 5
        self.ADDR = (host, port)
        self.BUFSIZ = 4096
        self.sel = selectors.DefaultSelector()

        # Create the server socket
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind(self.ADDR)
            self.server.listen(self.MAX_QUEUE)
        except OSError as err:
            logging.critical('Error: {}'.format(err))
            sys.exit(1)

        # Register some select events
        self.sel.register(self.server, selectors.EVENT_READ, self.spawn_client)
        self.sel.register(sys.stdin, selectors.EVENT_READ, self.admin_input)

    def run(self):
        """Run the chat server."""
        # Start the main thread
        logging.info('Starting main thread.  Waiting for connections.')
        accept_thread = threading.Thread(target=self.accept_connections)
        accept_thread.start()
        accept_thread.join()
        logging.info('Main thread exited.')

    def accept_connections(self):
        """Accept incoming client connections."""
        while not self.exit_flag:
            self.event_loop()

    def event_loop(self):
        """Select between reading from server socket and standard input."""
        events = self.sel.select()
        for key, mask in events:
            callback = key.data
            callback(key.fileobj, mask)

    def admin_input(self, key, mask):
        """Read from sys.stdin for administrative commands."""
        command = input('')
        if command == 'quit':
            self.close_server()
        elif command == 'who':
            self.who()
        else:
            print('Error: unknown command {}'.format(command))

    def close_server(self):
        """Shutdown the chat server."""
        self.broadcast_to_all('The lair is closed.')

        try:
            self.server.close()
        except OSError as err:
            logging.warn('Error: {}'.format(err))
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
        except OSError as err:
            print('Error: {}'.format(err))

        logging.info('{}:{} has connected.'.format(*client_address))

        # Say hello
        msg = 'You have entered the lair!\nEnter your name!'
        self.broadcast_to_client(msg, client)
        self.addresses[client] = client_address

        # Start the new thread
        logging.info('Starting a client thread {}'.format(client))
        threading.Thread(target=self.handle_client, args=(client,)).start()
        logging.info('Client thread started.')

    def handle_client(self, client):
        """Handles a single client connection."""
        # Get a unique nickname from the client
        nick = self.get_nick(client)
        if nick:
            self.clients[client] = nick
        else:
            return

        # Welcome the new client to the lair
        msg = 'Welcome to the Lair {}! Type {{help}} for commands.'.format(
            nick)
        self.broadcast_to_client(msg, client)

        # Inform other clients that a new one has connected
        msg = '{} has entered the lair!'.format(nick)
        self.broadcast_to_all(msg, client)

        # Start sending/recieving messages with client thread
        self.client_thread_loop(client, nick)

    def get_nick(self, client):
        """Get a unique nickname from the client."""
        while True:
            try:
                nick = client.recv(self.BUFSIZ)
            except OSError as err:
                logging.warning('Error: {}'.format(err))
                return False

            if not nick:
                return False

            nick = cipher.decrypt(nick)
            nick = nick.decode('utf-8', 'ignore')
            if nick in self.clients.values():
                msg = '{} is already taken, choose another name.'.format(
                    nick)
                self.broadcast_to_client(msg, client)
            else:
                logging.info('{} logged in as {}'.format(client, nick))
                return nick

    def broadcast_to_all(self, msg, omit_client=None, prefix=''):
        """Broadcast a message to clients."""
        # Potential clients to remove
        dead_clients = []

        # Create the encrypted message
        msg = str(prefix) + str(msg)
        msg = cipher.encrypt(msg)

        for sock in self.clients:
            if omit_client and sock == omit_client:
                continue

            try:
                sock.send(msg)
            except OSError as err:
                logging.warning('Error: {}'.format(err))
                dead_clients.append(sock)

        # Remove unresponsive client connections
        for sock in dead_clients:
            self.remove_client(sock, 'Dead client {}'.format(sock))

    def broadcast_to_client(self, msg, client, prefix=''):
        """Broadcast a message to a single client."""
        # Create the encrypted message
        msg = str(prefix) + str(msg)
        msg = cipher.encrypt(msg)

        try:
            client.send(msg)
        except OSError as err:
            logging.warning('Error: {}'.format(err))
            self.remove_client(client, 'Unknown visitor')

    def client_thread_loop(self, client, nick):
        """Send/Receive loop for client thread."""
        while not self.exit_flag:
            try:
                msg = client.recv(self.BUFSIZ)
            except OSError as err:
                logging.warning('Error: {}'.format(err))
                break

            if not msg:
                logging.warn('Error: unable to recvieve from {}'.format(
                    nick))
                self.remove_client(client, nick)
                break

            # Decrypt the message
            msg = cipher.decrypt(msg)
            msg = msg.decode('utf-8', 'ignore')

            if msg == '{quit}':
                self.remove_client(client, nick)
                break
            elif msg == '{who}':
                self.tell_who(client)
            else:
                self.broadcast_to_all(msg, client, nick + ': ')

    def remove_client(self, client, nick):
        """Remove a client connection."""
        logging.info('{}:{} has disconnected.'.format(*self.addresses[client]))

        # Remove client from dictionaries
        del self.addresses[client]
        del self.clients[client]

        msg = '{} has left the lair.'.format(nick)
        self.broadcast_to_all(msg, client)

        # Make sure client is disconnected
        try:
            client.close()
        except OSError as err:
            logging.warn('remove_client: {}'.format(err))

    def tell_who(self, client):
        """Send a list of connected users to a client."""
        for nick, addr in zip(self.clients.values(),
                              self.addresses.values()):
            msg = '{} at {}\n'.format(nick, addr[0])
            self.broadcast_to_client(msg, client)
            time.sleep(0.1)
