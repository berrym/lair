"""ChatServer.py

The Lair: Server class for a threaded chat application.
"""

import datetime
import logging
import os
import selectors
import sys
import threading
import time
from socket import *
from typing import *

from lairchat.crypto.AESCipher import aes_cipher

logfilename = os.path.join(os.path.expanduser('~'), '.lair.log')

# Enable logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)-15s [%(threadName)-12s]'
           + '[%(levelname)-8s]  %(message)s',
    handlers=[logging.FileHandler(logfilename), logging.StreamHandler()])


def timestamp() -> str:
    """Create a timestamp."""
    d_time = datetime.datetime.now()
    hour = str(d_time.hour).zfill(2)
    minute = str(d_time.minute).zfill(2)
    second = str(d_time.second).zfill(2)
    return f'[{hour}:{minute}:{second}]'


class ChatServer():
    """A simple chat room server."""

    def __init__(self, host: str, port: int) -> None:
        """Initialize the chat server."""
        self.exit_flag = False
        self.users: Dict[socket, str] = {}
        self.addresses: Dict[socket, Tuple[str, int]] = {}
        self.buf_size = 4096
        self.sel = selectors.DefaultSelector()
        max_queue = 5
        address = (host, port)

        # Create the server socket
        try:
            self.server = socket(AF_INET, SOCK_STREAM)
            self.server.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            self.server.bind(address)
            self.server.listen(max_queue)
        except OSError as e:
            logging.critical(f'Error: {e}')
            sys.exit(1)

        # Register some select events
        self.sel.register(self.server,
                          selectors.EVENT_READ,
                          self.spawn_client)
        self.sel.register(sys.stdin, selectors.EVENT_READ, self.admin_input)

    def run(self) -> None:
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

        logging.info('Main thread exited')

    def event_loop(self) -> None:
        """Select between reading from server socket and standard input."""
        while not self.exit_flag:
            logging.info('Executing event loop')

            events = self.sel.select()
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)

    def admin_input(self, key: selectors.SelectorKey, mask) -> None:
        """Read from standard input for administrative commands."""
        command = input('')
        if command == 'quit':
            self.close_server()
        elif command == 'who':
            self.who()
        else:
            print(f'error: unknown command {command}')

    def close_server(self) -> None:
        """Shutdown the chat server."""
        # Say goodbye
        self.broadcast_to_all('The lair is closed.')

        # Close the server
        try:
            self.server.close()
        except OSError as e:
            logging.warning(f'Error: {e}')
        finally:
            # Clean up selector
            self.sel.unregister(self.server)
            self.sel.unregister(sys.stdin)
            self.sel.close()

            # Set the exit flag
            self.exit_flag = True

    def who(self) -> None:
        """Print a list of all connected clients."""
        print('{:*^60}'.format(' The lair dwellers! '))
        for user, address in zip(
                self.users.values(), self.addresses.values()):
            print(f'{user} at {address}')

    def spawn_client(self, key: selectors.SelectorKey, mask) -> None:
        """Spawn a new client thread."""
        try:
            sock, address = self.server.accept()
        except OSError as e:
            logging.warning(f'Error: {e}')
            return

        logging.info(f'{address} has connected')

        # Say hello
        msg = 'You have entered the lair!\nEnter your name!'
        self.broadcast_to_client(msg, sock)
        self.addresses[sock] = address

        # Start the new thread
        logging.info(f'Starting a client thread for {address}')
        threading.Thread(target=self.handle_client, args=(sock,)).start()
        logging.info(f'Client thread for {address} started')

    def handle_client(self, sock: socket) -> None:
        """Handles a single client connection."""
        # Get a unique username from the client
        user = self.get_user(sock)
        if user is not '':
            self.users[sock] = user
        else:
            return

        # Welcome the new client to the lair
        msg = f'Welcome to the Lair {user}! Type {{help}} for commands.'
        self.broadcast_to_client(msg, sock)

        # Inform other clients that a new one has connected
        msg = f'{user} has entered the lair!'
        self.broadcast_to_all(msg, sock)

        # Start sending/receiving messages with client thread
        self.client_thread_loop(sock, user)

    def get_user(self, sock: socket) -> str:
        """Get a unique username from the client."""
        while True:
            try:
                data = sock.recv(self.buf_size)
            except OSError as e:
                logging.warning(f'Error: {e}')
                return ''

            # Decrypt and decode data
            decrypted = aes_cipher.decrypt(data)
            if decrypted is None:
                self.remove_client(sock, '')
                return ''
            user = decrypted.decode('utf-8', 'ignore')

            # Verify username
            if user in self.users.values():
                msg = f'{user} is already taken, choose another name.'
                self.broadcast_to_client(msg, sock)
            elif not user.isalnum() or len(user) > 8:
                msg = 'Your name must be alphanumeric only, e.g. The3vil1\n'
                msg = msg + 'and no longer than 8 characters.'
                self.broadcast_to_client(msg, sock)
            else:
                logging.info(f'{self.addresses[sock]} logged in as {user}')
                return user

    def broadcast_to_all(self,
                         message: str,
                         omit_client: Union[socket, None] = None) -> None:
        """Broadcast a message to clients."""
        # Create the encrypted message
        encrypted_message = aes_cipher.encrypt(message)
        if encrypted_message is None and omit_client:
            self.remove_client(omit_client, self.users[omit_client])
            return

        # Check message length, if too long inform client
        if len(encrypted_message) >= self.buf_size and omit_client:
            encrypted_message = 'Message was too long to send.'
            self.broadcast_to_client(encrypted_message, omit_client)
            return

        # Broadcast message
        for sock in self.addresses:
            # Don't send a client it's own message
            if omit_client and sock == omit_client:
                continue

            # Send message
            try:
                sock.sendall(encrypted_message)
            except OSError as e:
                logging.warning(f'Broadcast error: {e}')
                message = f'{self.users[sock]}'
                self.remove_client(sock, message)

    def broadcast_to_client(self, message: str, sock: socket) -> None:
        """Broadcast a message to a single client."""
        # Create the encrypted message
        encrypted_message = aes_cipher.encrypt(message)
        if encrypted_message is None:
            self.remove_client(sock, self.users[sock])
            return

        # Send message
        try:
            sock.sendall(encrypted_message)
        except OSError as e:
            logging.warning(f'Broadcast error: {e}')
            message = f'{self.users[sock]}'
            self.remove_client(sock, message)

    def client_thread_loop(self, sock: socket, user: str):
        """Send/Receive loop for client thread."""
        while not self.exit_flag:
            try:
                data = sock.recv(self.buf_size)
            except OSError as e:
                logging.warning(f'Receive error: {e}')
                self.remove_client(sock, user)
                return

            # Decrypt and decode the message
            decrypted_data = aes_cipher.decrypt(data)
            if decrypted_data is None:
                self.remove_client(sock, user)
                return
            message = decrypted_data.decode('utf-8', 'ignore')

            if message == '{quit}':
                self.remove_client(sock, user)
                break
            elif message == '{who}':
                self.tell_who(sock)
            else:
                message = f'{timestamp()}\n{user}: {message}'
                self.broadcast_to_all(message, sock)

    def remove_client(self, sock: socket, user: str) -> None:
        """Remove a client connection."""
        logging.info(f'{self.addresses[sock]} has disconnected.')

        # Remove client from dictionaries
        if sock in self.addresses.copy():
            del self.addresses[sock]

        if sock in self.users.copy():
            del self.users[sock]

        # Broadcast departure
        if user is not '':
            msg = f'{user} has left the lair.'
            self.broadcast_to_all(msg, sock)

        # Make sure client is disconnected
        try:
            sock.close()
        except OSError as e:
            logging.warning(f'remove_client: {e}')

    def tell_who(self, sock: socket) -> None:
        """Send a list of connected users to a client."""
        for user, address in zip(
                self.users.values(), self.addresses.values()):
            msg = f'{user} at {address[0]}\n'
            self.broadcast_to_client(msg, sock)
            time.sleep(0.1)
