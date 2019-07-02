#!/usr/bin/env python3

import os
import sys
import socket
import psutil
from threading import Thread
from PyQt5 import QtCore, QtWidgets

ADDR = '127.0.0.1'
PORT = 1234
TCP_CLIENT = None
EXIT_FLAG = False


def kill_proc_tree(pid):
    """Kill the entrire process tree."""
    parent = psutil.Process(pid)
    parent.kill()

def formatText(color='black', text=''):
    return ('<font color="{}">{}</font>'.format(color, text))

class ConnectionDialog(QtWidgets.QDialog):
    """Get Server Options."""
    def __init__(self):
        """Create a simple dialog.

        Populate ADDR and port of server with user input.
        """
        super().__init__()
        self.addressLabel = QtWidgets.QLabel('Server Address', self)
        self.addressField = QtWidgets.QLineEdit(self)
        self.addressField.setText(ADDR)
        self.portLabel = QtWidgets.QLabel('Server Port', self)
        self.portField = QtWidgets.QLineEdit(self)
        self.portField.setText(str(PORT))
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
        # self.resize(250, 250)

    def set_fields(self):
        """Get user input from the text fields then exit dialog."""
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
        global TCP_CLIENT
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
                TCP_CLIENT.send(bytes('{quit}', 'utf8'))
            except socket.error as err:
                QtWidgets.QMessageBox.critical(self.window,
                                               'Error',
                                               str(err),
                                               QtWidgets.QMessageBox.Ok)
            EXIT_FLAG = True

        # Check if EXIT_FLAG is set
        if EXIT_FLAG:
            self.quit()
        else:
            try:
                TCP_CLIENT.send(bytes(text, 'utf8'))
                self.chat.append(text)
                self.chatTextField.setText('')
            except socket.error as err:
                QtWidgets.QMessageBox.critical(self.window,
                                               'Error',
                                               str(err),
                                               QtWidgets.QMessageBox.Ok)
                self.quit()

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
        global TCP_CLIENT
        TCP_CLIENT.close()
        self.window.close()
        kill_proc_tree(os.getpid())

    def recv_loop(self):
        """Read data from server."""
        BUFSIZ = 4096
        global TCP_CLIENT
        global EXIT_FLAG

        while not EXIT_FLAG:
            try:
                data = TCP_CLIENT.recv(BUFSIZ).decode('utf8')
            except socket.error as err:
                QtWidgets.QMessageBox.critical(self.window,
                                               'Error',
                                               str(err),
                                               QtWidgets.QMessageBox.Ok)
                EXIT_FLAG = True

            # The server closed, set EXIT_FLAG
            if data == 'The lair is closed.':
                EXIT_FLAG = True

            # add recieved text to chat field
            self.window.chat.append(data)

        self.quit()

    def run(self):
        """Run the client thread."""
        global ADDR
        global PORT
        global TCP_CLIENT
        global EXIT_FLAG

        try:
            TCP_CLIENT = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error as err:
            QtWidgets.QMessageBox.critical(self.window,
                                           'Error',
                                           str(err),
                                           QtWidgets.QMessageBox.Ok)
            EXIT_FLAG = True
        try:
            TCP_CLIENT.connect((ADDR, PORT))
        except socket.error as err:
            QtWidgets.QMessageBox.critical(self.window,
                                           'Error',
                                           str(err),
                                           QtWidgets.QMessageBox.Ok)
            EXIT_FLAG = True

        # recieve loop
        self.recv_loop()


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
