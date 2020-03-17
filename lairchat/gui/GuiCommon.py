"""GuiCommon.py

Common variables and functions for the gui classes.
"""

from PyQt5 import QtWidgets


def format_text(color="black", text=""):
    """Perform some basic formatting on text."""
    return f'<font color="{color}">{text}</font>'.replace("\n", "<br>")


def critical_error(parent=None, err=None):
    """Display an error message."""
    QtWidgets.QMessageBox.critical(parent, "Error", str(err), QtWidgets.QMessageBox.Ok)
