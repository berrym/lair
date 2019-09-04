#!/usr/bin/env python3

"""lair_client-qt.py

Simple Qt client to The Lair chat server.

Copyright (C) <2019>  <Michael Berry>

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

import os
import sys
import socket
import psutil
from threading import Thread
from PyQt5 import QtCore, QtWidgets
from modules.AESCipher import cipher


# Global variables
ADDR = '127.0.0.1'
PORT = 1234
TCP_CLIENT = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
EXIT_FLAG = False


def kill_proc_tree(pid):
    """Kill the entrire process tree."""
    parent = psutil.Process(pid)
    parent.kill()


def formatText(color='black', text=''):
    """Perform some basic formatting on text."""
    return ('<font color="{}">{}</font>'.format(color, text).replace('\n', '<br>'))


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

    def quit(self):
        """Exit the program."""
        TCP_CLIENT.shutdown(socket.SHUT_RDWR)
        TCP_CLIENT.close()
        self.close()
        kill_proc_tree(os.getpid())

    def send(self):
        """Send text to the lair server."""
        global EXIT_FLAG
        text = self.chatTextField.text()
        font = self.chat.font()
        self.chat.setFont(font)

        if text == '{help}':
            self.chatTextField.setText('')
            return self.help()
        elif text == '{quit}':
            self.chatTextField.setText('')

            try:
                text = cipher.encrypt(text)
                TCP_CLIENT.send(text)
            except (OSError, UnicodeDecodeError) as err:
                CriticalError(self.window, err)

            EXIT_FLAG = True

        # Check if EXIT_FLAG is set
        if EXIT_FLAG:
            self.quit()

        try:
            text = cipher.encrypt(text)
            TCP_CLIENT.send(text)
        except OSError as err:
            CriticalError(self.window, err)
            self.quit()

        # Update UI
        text = cipher.decrypt(text)
        text = text.decode('utf-8', 'ignore')
        self.chat.append(text)
        self.chatTextField.setText('')

    def help(self):
        """Print a list of available commands."""
        self.chat.append('Available Commands:\n')
        self.chat.append('\t{help}:\tThis help menu')
        self.chat.append('\t{quit}:\tExit program')
        self.chat.append('\t{who}\tList of user names in the lair.')


class ClientThread(Thread):
    """Create a client thread for networking communications."""
    def __init__(self, window):
        """Initialize the thread."""
        Thread.__init__(self)
        self.window = window

    def quit(self):
        """Exit the program."""
        global TCP_CLIENT
        TCP_CLIENT.shutdown(socket.SHUT_RDWR)
        TCP_CLIENT.close()
        self.window.close()
        kill_proc_tree(os.getpid())

    def recv_loop(self):
        """Read data from server."""
        BUFSIZ = 4096
        global EXIT_FLAG

        while not EXIT_FLAG:
            try:
                data = TCP_CLIENT.recv(BUFSIZ)
                data = cipher.decrypt(data)
                data = data.decode('utf-8', 'ignore')
            except (OSError, UnicodeDecodeError) as err:
                CriticalError(self.window, err)
                EXIT_FLAG = True

            # The server closed, set EXIT_FLAG
            if data == 'The lair is closed.':
                EXIT_FLAG = True

            # add recieved text to chat field
            self.window.chat.append(formatText(color='blue', text=data))

        self.quit()

    def run(self):
        """Run the client thread."""
        global EXIT_FLAG

        try:
            TCP_CLIENT.connect((ADDR, PORT))
        except OSError as err:
            CriticalError(self.window, err)
            EXIT_FLAG = True

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
    sys.exit(app.exec_())


# __main__? Program entry point
if __name__ == '__main__':
    main()
