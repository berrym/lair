"""ChatWindow.py

Main gui window for gui chat app.
"""

from socket import *

from PyQt5 import QtCore, QtGui

from lairchat.crypto.AESCipher import aes_cipher
from lairchat.gui.ClientThread import ClientThread
from lairchat.gui.ConnectionDialog import ConnectionDialog
from lairchat.gui.GuiCommon import *


class ChatWindow(QtWidgets.QMainWindow):
    """Graphical chat window."""

    def __init__(self):
        """Initialize the chat window."""
        super().__init__()
        self.ct = ClientThread(self)
        self.chat_view = QtWidgets.QTextEdit()
        self.chat_text_field = QtWidgets.QLineEdit(self)
        self.initUI()
        self.sock = socket(AF_INET, SOCK_STREAM)
        self.conn = []

    def initUI(self):
        """Create all gui components."""
        exit_act = QtWidgets.QAction(QtGui.QIcon(), "Exit", self)
        exit_act.setShortcut("Ctrl+Q")
        exit_act.setStatusTip("Exit application")
        exit_act.triggered.connect(self.close)

        conn_act = QtWidgets.QAction(QtGui.QIcon(), "Connect", self)
        conn_act.setShortcut("F2")
        conn_act.setStatusTip("Connect To a Lair")
        conn_act.triggered.connect(self.connect)

        about_act = QtWidgets.QAction(QtGui.QIcon(), "About The Lair", self)
        about_act.triggered.connect(self.aboutTheLair)

        about_qt_act = QtWidgets.QAction(QtGui.QIcon(), "About Qt", self)
        about_qt_act.triggered.connect(self.aboutQt)

        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction(conn_act)
        file_menu.addAction(exit_act)

        help_menu = menu_bar.addMenu("&Help")
        help_menu.addAction(about_act)
        help_menu.addAction(about_qt_act)

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

        self.setCentralWidget(splitter2)

        self.setWindowTitle("The Lair")
        self.resize(500, 500)
        self.chat_text_field.setFocus()

        self.statusBar()

    def closeEvent(self, event):
        """Quit app when the window is closed."""
        exit(0)

    def connect(self):
        """Create a client connection in a new thread."""
        conn_win = ConnectionDialog(self.conn)
        conn_win.exec_()
        self.ct.communicator.close_app.connect(self.close)
        self.ct.start()

    def send(self):
        """Send text to the lair server."""
        global announce_exit
        text = self.chat_text_field.text()

        if text == "{help}":
            self.chat_text_field.setText("")
            return self.help()
        elif text == "{quit}":
            self.ct.communicator.close_app.emit()

        # Encrypt the text
        if (data := aes_cipher.encrypt(text)) is None:
            critical_error(self, "unable to encrypt data.")
            exit(0)

        # Send the text
        try:
            self.sock.sendall(data)
        except OSError as e:
            critical_error(self.window, e)
            exit(0)

        # Decrypt the text
        decrypted = aes_cipher.decrypt(data)
        msg = decrypted.decode("utf-8", "ignore")

        # Update UI
        self.chat_view.append(msg)
        self.chat_text_field.setText("")

    def help(self):
        """Print a list of available commands."""
        self.chat_view.append("Available Commands:\n")
        self.chat_view.append("\t{help}:\tThis help menu")
        self.chat_view.append("\t{quit}:\tExit program")
        self.chat_view.append("\t{who}\tList of user names in the lair.")

    def aboutTheLair(self):
        """Display an about message box with Program/Author information."""
        text = """<b><u>The Lair v0.0.1</u></b>
        <br><br>Simple chat application written in Python 3
        <br><br>License: <a href="http://www.fsf.org/licenses/gpl.html">\
        GPLv3</a>
        <br><br><b>Copyright (C) Michael Berry 2019</b>
        """
        QtWidgets.QMessageBox.about(self, "About The Lair", text)

    def aboutQt(self):
        """Display information about Qt."""
        QtWidgets.QMessageBox.aboutQt(self, "About Qt")
