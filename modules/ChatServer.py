"""ChatServer.py

The Lair: Server class for multithreaded (asynchronous) chat application.
"""


import os
import sys
import time
import logging
import threading
import selectors
import socket
from modules.AESCipher import cipher


logfilename = os.path.join(os.path.expanduser('~'), '.lair.log')

# Enable logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)-15s [%(threadName)-12s]'
    + '[%(levelname)-8s]  %(message)s',
    handlers=[logging.FileHandler(logfilename), logging.StreamHandler()])


class ChatServer():
    """A simple chatroom server."""
    def __init__(self, host, port):
        """Initialize the chat server.

        Important variables set:
            self.exit_flag: Boolean value, when true the server should exit
            self.nicks: Dictionary of socket->nick
            self.addrs: Dictionary of socket->address
            self.threads: Dictionary of client threads, socket->thread
            self.BUFSIZ: Buffer size for packets being sent/recieved
            self.server: Socket used for communications
            self.sel: Default I/O multiplexing selector
            ADDR: Tuple value of (host, port)
            MAX_QUEUE: Maximum number of queued connectiions

        Class Methods:
            run: Run the chat server
            event_loop: Select between registered events
            admin_input: Accept commands from administrator
            close_server: Shutdown the chat server
            who: Print a list of connected clients
            spawn_client: Spawn a new client thread
            handle_client: Handle client connection
            get_nick: Get a unique nickname
            broadcast_to_all: Broadcast a message to all clients
            broadcast_to_client: Broadcast a message to a client
            client_thread_loop: Send/Recieve loop for client
            remove_client: Remove a client connection
            tell_who: Send a list of all connected users to a client
        """
        self.exit_flag = False
        self.nicks = {}
        self.addrs = {}
        self.BUFSIZ = 4096
        self.sel = selectors.DefaultSelector()
        MAX_QUEUE = 5
        ADDR = (host, port)

        # Create the server socket
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind(ADDR)
            self.server.listen(MAX_QUEUE)
        except OSError as e:
            logging.critical(f'Error: {e}')
            sys.exit(1)

        # Register some select events
        self.sel.register(self.server, selectors.EVENT_READ, self.spawn_client)
        self.sel.register(sys.stdin, selectors.EVENT_READ, self.admin_input)

    def run(self):
        """Run the chat server."""
        # Start the main thread
        logging.info('Starting main thread, waiting for connections')

        try:
            accept_thread = threading.Thread(target=self.event_loop)
            accept_thread.daemon = True
            accept_thread.start()
            accept_thread.join()
        except KeyboardInterrupt:
            self.close_server()

        logging.info('Main thread exited.')

    def event_loop(self):
        """Select between reading from server socket and standard input."""
        while not self.exit_flag:
            ct = threading.currentThread()
            logging.info(f'Executing event loop in {ct.name}')

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
            print(f'Error: unknown command {command}')

    def close_server(self):
        """Shutdown the chat server."""
        # Say goobye
        self.broadcast_to_all('The lair is closed.')

        # Close the server
        try:
            self.server.close()
        except OSError as e:
            logging.warn(f'Error: {e}')
        finally:
            # Clean up selector
            self.sel.unregister(self.server)
            self.sel.unregister(sys.stdin)
            self.sel.close()

            # Set the exit flag
            self.exit_flag = True

    def who(self):
        """Print a list of all connected clients."""
        print('{:*^60}'.format(' The lair dwellers! '))
        for nick, addr in zip(self.nicks.values(), self.addrs.values()):
            print(f'{nick} at {addr}')

    def spawn_client(self, key, mask):
        """Spawn a new client thread."""
        try:
            sock, addr = self.server.accept()
        except OSError as e:
            print(f'Error: {e}')

        logging.info(f'{addr[0]}:{addr[1]} has connected')

        # Say hello
        msg = 'You have entered the lair!\nEnter your name!'
        self.broadcast_to_client(msg, sock)
        self.addrs[sock] = addr

        # Start the new thread
        logging.info(f'Starting a client thread for {addr[0]}:{addr[1]}')
        threading.Thread(target=self.handle_client, args=(sock,)).start()
        logging.info(f'Client thread for {addr[0]}:{addr[1]} started')

    def handle_client(self, sock):
        """Handles a single client connection."""
        # Get a unique nickname from the client
        nick = self.get_nick(sock)
        if nick:
            self.nicks[sock] = nick
        else:
            return

        # Welcome the new client to the lair
        msg = f'Welcome to the Lair {nick}! Type {{help}} for commands.'
        self.broadcast_to_client(msg, sock)

        # Inform other clients that a new one has connected
        msg = f'{nick} has entered the lair!'
        self.broadcast_to_all(msg, sock)

        # Start sending/recieving messages with client thread
        self.client_thread_loop(sock, nick)

    def get_nick(self, sock):
        """Get a unique nickname from the client."""
        while True:
            try:
                nick = sock.recv(self.BUFSIZ)
            except OSError as e:
                logging.warning(f'Error: {e}')
                return False

            # Decrypt and decode data
            nick = cipher.decrypt(nick)
            nick = nick.decode('utf-8', 'ignore')

            # Verify nickname
            if nick in self.nicks.values():
                msg = f'{nick} is already taken, choose another name.'
                self.broadcast_to_client(msg, sock)
            elif not nick.isalnum() or len(nick) > 8:
                msg = 'Your name must be alphanumeric only, e.g. The3vil1\n'
                msg = msg + 'and no longer than 8 characters.'
                self.broadcast_to_client(msg, sock)
            else:
                ip, port = self.addrs[sock]
                logging.info(f'{ip}:{port} logged in as {nick}')
                return nick

    def broadcast_to_all(self, msg, omit_client=None, prefix=''):
        """Broadcast a message to clients."""
        # Create the encrypted message
        msg = str(prefix) + str(msg)
        msg = cipher.encrypt(msg)

        # Check message length, if too long inform client
        if len(msg) >= self.BUFSIZ:
            msg = 'Message was too long to send.'
            self.broadcast_to_client(msg, omit_client)
            return

        # Broadcast message
        for sock in self.addrs:
            # Don't send a client it's own message
            if omit_client and sock == omit_client:
                continue

            # Send message
            try:
                sock.sendall(msg)
            except OSError as e:
                logging.warning(f'Broadcast error: {e}')
                msg = f'{self.nicks[sock]}'
                self.remove_client(sock, msg)

    def broadcast_to_client(self, msg, sock, prefix=''):
        """Broadcast a message to a single client."""
        # Create the encrypted message
        msg = str(prefix) + str(msg)
        msg = cipher.encrypt(msg)

        # Send message
        try:
            sock.sendall(msg)
        except OSError as e:
            logging.warning(f'Broadcast error: {e}')
            msg = f'{self.nicks[sock]}'
            self.remove_client(sock, msg)

    def client_thread_loop(self, sock, nick):
        """Send/Receive loop for client thread."""
        while not self.exit_flag:
            try:
                msg = sock.recv(self.BUFSIZ)
            except OSError as e:
                logging.warning(f'Error: {e}')
                self.remove_client(sock, nick)

            # Decrypt and decode the message
            msg = cipher.decrypt(msg)
            msg = msg.decode('utf-8', 'ignore')

            if msg == '{quit}':
                self.remove_client(sock, nick)
                break
            elif msg == '{who}':
                self.tell_who(sock)
            else:
                self.broadcast_to_all(msg, sock, nick + ': ')

    def remove_client(self, sock, nick):
        """Remove a client connection."""
        addr, port = self.addrs[sock]
        logging.info(f'{addr}:{port} has disconnected.')

        # Remove client from dictionaries
        if sock in self.addrs.copy():
            del self.addrs[sock]

        if sock in self.nicks.copy():
            del self.nicks[sock]

        # Broadcast departure
        msg = f'{nick} has left the lair.'
        self.broadcast_to_all(msg, sock)

        # Make sure client is disconnected
        try:
            sock.close()
        except OSError as e:
            logging.warn(f'remove_client: {e}')

    def tell_who(self, sock):
        """Send a list of connected users to a client."""
        for nick, addr in zip(self.nicks.values(), self.addrs.values()):
            msg = f'{nick} at {addr[0]}\n'
            self.broadcast_to_client(msg, sock)
            time.sleep(0.1)
