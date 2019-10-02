"""ChatServer.py

The Lair: Threaded server class for a chat application.
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


def broadcast_to_client(message: str, sock: socket) -> None:
    """Broadcast a message to a single client."""
    # Create the encrypted message
    encrypted_message = aes_cipher.encrypt(message)
    if encrypted_message is None:
        return

    # Send message
    try:
        sock.sendall(encrypted_message)
    except OSError as e:
        logging.warning(f'Broadcast error: {e}')


class ChatServer:
    """A simple chat room server."""

    def __init__(self, host: str, port: int) -> None:
        """Initialize the chat server."""
        self.exit_flag = False
        self.connections: Dict[str, Dict] = {}
        self.buf_size = 4096
        self.sel = selectors.DefaultSelector()

        # Create the server socket
        try:
            self.server = socket(AF_INET, SOCK_STREAM)
            self.server.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            self.server.bind((host, port))
            self.server.listen(5)
        except OSError as e:
            logging.critical(f'Error: {e}')
            sys.exit(1)

        # Register some select events
        self.sel.register(self.server,
                          selectors.EVENT_READ,
                          self.spawn_connection)
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
        print(f'{" The lair dwellers! ":*^60}')
        for username, info in self.connections.items():
            print(f'{username} @ {info["address"]}')

    def spawn_connection(self, key: selectors.SelectorKey, mask) -> None:
        """Spawn a new client thread."""
        try:
            sock, address = self.server.accept()
        except OSError as e:
            logging.warning(f'Error: {e}')
            return

        logging.info(f'{address} has connected')

        # Say hello
        message = 'You have entered the lair!\nEnter your name!'
        broadcast_to_client(message, sock)

        # Start the new thread
        logging.info(f'Starting a client thread for {address}')
        threading.Thread(
            target=self.handle_connection, args=(sock, address,)).start()
        logging.info(f'Client thread for {address} started')

    def handle_connection(
            self, sock: socket, address: Tuple[str, int]) -> None:
        """Handles a single client connection."""
        # Get a unique username from the client
        username = self.prompt_username(sock)
        if username is not '':
            self.connections[username] = {}
            self.connections[username]['socket'] = sock
            self.connections[username]['address'] = address
        else:
            return

        logging.info(f'{address} logged in as {username}')

        # Welcome the new client to the lair
        message = f'Hello {username}!  Type {{help}} for commands.'
        broadcast_to_client(message, sock)

        # Inform other clients that a new one has connected
        self.broadcast_to_all(f'{username} has entered the lair!', username)

        # Start sending/receiving messages with client thread
        self.connection_thread_loop(username)

    def prompt_username(self, sock: socket) -> str:
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
                return ''
            username = decrypted.decode('utf-8', 'ignore')

            # Verify username
            if username in self.connections.keys():
                message = f'{username} is already taken, choose another name.'
                broadcast_to_client(message, sock)
            elif not username.isalnum() or len(username) > 8:
                message = 'Your name must be alphanumeric only\n'
                message = message + 'and no longer than 8 characters.\n'
                message = message + 'e.g, The3vil1'
                broadcast_to_client(message, sock)
            else:
                return username

    def broadcast_to_all(self,
                         message: str,
                         omit_username: Union[str, None] = None) -> None:
        """Broadcast a message to clients."""
        # Create the encrypted message
        encrypted_message = aes_cipher.encrypt(message)
        if encrypted_message is None:
            return

        # Check message length, if too long inform client
        if len(encrypted_message) >= (self.buf_size / 4) and omit_username:
            info = self.connections[omit_username]
            encrypted_message = 'Message was too long to send.'
            broadcast_to_client(encrypted_message, info['socket'])
            return

        # Broadcast message
        for username in self.connections.keys():
            # Don't send a client it's own message
            if omit_username and username == omit_username:
                continue

            # Send message
            try:
                self.connections[username]['socket'].sendall(
                    encrypted_message)
            except OSError as e:
                logging.warning(f'Broadcast error: {e}')
                self.remove_client(username)

    def connection_thread_loop(self, username: str) -> None:
        """Send/Receive loop for client thread."""
        while not self.exit_flag:
            try:
                data = self.connections[username]['socket'].recv(
                    self.buf_size)
            except OSError as e:
                logging.warning(f'Receive error: {e}')
                self.remove_client(username)
                return

            # Decrypt and decode the message
            decrypted_data = aes_cipher.decrypt(data)
            if decrypted_data is None:
                return
            message = decrypted_data.decode('utf-8', 'ignore')

            if message == '{quit}':
                self.remove_client(username)
                break
            elif message == '{who}':
                self.tell_who(username)
            else:
                message = f'{timestamp()}\n{username}: {message}'
                self.broadcast_to_all(message, username)

    def remove_client(self, username: str) -> None:
        """Remove a client connection."""
        info = self.connections[username]
        logging.info(f'{username} @ {info["address"]} has disconnected.')
        self.broadcast_to_all(f'{username} has left the lair.', username)
        del self.connections[username]

    def tell_who(self, username: str) -> None:
        """Send a list of connected username's to a client."""
        sock = self.connections[username]['socket']
        for username, info in self.connections.items():
            broadcast_to_client(f'{username} @ {info["address"][0]}', sock)
            time.sleep(0.1)
