#!/usr/bin/env python3

import os
import sys
import socket
import psutil
from threading import Thread
from PyQt5 import QtCore, QtWidgets

addr = '127.0.0.1'
port = 1234
tcp_client = None
exit_flag = False


def kill_proc_tree(pid):
    """Kill the entrire process tree."""
    parent = psutil.Process(pid)
    parent.kill()


class ConnectionDialog(QtWidgets.QDialog):
    """Get Server Options."""
    def __init__(self):
        """Create a simple dialog.

        Populate addr and port of server with user input.
        """
        super().__init__()
        self.addressLabel = QtWidgets.QLabel('Server Address', self)
        self.addressField = QtWidgets.QLineEdit(self)
        self.portLabel = QtWidgets.QLabel('Server Port', self)
        self.portField = QtWidgets.QLineEdit(self)
        self.btnConnect = QtWidgets.QPushButton('Connect', self)
        self.btnConnect.clicked.connect(self.set_fields)
        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.addWidget(self.addressLabel)
        self.vbox.addWidget(self.addressField)
        self.vbox.addWidget(self.portLabel)
        self.vbox.addWidget(self.portField)
        self.vbox.addWidget(self.btnConnect)
        self.setLayout(self.vbox)
        self.setWindowTitle('Connect to Lair Server')
        self.resize(250, 250)

    def set_fields(self):
        """Get user input from the text fields then exit dialog."""
        global addr
        global port
        addr = self.addressField.text()
        port = int(self.portField.text())
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
        tcp_client.close()
        self.close()
        kill_proc_tree(os.getpid())

    def send(self):
        """Send text to the lair server."""
        text = self.chatTextField.text()
        font = self.chat.font()
        self.chat.setFont(font)

        if text == '{help}':
            self.chatTextField.setText('')
            return self.help()
        elif text == '{quit}':
            self.chatTextField.setText('')
            tcp_client.send(bytes('{quit}', 'utf8'))
            self.quit()

        # Check if client thread set the exit_flag
        if exit_flag:
            self.quit()
        else:
            try:
                tcp_client.send(bytes(text, 'utf8'))
                self.chat.append(text)
                self.chatTextField.setText('')
            except socket.error as err:
                QtWidgets.QMessageBox.critical(self.window,
                                               'Error',
                                               str(err),
                                               QtWidgets.QMessageBox.Ok)
                self.quit()
                tcp_client.close()
                kill_proc_tree(os.getpid())

    def help(self):
        """Print a list of available commands."""
        self.chat.append('Available Commands:\n')
        self.chat.append('\t{help}:\t This help menu')
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
        tcp_client.close()
        self.window.close()
        kill_proc_tree(os.getpid())

    def run(self):
        """Run the client thread."""
        BUFSIZ = 4096

        global addr
        global port
        global tcp_client
        try:
            tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_client.connect((addr, port))
        except socket.error as err:
            QtWidgets.QMessageBox.critical(self.window,
                                           'Error',
                                           str(err),
                                           QtWidgets.QMessageBox.Ok)
            self.quit()

        global exit_flag
        while not exit_flag:
            try:
                data = tcp_client.recv(BUFSIZ).decode('utf8')
                if data == 'The lair is closed.':
                    exit_flag = False
                self.window.chat.append(data)
            except socket.error as err:
                exit_flag = True
                QtWidgets.QMessageBox.critical(self.window,
                                               'Error',
                                               str(err),
                                               QtWidgets.QMessageBox.Ok)

        self.quit()


# __main__? Program entry point
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    opt_win = ConnectionDialog()
    opt_win.exec_()
    main_win = ChatWindow()
    ct = ClientThread(main_win)
    ct.start()
    main_win.exec_()
    sys.exit(app.exec_())
