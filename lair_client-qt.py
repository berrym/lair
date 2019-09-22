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
from PyQt5 import QtCore, QtGui, QtWidgets
from modules.AESCipher import aes_cipher


# Global variables
ANNOUNCE_EXIT = False


def format_text(color='black', text=''):
    """Perform some basic formatting on text."""
    return f'<font color="{color}">{text}</font>'.replace('\n', '<br>')


def critical_error(parent=None, err=None):
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
        address_label = QtWidgets.QLabel('Server Address', self)
        self.address_field = QtWidgets.QLineEdit(self)
        self.address_field.setText('127.0.0.1')

        # Port
        port_label = QtWidgets.QLabel('Server Port', self)
        self.port_field = QtWidgets.QLineEdit(self)
        self.port_field.setText('8888')

        # Click button
        btn_connect = QtWidgets.QPushButton('Connect', self)
        btn_connect.clicked.connect(self.set_host)

        # Create a vertical box layout
        v_box = QtWidgets.QVBoxLayout()
        v_box.addWidget(address_label)
        v_box.addWidget(self.address_field)
        v_box.addWidget(port_label)
        v_box.addWidget(self.port_field)
        v_box.addWidget(btn_connect)

        # Set the layout
        self.setLayout(v_box)
        self.setWindowTitle('Connect to Lair Server')

        self.conn = conn

    def set_host(self):
        """Get user input from the text fields.

        Set global host variables ADDR and PORT then exit dialog."""
        address = self.address_field.text()
        port = int(self.port_field.text())
        self.conn.append((address, port))
        self.accept()


class ChatWindow(QtWidgets.QMainWindow):
    """Graphical chat window."""
    def __init__(self):
        """Initialize the chat window."""
        super().__init__()
        self.chat_view = QtWidgets.QTextEdit()
        self.chat_text_field = QtWidgets.QLineEdit(self)
        self.window_frame = QtWidgets.QVBoxLayout(self)
        self.initUI()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn = []

    def initUI(self):
        """Create all gui components."""
        exit_act = QtWidgets.QAction(QtGui.QIcon(''), 'Exit', self)
        exit_act.setShortcut('Ctrl+Q')
        exit_act.setStatusTip('Exit application')
        exit_act.triggered.connect(self.close)

        conn_act = QtWidgets.QAction(QtGui.QIcon(''), 'Connect', self)
        conn_act.setShortcut('F2')
        conn_act.setStatusTip('Connect To a Lair')
        conn_act.triggered.connect(self.connect)

        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu('&File')
        file_menu.addAction(conn_act)
        file_menu.addAction(exit_act)
        self.window_frame.addWidget(menu_bar)

        self.chat_text_field.resize(480, 100)
        self.chat_text_field.move(10, 350)

        btn_send = QtWidgets.QPushButton("Send", self)
        btn_send.resize(480, 30)
        btn_send_font = btn_send.font()
        btn_send_font.setPointSize(12)
        btn_send.setFont(btn_send_font)
        btn_send.move(10, 460)
        btn_send.clicked.connect(self.send)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.chat_view.setReadOnly(True)
        splitter.addWidget(self.chat_view)
        splitter.addWidget(self.chat_text_field)
        splitter.setSizes([400, 100])

        splitter2 = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        splitter2.addWidget(splitter)
        splitter2.addWidget(btn_send)
        splitter2.setSizes([200, 10])

        self.window_frame.addWidget(splitter2)
        self.setCentralWidget(splitter2)

        self.setWindowTitle('The Lair')
        self.resize(500, 500)
        self.chat_text_field.setFocus()

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
                data = aes_cipher.encrypt(data)
                self.sock.sendall(data)
            except OSError as e:
                critical_error(self, f'Chat window->quit: {e}')
            finally:
                self.sock.close()
        else:
            ANNOUNCE_EXIT = True

        exit(0)

    def connect(self):
        conn_win = ConnectionDialog(self.conn)
        conn_win.exec_()
        ct = ClientThread(self)
        ct.start()

    def send(self):
        """Send text to the lair server."""
        global ANNOUNCE_EXIT
        text = self.chat_text_field.text()

        if text == '{help}':
            self.chat_text_field.setText('')
            return self.help()
        elif text == '{quit}':
            ANNOUNCE_EXIT = True
            exit(self.quit())

        # Encrypt the text
        data = aes_cipher.encrypt(text)
        if data is None:
            critical_error(self, 'unable to encrypt data.')
            exit(self.quit())

        # Send the text
        try:
            self.sock.sendall(data)
        except OSError as e:
            critical_error(self.window, e)
            exit(self.quit())

        # Decrypt the text
        decrypted = aes_cipher.decrypt(data)
        msg = decrypted.decode('utf-8', 'ignore')

        # Update UI
        self.chat_view.append(msg)
        self.chat_text_field.setText('')

    def help(self):
        """Print a list of available commands."""
        self.chat_view.append('Available Commands:\n')
        self.chat_view.append('\t{help}:\tThis help menu')
        self.chat_view.append('\t{quit}:\tExit program')
        self.chat_view.append('\t{who}\tList of user names in the lair.')


class ClientThread(QtCore.QThread):
    """Create a client thread for networking communications."""

    def __init__(self, parent):
        """Initialize the thread."""
        QtCore.QThread.__init__(self, parent)
        self.parent = parent

    def __del__(self):
        """Thread cleanup."""
        self.wait()

    def quit(self):
        """Exit the program."""
        exit(self.parent.quit())

    def recveive(self):
        """Read data from server."""
        BUFSIZ = 4096
        global ANNOUNCE_EXIT

        try:
            data = self.parent.sock.recv(BUFSIZ)
        except OSError as e:
            critical_error(self.parent, f'recv: {e}')
            exit(self.quit())

        # Make sure the other thread hasn't called quit yet
        # If it has, stop executing this frame
        if ANNOUNCE_EXIT:
            exit(0)

        # Decrypt and decode the data
        decrypted = aes_cipher.decrypt(data)
        if decrypted is None:
            critical_error(self.parent, 'unable to decrypt message')
            exit(self.quit())

        msg = decrypted.decode('utf-8', 'ignore')

        # Add received text to chat field
        self.parent.chat_view.append(format_text(color='blue', text=msg))

        # The server closed, do NOT set ANNOUNCE_EXIT
        if msg == 'The lair is closed.':
            exit(self.quit())

    def run(self):
        """Run the client thread."""
        try:
            self.parent.sock.connect(self.parent.conn[0])
        except OSError as e:
            critical_error(self.parent, e)
            return self.quit()

        # Receive loop
        while not ANNOUNCE_EXIT:
            self.recveive()


def main():
    """Main function."""
    app = QtWidgets.QApplication(sys.argv)
    main_win = ChatWindow()
    main_win.show()
    app.exec_()


# __main__? Program entry point
if __name__ == '__main__':
    sys.exit(main())
