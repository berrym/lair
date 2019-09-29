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

from PyQt5 import QtWidgets

from lairchat.gui.ChatWindow import ChatWindow


def main():
    """Main function."""
    app = QtWidgets.QApplication(sys.argv)
    main_win = ChatWindow()
    main_win.show()
    app.exec_()


# __main__? Program entry point
if __name__ == '__main__':
    sys.exit(main())
