"""ChatServer.py

The Lair: Server class for multithreaded (asynchronous) chat application.
"""

import datetime
import logging
import os
import selectors
import socket
import sys
import threading
import time
from typing import *

from modules.crypto.AESCipher import aes_cipher

logfilename = os.path.join(os.path.expanduser('~'), '.lair.log')

# Enable logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)-15s [%(threadName)-12s]'
           + '[%(levelname)-8s]  %(message)s',
    handlers=[logging.FileHandler(logfilename), logging.StreamHandler()])


class ChatServer():
    """A simple chat room server."""

    def __init__(self, host: str, port: int) -> None:
        """Initialize the chat server."""
        self.exit_flag = False
        self.nicks: Dict[socket.socket, str] = {}
        self.addrs: Dict[socket.socket, Tuple[str, int]] = {}
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
        for nick, addr in zip(self.nicks.values(), self.addrs.values()):
            print(f'{nick} at {addr}')

    def spawn_client(self, key: selectors.SelectorKey, mask) -> None:
        """Spawn a new client thread."""
        try:
            sock, addr = self.server.accept()
        except OSError as e:
            logging.warning(f'Error: {e}')
            return

        logging.info(f'{addr} has connected')

        # Say hello
        msg = 'You have entered the lair!\nEnter your name!'
        self.broadcast_to_client(msg, sock)
        self.addrs[sock] = addr

        # Start the new thread
        logging.info(f'Starting a client thread for {addr}')
        threading.Thread(target = self.handle_client, args = (sock,)).start()
        logging.info(f'Client thread for {addr} started')

    def handle_client(self, sock: socket.socket) -> None:
        """Handles a single client connection."""
        # Get a unique nickname from the client
        nick = self.get_nick(sock)
        if nick is not '':
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

    def get_nick(self, sock: socket.socket) -> str:
        """Get a unique nickname from the client."""
        while True:
            try:
                data = sock.recv(self.BUFSIZ)
            except OSError as e:
                logging.warning(f'Error: {e}')
                return ''

            # Decrypt and decode data
            decrypted = aes_cipher.decrypt(data)
            if decrypted is None:
                self.remove_client(sock, '')
                return ''
            nick = decrypted.decode('utf-8', 'ignore')

            # Verify nickname
            if nick in self.nicks.values():
                msg = f'{nick} is already taken, choose another name.'
                self.broadcast_to_client(msg, sock)
            elif not nick.isalnum() or len(nick) > 8:
                msg = 'Your name must be alphanumeric only, e.g. The3vil1\n'
                msg = msg + 'and no longer than 8 characters.'
                self.broadcast_to_client(msg, sock)
            else:
                logging.info(f'{self.addrs[sock]} logged in as {nick}')
                return nick

    def broadcast_to_all(self,
                         msg: str,
                         omit_client: Union[socket.socket, None] = None) \
            -> None:
        """Broadcast a message to clients."""
        # Create the encrypted message
        b_msg = aes_cipher.encrypt(msg)
        if b_msg is None and omit_client:
            self.remove_client(omit_client, self.nicks[omit_client])
            return

        # Check message length, if too long inform client
        if len(b_msg) >= self.BUFSIZ and omit_client:
            b_msg = 'Message was too long to send.'
            self.broadcast_to_client(b_msg, omit_client)
            return

        # Broadcast message
        for sock in self.addrs:
            # Don't send a client it's own message
            if omit_client and sock == omit_client:
                continue

            # Send message
            try:
                sock.sendall(b_msg)
            except OSError as e:
                logging.warning(f'Broadcast error: {e}')
                msg = f'{self.nicks[sock]}'
                self.remove_client(sock, msg)

    def broadcast_to_client(self, msg: str, sock: socket.socket) -> None:
        """Broadcast a message to a single client."""
        # Create the encrypted message
        b_msg = aes_cipher.encrypt(msg)
        if b_msg is None:
            self.remove_client(sock, self.nicks[sock])
            return

        # Send message
        try:
            sock.sendall(b_msg)
        except OSError as e:
            logging.warning(f'Broadcast error: {e}')
            msg = f'{self.nicks[sock]}'
            self.remove_client(sock, msg)

    def client_thread_loop(self, sock: socket.socket, nick: str):
        """Send/Receive loop for client thread."""
        while not self.exit_flag:
            try:
                data = sock.recv(self.BUFSIZ)
            except OSError as e:
                logging.warning(f'Receive error: {e}')
                self.remove_client(sock, nick)
                return

            # Decrypt and decode the message
            decrypted = aes_cipher.decrypt(data)
            if decrypted is None:
                self.remove_client(sock, nick)
                return
            msg = decrypted.decode('utf-8', 'ignore')

            if msg == '{quit}':
                self.remove_client(sock, nick)
                break
            elif msg == '{who}':
                self.tell_who(sock)
            else:
                dtime = datetime.datetime.now()
                hour = str(dtime.hour).zfill(2)
                minute = str(dtime.minute).zfill(2)
                sec = str(dtime.second).zfill(2)
                timestamp = f'{hour}:{minute}:{sec}'
                prefix = f'[{timestamp}]\n{nick}: '
                msg = f'{prefix}{msg}'
                self.broadcast_to_all(msg, sock)

    def remove_client(self, sock: socket.socket, nick: str) -> None:
        """Remove a client connection."""
        logging.info(f'{self.addrs[sock]} has disconnected.')

        # Remove client from dictionaries
        if sock in self.addrs.copy():
            del self.addrs[sock]

        if sock in self.nicks.copy():
            del self.nicks[sock]

        # Broadcast departure
        if nick is not '':
            msg = f'{nick} has left the lair.'
            self.broadcast_to_all(msg, sock)

        # Make sure client is disconnected
        try:
            sock.close()
        except OSError as e:
            logging.warning(f'remove_client: {e}')

    def tell_who(self, sock: socket.socket) -> None:
        """Send a list of connected users to a client."""
        for nick, addr in zip(self.nicks.values(), self.addrs.values()):
            msg = f'{nick} at {addr[0]}\n'
            self.broadcast_to_client(msg, sock)
            time.sleep(0.1)
