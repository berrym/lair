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
from PyQt5.QtCore import QThread
from modules.AESCipher import cipher


# Global variables
ADDR = '127.0.0.1'
PORT = 1234
TCP_CLIENT = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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

    def __init__(self):
        """Create a simple dialog.

        Populate address and port of server with user input.
        """
        super().__init__()
        self.addressLabel = QtWidgets.QLabel('Server Address', self)
        self.addressField = QtWidgets.QLineEdit(self)
        self.addressField.setText(ADDR)
        self.portLabel = QtWidgets.QLabel('Server Port', self)
        self.portField = QtWidgets.QLineEdit(self)
        self.portField.setText(str(PORT))
        self.btnConnect = QtWidgets.QPushButton('Connect', self)
        self.btnConnect.clicked.connect(self.set_host)
        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.addWidget(self.addressLabel)
        self.vbox.addWidget(self.addressField)
        self.vbox.addWidget(self.portLabel)
        self.vbox.addWidget(self.portField)
        self.vbox.addWidget(self.btnConnect)
        self.setLayout(self.vbox)
        self.setWindowTitle('Connect to Lair Server')

    def set_host(self):
        """Get user input from the text fields.

        Set global host variables ADDR and PORT then exit dialog."""
        global ADDR
        global PORT
        ADDR = self.addressField.text()
        PORT = int(self.portField.text())
        self.close()


class ChatWindow(QtWidgets.QDialog):
    """Graphical chat window."""

    def __init__(self):
        """Initialize the chat window.

        Create all gui components.
        """
        super().__init__()
        self.chatTextField = QtWidgets.QLineEdit(self)
        self.chatTextField.resize(480, 100)
        self.chatTextField.move(10, 350)

        self.btnSend = QtWidgets.QPushButton("Send", self)
        self.btnSend.resize(480, 30)
        self.btnSendFont = self.btnSend.font()
        self.btnSendFont.setPointSize(12)
        self.btnSend.setFont(self.btnSendFont)
        self.btnSend.move(10, 460)
        self.btnSend.clicked.connect(self.send)
        self.chatBody = QtWidgets.QVBoxLayout(self)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.chat = QtWidgets.QTextEdit()
        self.chat.setReadOnly(True)
        splitter.addWidget(self.chat)
        splitter.addWidget(self.chatTextField)
        splitter.setSizes([400, 100])

        splitter2 = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        splitter2.addWidget(splitter)
        splitter2.addWidget(self.btnSend)
        splitter2.setSizes([200, 10])
        self.chatBody.addWidget(splitter2)

        self.setWindowTitle('The Lair')
        self.resize(500, 500)
        self.chatTextField.setFocus()

    def closeEvent(self, event):
        """Quit app when the window is closed."""
        self.quit()
        event.accept()

    def quit(self, event=None):
        """Exit the program."""
        global ANNOUNCE_EXIT
        global TCP_CLIENT

        if ANNOUNCE_EXIT:
            try:
                data = '{quit}'
                data = cipher.encrypt(data)
                TCP_CLIENT.sendall(data)
            except OSError as e:
                CriticalError(self, f'Chat window->quit: {e}')
            finally:
                TCP_CLIENT.close()
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
            TCP_CLIENT.sendall(data)
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


class ClientThread(QThread):
    """Create a client thread for networking communications."""
    def __init__(self, window):
        """Initialize the thread."""
        QThread.__init__(self)
        self.window = window

    def __del__(self):
        """Thread cleanup."""
        self.wait()

    def quit(self):
        """Exit the program."""
        exit(self.window.quit())

    def recv_loop(self):
        """Read data from server."""
        BUFSIZ = 4096
        global ANNOUNCE_EXIT

        while not ANNOUNCE_EXIT:
            try:
                data = TCP_CLIENT.recv(BUFSIZ)
            except OSError as e:
                CriticalError(self.window, f'recv: {e}')
                exit(self.quit())

            # Make sure the other thread hasn't called quit yet
            # If it has, stop executing this frame
            if ANNOUNCE_EXIT:
                exit(0)

            # Decrypyt and decode the data
            decrypted = cipher.decrypt(data)
            if decrypted is None:
                CriticalError(self.window, 'unable to decrypt message')
                exit(self.quit())

            msg = decrypted.decode('utf-8', 'ignore')

            # The server closed, do NOT set ANNOUNCE_EXIT
            if msg == 'The lair is closed.':
                exit(self.quit())

            # add recieved text to chat field
            self.window.chat.append(formatText(color='blue', text=msg))

    def run(self):
        """Run the client thread."""
        global TCP_CLIENT
        try:
            TCP_CLIENT.connect((ADDR, PORT))
        except OSError as e:
            CriticalError(self.window, e)
            return self.quit()

        # recieve loop
        self.recv_loop()


def main():
    """Main function."""
    app = QtWidgets.QApplication(sys.argv)
    conn_win = ConnectionDialog()
    conn_win.exec_()
    main_win = ChatWindow()
    ct = ClientThread(main_win)
    ct.start()
    main_win.exec_()
    app.exec_()


# __main__? Program entry point
if __name__ == '__main__':
    sys.exit(main())
