#!/usr/bin/env python3


"""lair_client-qt.py

Simple Qt client to The Lair chat server.

Copyright (C) 2019 Michael Berry

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


import sys
import socket
from PyQt5 import QtCore, QtWidgets
from modules.AESCipher import cipher


# Global variables
ANNOUNCE_EXIT = False


def formatText(color='black', text=''):
    """Perform some basic formatting on text."""
    return f'<font color="{color}">{text}</font>'.replace('\n', '<br>')


def CriticalError(parent=None, err=None):
    """Display an error message."""
    QtWidgets.QMessageBox.critical(parent,
                                   'Error',
                                   str(err),
                                   QtWidgets.QMessageBox.Ok)


class ConnectionDialog(QtWidgets.QDialog):
    """Get Server Options."""

    def __init__(self, conn):
        """Create a simple dialog.

        Populate address and port of server with user input.
        """
        super().__init__()

        # Address
        addressLabel = QtWidgets.QLabel('Server Address', self)
        self.addressField = QtWidgets.QLineEdit(self)
        self.addressField.setText('127.0.0.1')

        # Port
        portLabel = QtWidgets.QLabel('Server Port', self)
        self.portField = QtWidgets.QLineEdit(self)
        self.portField.setText('8888')

        # Click button
        btnConnect = QtWidgets.QPushButton('Connect', self)
        btnConnect.clicked.connect(self.set_host)

        # Create a vertical box layout
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(addressLabel)
        vbox.addWidget(self.addressField)
        vbox.addWidget(portLabel)
        vbox.addWidget(self.portField)
        vbox.addWidget(btnConnect)

        # Set the layout
        self.setLayout(vbox)
        self.setWindowTitle('Connect to Lair Server')

        self.conn = conn

    def set_host(self):
        """Get user input from the text fields.

        Set global host variables ADDR and PORT then exit dialog."""
        #global ADDR
        #global PORT
        addr = self.addressField.text()
        port = int(self.portField.text())
        self.conn.append((addr, port))
        self.accept()


class ChatWindow(QtWidgets.QDialog):
    """Graphical chat window."""

    def __init__(self, sock):
        """Initialize the chat window.

        Create all gui components.
        """
        super().__init__()
        self.chatTextField = QtWidgets.QLineEdit(self)
        self.chatTextField.resize(480, 100)
        self.chatTextField.move(10, 350)

        btnSend = QtWidgets.QPushButton("Send", self)
        btnSend.resize(480, 30)
        btnSendFont = btnSend.font()
        btnSendFont.setPointSize(12)
        btnSend.setFont(btnSendFont)
        btnSend.move(10, 460)
        btnSend.clicked.connect(self.send)

        self.chatBody = QtWidgets.QVBoxLayout(self)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.chat = QtWidgets.QTextEdit()
        self.chat.setReadOnly(True)
        splitter.addWidget(self.chat)
        splitter.addWidget(self.chatTextField)
        splitter.setSizes([400, 100])

        splitter2 = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        splitter2.addWidget(splitter)
        splitter2.addWidget(btnSend)
        splitter2.setSizes([200, 10])
        self.chatBody.addWidget(splitter2)

        self.setWindowTitle('The Lair')
        self.resize(500, 500)
        self.chatTextField.setFocus()

        self.sock = sock

    def closeEvent(self, event):
        """Quit app when the window is closed."""
        self.quit()
        event.accept()

    def quit(self, event=None):
        """Exit the program."""
        global ANNOUNCE_EXIT

        if ANNOUNCE_EXIT:
            try:
                data = '{quit}'
                data = cipher.encrypt(data)
                self.sock.sendall(data)
            except OSError as e:
                CriticalError(self, f'Chat window->quit: {e}')
            finally:
                self.sock.close()
        else:
            ANNOUNCE_EXIT = True

        exit(0)

    def send(self):
        """Send text to the lair server."""
        global ANNOUNCE_EXIT
        text = self.chatTextField.text()

        if text == '{help}':
            self.chatTextField.setText('')
            return self.help()
        elif text == '{quit}':
            ANNOUNCE_EXIT = True
            exit(self.quit())

        # Encrpyt the text
        data = cipher.encrypt(text)
        if data is None:
            CriticalError(self, 'unable to encrypt data.')
            exit(self.quit())

        # Send the text
        try:
            self.sock.sendall(data)
        except OSError as e:
            CriticalError(self.window, e)
            exit(self.quit())

        # Decrypt the text
        decrypted = cipher.decrypt(data)
        msg = decrypted.decode('utf-8', 'ignore')

        # Update UI
        self.chat.append(msg)
        self.chatTextField.setText('')

    def help(self):
        """Print a list of available commands."""
        self.chat.append('Available Commands:\n')
        self.chat.append('\t{help}:\tThis help menu')
        self.chat.append('\t{quit}:\tExit program')
        self.chat.append('\t{who}\tList of user names in the lair.')


class ClientThread(QtCore.QThread):
    """Create a client thread for networking communications."""

    def __init__(self, window, sock):
        """Initialize the thread."""
        QtCore.QThread.__init__(self)
        self.window = window
        self.sock = sock

    def __del__(self):
        """Thread cleanup."""
        self.wait()

    def recv_loop(self):
        """Read data from server."""
        BUFSIZ = 4096

        try:
            data = self.sock.recv(BUFSIZ)
        except OSError as e:
            CriticalError(self.window, f'recv: {e}')
            exit(self.window.quit())

        # Make sure the other thread hasn't called quit yet
        # If it has, stop executing this frame
        if ANNOUNCE_EXIT:
            exit(0)

        # Decrypyt and decode the data
        decrypted = cipher.decrypt(data)
        if decrypted is None:
            CriticalError(self.window, 'unable to decrypt message')
            exit(self.window.quit())

        msg = decrypted.decode('utf-8', 'ignore')

        # The server closed, do NOT set ANNOUNCE_EXIT
        if msg == 'The lair is closed.':
            exit(self.window.quit())

        # add recieved text to chat field
        self.window.chat.append(formatText(color='blue', text=msg))

    def run(self):
        """Run the client thread."""
        global ANNOUNCE_EXIT
        while not ANNOUNCE_EXIT:
            self.recv_loop()


def main():
    """Main function."""
    conn = []
    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    app = QtWidgets.QApplication(sys.argv)

    conn_win = ConnectionDialog(conn)
    conn_win.exec_()

    try:
        tcp_sock.connect(conn[0])
    except OSError as e:
        CriticalError(None, e)
        exit(1)

    main_win = ChatWindow(tcp_sock)

    ct = ClientThread(main_win, tcp_sock)
    ct.start()

    main_win.exec_()
    app.exec_()


# __main__? Program entry point
if __name__ == '__main__':
    sys.exit(main())
