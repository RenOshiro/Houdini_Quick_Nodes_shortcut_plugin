"""First-run welcome: after installing, the first Houdini start offers a one-click "Turn on keys".

Shown once (a marker file is written before anything else happens), and never when the
keys are already enabled.
"""

import os

import hou

from . import config, installer

try:
    from PySide6 import QtCore, QtWidgets
except ImportError:                      # older Houdini
    from PySide2 import QtCore, QtWidgets

MESSAGE = (
    "Network Shortcuts is installed.\n\n"
    "With the keys on, one key press creates a node at the mouse cursor in the Network Editor:\n"
    "    M = Merge (SOP) / Multiply (VOP)\n"
    "    W = Attribute Wrangle      1-4 = Constants      and more\n\n"
    "Turning the keys on replaces Houdini's own single-key shortcuts in the Network Editor\n"
    "(for example P, G, F, S, A). You can undo this at any time with 'Disable' in the key settings.\n\n"
    "You can also do this later: Network Shortcuts shelf tab > NS: Customize keys..."
)


def _marker():
    return os.path.join(config.user_dir(), "welcome_done")


def should_show():
    return not os.path.isfile(installer._marker_path()) and not os.path.isfile(_marker())


def _make_box(main):
    box = QtWidgets.QMessageBox(main)
    box.setWindowTitle("Network Shortcuts")
    box.setIcon(QtWidgets.QMessageBox.Information)
    box.setText(MESSAGE)
    on = box.addButton("Turn on keys now", QtWidgets.QMessageBox.AcceptRole)
    opn = box.addButton("Open key settings", QtWidgets.QMessageBox.ActionRole)
    later = box.addButton("Later", QtWidgets.QMessageBox.RejectRole)
    box.setDefaultButton(on)
    box.setEscapeButton(later)
    return box, on, opn, later


def _ask():
    """Show the dialog centered on the Houdini window. Returns 'on', 'open' or 'later'."""
    main = hou.qt.mainWindow()
    box, on, opn, later = _make_box(main)

    def center():
        box.adjustSize()
        box.move(main.geometry().center() - QtCore.QPoint(box.width() // 2, box.height() // 2))

    QtCore.QTimer.singleShot(0, center)
    box.exec()
    clicked = box.clickedButton()
    return "on" if clicked is on else "open" if clicked is opn else "later"


def maybe_show():
    try:
        if not should_show():
            return
        os.makedirs(config.user_dir(), exist_ok=True)
        with open(_marker(), "w") as fh:               # first, so a crash can never make it loop
            fh.write("shown")
        choice = _ask()
        if choice == "on":
            installer.install(config.load())
            hou.ui.displayMessage("Keys are set.\n\nRestart Houdini once to start using them.",
                                  title="Network Shortcuts")
        elif choice == "open":
            from . import ui
            ui.show()
    except Exception as exc:
        print("Network Shortcuts: welcome dialog failed: %s" % exc)
