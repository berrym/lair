"""ChatWindow.py

Main gui window for gui chat app.
"""

from socket import *

from PyQt5 import QtCore, QtGui

from modules.crypto.AESCipher import aes_cipher
from modules.gui.ClientThread import ClientThread
from modules.gui.ConnectionDialog import ConnectionDialog
from modules.gui.utility import *


class ChatWindow(QtWidgets.QMainWindow):
    """Graphical chat window."""

    def __init__(self):
        """Initialize the chat window."""
        super().__init__()
        self.chat_view = QtWidgets.QTextEdit()
        self.chat_text_field = QtWidgets.QLineEdit(self)
        self.window_frame = QtWidgets.QVBoxLayout(self)
        self.initUI()
        self.sock = socket(AF_INET, SOCK_STREAM)
        self.conn = []

    def initUI(self):
        """Create all gui components."""
        exit_act = QtWidgets.QAction(QtGui.QIcon(), 'Exit', self)
        exit_act.setShortcut('Ctrl+Q')
        exit_act.setStatusTip('Exit application')
        exit_act.triggered.connect(self.close)

        conn_act = QtWidgets.QAction(QtGui.QIcon(), 'Connect', self)
        conn_act.setShortcut('F2')
        conn_act.setStatusTip('Connect To a Lair')
        conn_act.triggered.connect(self.connect)

        about_act = QtWidgets.QAction(QtGui.QIcon(), 'About The Lair', self)
        about_act.triggered.connect(self.aboutTheLair)

        about_Qt_act = QtWidgets.QAction(QtGui.QIcon(), 'About Qt', self)
        about_Qt_act.triggered.connect(self.aboutQt)

        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu('&File')
        file_menu.addAction(conn_act)
        file_menu.addAction(exit_act)
        self.window_frame.addWidget(menu_bar)

        help_menu = menu_bar.addMenu('&Help')
        help_menu.addAction(about_act)
        help_menu.addAction(about_Qt_act)

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

        self.statusBar()

    def closeEvent(self, event):
        """Quit app when the window is closed."""
        self.quit()
        event.accept()

    def quit(self):
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

    def aboutTheLair(self):
        """Display an about message box with Program/Author information."""
        text = """<b><u>The Lair v0.0.1</u></b>
        <br><br>Simple chat application written in Python 3
        <br><br>License: <a href="http://www.fsf.org/licenses/gpl.html">\
        GPLv3</a>
        <br><br><b>Copyright (C) Michael Berry 2019</b>
        """
        QtWidgets.QMessageBox.about(self, 'About The Lair', text)

    def aboutQt(self):
        """Display information about Qt."""
        QtWidgets.QMessageBox.aboutQt(self, 'About Qt')