"""Key settings window.  Shelf button: "NS: Customize keys..."

Edit the key of every action, add your own node actions (label + SOP node +
VOP node picked from lists), see conflicts with other Network Editor keys, then
Enable / Apply. Disable restores the keymap you had before the first Enable.
Apply writes <prefs>/network_shortcuts/user.json, updates the keymap overrides
file and asks you to restart Houdini.
"""

import json
import os
import re

import hou

from . import autoshelf, config, installer

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:                      # older Houdini
    from PySide2 import QtCore, QtGui, QtWidgets

_window = None


def _user_json_path():
    return os.path.join(config.user_dir(), "user.json")


def _read_user():
    try:
        with open(_user_json_path(), "r", encoding="utf-8-sig") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _default_keys():
    with open(os.path.join(config.root_dir(), "config", "keys.json"), "r", encoding="utf-8-sig") as fh:
        return json.load(fh)["keys"]


def _node_text(spec, kind):
    if "python" in spec:
        return "(Python script)" if kind == "sop" else ""
    node = spec.get(kind)
    if not node:
        return ""
    types = node["type"]
    text = types if isinstance(types, str) else types[0]
    if node.get("parms"):
        text += " (%s)" % ", ".join("%s=%s" % kv for kv in node["parms"].items())
    return text


def node_choices(category):
    """[(display text, type name)] of visible node types, one per description, sorted."""
    best = {}
    for name, nt in category.nodeTypes().items():
        if nt.hidden() or nt.deprecated():
            continue
        desc = nt.description() or name
        if desc not in best or name > best[desc]:      # newest version sorts last
            best[desc] = name
    return sorted(("%s  [%s]" % (d, n), n) for d, n in best.items())


class NodeCombo(QtWidgets.QComboBox):
    """Searchable list of node types. type_name() is None when nothing is chosen."""

    def __init__(self, category, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        self.addItem("(none)", "")
        for text, name in node_choices(category):
            self.addItem(text, name)
        completer = self.completer()
        completer.setFilterMode(QtCore.Qt.MatchContains)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.setCurrentIndex(0)

    def type_name(self):
        """Selected type name; "" for none; None if the typed text is not in the list."""
        idx = self.findText(self.currentText(), QtCore.Qt.MatchFixedString)
        if idx < 0:
            return None
        return self.itemData(idx)


class AddCustomDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add custom node")
        self.resize(520, 340)
        self.action_kind = QtWidgets.QComboBox()
        self.action_kind.addItems(["Create node", "Run Python script"])
        self.label = QtWidgets.QLineEdit()
        self.sop = NodeCombo(hou.sopNodeTypeCategory())
        self.vop = NodeCombo(hou.vopNodeTypeCategory())
        form = QtWidgets.QFormLayout(self)
        form.addRow("Action:", self.action_kind)
        form.addRow("Label:", self.label)
        pages = QtWidgets.QStackedWidget()
        node_page = QtWidgets.QWidget()
        node_form = QtWidgets.QFormLayout(node_page)
        node_form.setContentsMargins(0, 0, 0, 0)
        node_form.addRow("SOP node:", self.sop)
        node_form.addRow("VOP node:", self.vop)
        node_form.addRow(QtWidgets.QLabel(
            "Pick a node from each list (type to search). Leave a list on (none) "
            "if the key should do nothing in that network."))
        pages.addWidget(node_page)
        script_page = QtWidgets.QWidget()
        script_form = QtWidgets.QFormLayout(script_page)
        script_form.setContentsMargins(0, 0, 0, 0)
        self.script = QtWidgets.QPlainTextEdit()
        self.script.setFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont))
        script_form.addRow("Python:", self.script)
        hint = QtWidgets.QLabel(
            "Variables: hou, editor, parent, kind, cursor (network values may be None).\n"
            "Example: hou.ui.displayMessage('hi')")
        hint.setWordWrap(True)
        script_form.addRow(hint)
        pages.addWidget(script_page)
        self.action_kind.currentIndexChanged.connect(pages.setCurrentIndex)
        form.addRow(pages)
        box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        box.accepted.connect(self._ok)
        box.rejected.connect(self.reject)
        form.addRow(box)

    def _ok(self):
        label = self.label.text().strip()
        if self.action_kind.currentIndex() == 1:
            code = self.script.toPlainText()
            if not label or not code.strip():
                QtWidgets.QMessageBox.warning(self, "Incomplete", "Enter a label and a Python script.")
                return
            try:
                compile(code, "<Network Shortcut>", "exec")
            except SyntaxError as exc:
                QtWidgets.QMessageBox.warning(self, "Invalid Python script", str(exc))
                return
            self.result_spec = {"label": label, "python": code}
            self.accept()
            return
        sop, vop = self.sop.type_name(), self.vop.type_name()
        if sop is None or vop is None:
            QtWidgets.QMessageBox.warning(self, "Pick from the list",
                                          "Choose a node from the list (or (none)).")
            return
        if not label or not (sop or vop):
            QtWidgets.QMessageBox.warning(self, "Incomplete",
                                          "Enter a label and choose at least one node.")
            return
        self.result_spec = {"label": label}
        if sop:
            self.result_spec["sop"] = {"type": sop}
        if vop:
            self.result_spec["vop"] = {"type": vop}
        self.accept()


class KeyEdit(QtWidgets.QKeySequenceEdit):
    """Single-key capture with a clear button."""

    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            self.setMaximumSequenceLength(1)
        except AttributeError:
            pass
        try:
            self.setClearButtonEnabled(True)
        except AttributeError:
            pass

    def key_string(self):
        text = self.keySequence().toString(QtGui.QKeySequence.PortableText)
        return text.split(",")[0].strip() or None


class KeyWindow(QtWidgets.QDialog):
    COLS = ("Action", "SOP node", "VOP node", "Key", "Conflict", "")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Network Shortcuts - Customize keys")
        self.resize(900, 640)
        self._user = _read_user()
        self._cfg = config.load()
        self._edits = {}
        self._pending_restart = False

        top = QtWidgets.QHBoxLayout()
        reset = QtWidgets.QPushButton("Reset keys to defaults")
        reset.clicked.connect(self.reset_keys)
        top.addWidget(reset)
        self.auto_shelf = QtWidgets.QCheckBox("Show Network Shortcuts shelf tab automatically")
        self.auto_shelf.setChecked(self._cfg["auto_shelf"])
        top.addWidget(self.auto_shelf)
        top.addStretch(1)
        add = QtWidgets.QPushButton("Add custom node...")
        add.clicked.connect(self.add_custom)
        top.addWidget(add)

        self.table = QtWidgets.QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        hdr.setSectionResizeMode(4, QtWidgets.QHeaderView.Stretch)
        for col in (1, 2, 3, 5):
            hdr.setSectionResizeMode(col, QtWidgets.QHeaderView.ResizeToContents)

        self.note = QtWidgets.QLabel(
            "Tip: click a Key box and press the key; use the clear button inside the box to "
            "remove a key. Keys that Houdini already uses in the Network Editor will be overwritten.")
        self.note.setWordWrap(True)

        self.status = QtWidgets.QLabel()
        apply_btn = QtWidgets.QPushButton("Enable / Apply keys")
        apply_btn.clicked.connect(self.apply)
        disable_btn = QtWidgets.QPushButton("Disable (restore original keys)")
        disable_btn.clicked.connect(self.disable)
        close_btn = QtWidgets.QPushButton("Close")
        close_btn.clicked.connect(self.close)
        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(self.status, 1)
        buttons.addWidget(disable_btn)
        buttons.addWidget(apply_btn)
        buttons.addWidget(close_btn)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.table)
        layout.addWidget(self.note)
        layout.addLayout(buttons)
        self.populate(self._cfg["keys"])
        self.refresh_status()

    # -- table ------------------------------------------------------------
    def populate(self, keys):
        actions = self._cfg["actions"]
        self.table.setRowCount(0)
        self._edits = {}
        for action, spec in actions.items():
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(spec.get("label", action)))
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(_node_text(spec, "sop")))
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(_node_text(spec, "vop")))
            edit = KeyEdit()
            if keys.get(action):
                edit.setKeySequence(QtGui.QKeySequence(keys[action]))
            edit.keySequenceChanged.connect(self.refresh_conflicts)
            self.table.setCellWidget(row, 3, edit)
            self.table.setItem(row, 4, QtWidgets.QTableWidgetItem(""))
            if action in self._user.get("actions", {}):          # only your own actions can be deleted
                btn = QtWidgets.QPushButton("Delete")
                btn.clicked.connect(lambda _checked=False, a=action: self.delete_custom(a))
                self.table.setCellWidget(row, 5, btn)
            self._edits[action] = (row, edit)
        self.refresh_conflicts()

    def keys(self):
        return {a: e.key_string() for a, (_r, e) in self._edits.items()}

    def conflicts(self):
        """action -> (text, is_blocking). Blocking = same key used twice here."""
        out = {}
        used = {}
        for action, key in self.keys().items():
            if key:
                used.setdefault(config.normalize_key(key), []).append(action)
        for action, key in self.keys().items():
            if not key:
                continue
            dup = [a for a in used[config.normalize_key(key)] if a != action]
            if dup:
                out[action] = ("Also used by: " + ", ".join(self._cfg["actions"][a].get("label", a)
                                                           for a in dup), True)
                continue
            try:
                own, _foreign = installer._classify(installer._symbol(action), key)
            except Exception:
                own = []
            names = []
            for _ctx, sym in own:
                if ".tool:qns_" in sym:
                    continue                      # our own earlier binding
                label = hou.hotkeys.hotkeyLabel(sym) or sym.rsplit(".", 1)[-1]
                names.append(label)
            if names:
                out[action] = ("Overwrites: " + ", ".join(names), False)
        return out

    def refresh_conflicts(self, *_):
        conflicts = self.conflicts()
        for action, (row, _edit) in self._edits.items():
            text, blocking = conflicts.get(action, ("", False))
            item = self.table.item(row, 4)
            item.setText(text)
            item.setForeground(QtGui.QBrush(QtGui.QColor("#e05050" if blocking else "#d0a040")))

    # -- actions ----------------------------------------------------------
    def reset_keys(self):
        self.populate(_default_keys())

    def add_custom(self):
        dlg = AddCustomDialog(self)
        if dlg.exec() != QtWidgets.QDialog.Accepted:
            return
        spec = dlg.result_spec
        action = "custom_" + re.sub(r"[^a-z0-9]+", "_", spec["label"].lower()).strip("_")
        if action in self._cfg["actions"]:
            QtWidgets.QMessageBox.warning(self, "Exists", "An action named %r already exists." % action)
            return
        self._cfg["actions"][action] = spec
        self._user.setdefault("actions", {})[action] = spec
        self.populate(dict(self.keys()))

    def delete_custom(self, action):
        label = self._cfg["actions"].get(action, {}).get("label", action)
        ans = QtWidgets.QMessageBox.question(
            self, "Delete custom node",
            "Delete \"%s\" and its key?\n\nIt is removed for good when you press Enable / Apply keys."
            % label)
        if ans != QtWidgets.QMessageBox.Yes:
            return
        keys = self.keys()
        keys.pop(action, None)
        self._cfg["actions"].pop(action, None)
        self._user.get("actions", {}).pop(action, None)
        if not self._user.get("actions"):
            self._user.pop("actions", None)
        self.populate(keys)

    def apply(self):
        keys = self.keys()
        conflicts = self.conflicts()
        if any(blocking for _t, blocking in conflicts.values()):
            QtWidgets.QMessageBox.warning(self, "Duplicate keys",
                                          "Two actions use the same key. Fix the red rows first.")
            return
        if conflicts:
            ans = QtWidgets.QMessageBox.question(
                self, "Overwrite existing keys?",
                "%d key(s) are already used by Houdini in the Network Editor and will be "
                "overwritten (restorable with Disable).\n\nContinue?" % len(conflicts))
            if ans != QtWidgets.QMessageBox.Yes:
                return
        self._user.pop("preset", None)           # presets no longer exist
        self._user["keys"] = keys
        self._user["auto_shelf"] = self.auto_shelf.isChecked()
        os.makedirs(config.user_dir(), exist_ok=True)
        with open(_user_json_path(), "w", encoding="utf-8") as fh:
            json.dump(self._user, fh, indent=2, ensure_ascii=False)
        self._write_custom_shelf()
        installer.install(config.load())
        autoshelf.ensure()
        self._pending_restart = True
        self.refresh_status()
        QtWidgets.QMessageBox.information(self, "Enabled", "Keys written. Restart Houdini to activate them.")

    def disable(self):
        if not os.path.isfile(installer._marker_path()):
            QtWidgets.QMessageBox.information(self, "Not enabled", "Network Shortcuts keys are not enabled.")
            return
        ans = QtWidgets.QMessageBox.question(
            self, "Disable Network Shortcuts keys?",
            "This restores the keymap you had before the first Enable (your original keys "
            "return). Your settings in this window are kept.\n\nContinue?")
        if ans != QtWidgets.QMessageBox.Yes:
            return
        try:
            installer.uninstall()
        except RuntimeError as exc:
            QtWidgets.QMessageBox.warning(self, "Cannot restore", str(exc))
            return
        self._pending_restart = True
        self.refresh_status()
        QtWidgets.QMessageBox.information(self, "Disabled", "Original keys restored. Restart Houdini.")

    def refresh_status(self):
        enabled = os.path.isfile(installer._marker_path())
        text = "Status: ENABLED" if enabled else "Status: DISABLED"
        if self._pending_restart:
            text += "  (restart Houdini to apply the change)"
        self.status.setText(text)

    def _write_custom_shelf(self):
        custom = self._user.get("actions", {})
        path = os.path.join(hou.homeHoudiniDirectory(), "toolbar", "network_shortcuts_custom.shelf")
        if not custom:
            if os.path.isfile(path):
                os.remove(path)
            return
        from . import shelf
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(shelf.build_user(custom))


def show():
    global _window
    _window = KeyWindow(hou.qt.mainWindow())
    _window.show()
    return _window
