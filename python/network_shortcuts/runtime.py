"""Create the node for an action at the Network Editor cursor.

SOP / VOP are detected from the network being viewed, so the same key makes
different nodes (e.g. M: Merge in SOP, Multiply in VOP). Other networks are
left untouched by node actions. Python script actions work in any network.
No auto-wiring.
"""

import hou

from . import config


class ShortcutError(RuntimeError):
    pass


def find_network_editor():
    pane = hou.ui.paneTabUnderCursor()
    if not isinstance(pane, hou.NetworkEditor):
        # e.g. the shelf button was clicked, so the cursor was over the shelf
        pane = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
    if not isinstance(pane, hou.NetworkEditor):
        raise ShortcutError("No Network Editor found")
    return pane


def network_kind(parent):
    category = parent.childTypeCategory()
    if category == hou.sopNodeTypeCategory():
        return "sop"
    if category == hou.vopNodeTypeCategory():
        return "vop"
    return None


def _resolve_type(parent, candidates):
    if isinstance(candidates, str):
        candidates = [candidates]
    category = parent.childTypeCategory()
    for name in candidates:
        if hou.nodeType(category, name) is not None:
            return name
    raise ShortcutError("Node type not available: %s" % ", ".join(candidates))


def _apply_parms(node, parms):
    for name, value in parms.items():
        parm = node.parm(name)
        if parm is None:
            raise ShortcutError("%s has no parm %r" % (node.type().name(), name))
        items = parm.menuItems() if parm.menuItems() else None
        if items is not None and value not in items:
            raise ShortcutError("%r is not a valid value of %s (choices: %s)"
                                % (value, name, ", ".join(items)))
        parm.set(value)


def create(action, cfg=None, editor=None):
    """Create the node for `action`. Returns the node, or None if the current
    network type has no node for this action. Raises ShortcutError on failure."""
    cfg = cfg or config.load()
    spec = cfg["actions"].get(action)
    if spec is None:
        raise ShortcutError("Unknown action %r" % action)

    editor = editor or find_network_editor()
    parent = editor.pwd()
    if parent is None:
        raise ShortcutError("Network Editor has no current network")
    kind = network_kind(parent)
    node_spec = spec.get(kind) if kind else None
    if node_spec is None:
        return None

    type_name = _resolve_type(parent, node_spec["type"])
    with hou.undos.group("Network Shortcut: %s" % spec.get("label", action)):
        try:
            node = parent.createNode(type_name)
            node.setPosition(editor.cursorPosition() - node.size() * 0.5)
            _apply_parms(node, node_spec.get("parms", {}))
        except hou.OperationFailed as exc:
            raise ShortcutError("Could not create %s: %s" % (type_name, exc))
        node.setSelected(True, clear_all_selected=True)
    return node


def run(action):
    """Entry point used by the shelf tools. Never raises into the UI."""
    try:
        cfg = config.load()
        spec = cfg["actions"].get(action)
        if spec is not None and "python" in spec:
            # Python wins when a spec also defines SOP/VOP nodes.
            try:
                editor = find_network_editor()
            except ShortcutError:
                editor = None
            parent = editor.pwd() if editor is not None else None
            namespace = {"hou": hou, "editor": editor, "parent": parent,
                         "kind": network_kind(parent) if parent is not None else None,
                         "cursor": editor.cursorPosition() if editor is not None else None}
            try:
                with hou.undos.group("Network Shortcut: %s" % spec.get("label", action)):
                    exec(spec["python"], namespace)
            except BaseException as exc:  # user code (even SystemExit) must not escape into the UI
                hou.ui.setStatusMessage("Network Shortcuts: %s" % exc, severity=hou.severityType.Error)
            return None
        node = create(action, cfg=cfg)
        if node is None:
            hou.ui.setStatusMessage("Network Shortcuts: '%s' has no node in this network" % action)
        return node
    except Exception as exc:  # shown in the status bar, not as a modal dialog
        hou.ui.setStatusMessage("Network Shortcuts: %s" % exc, severity=hou.severityType.Error)
        return None
