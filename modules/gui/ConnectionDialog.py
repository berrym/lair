"""ConnectionDialog.py

Simple dialog to get the server's host address and port number.
"""

from PyQt5 import QtWidgets


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