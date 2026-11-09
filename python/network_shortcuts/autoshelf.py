"""Keep the "Network Shortcuts" shelf tab in the shelf dock.

A hip file can restore a desktop whose shelf sets do not contain our tab, so
besides startup this also runs after every file load / new file.
Switch it off with  "auto_shelf": false  in user.json (Customize window checkbox).
"""

import hou

from . import config

SHELF_NAMES = ("network_shortcuts", "network_shortcuts_custom")
_hooked = False


def ensure():
    """Put our shelves last in the first shelf set of the current dock; Houdini then
    selects the last tab, so the Network Shortcuts tab opens."""
    try:
        if not config.load()["auto_shelf"]:
            return
        shelves = hou.shelves.shelves()
        ours = [shelves[n] for n in SHELF_NAMES if n in shelves]
        if not ours:
            return
        sets = hou.ui.curDesktop().shelfDock().shelfSets()
        if not sets:
            return
        target = sets[0]
        current = list(target.shelves())
        others = [s for s in current if s.name() not in SHELF_NAMES]
        wanted = others + ours                       # our tabs last
        if [s.name() for s in current] == [s.name() for s in wanted]:
            # already in place: take them out and put them back so Houdini
            # selects the last tab again (there is no API to select a tab)
            target.setShelves(tuple(others))
        target.setShelves(tuple(wanted))
    except Exception as exc:        # never break startup or file loading
        print("Network Shortcuts: could not show shelf tab: %s" % exc)


def _on_hip_event(event_type):
    if event_type in (hou.hipFileEventType.AfterLoad, hou.hipFileEventType.AfterClear):
        ensure()


def start():
    """Called from scripts/123.py at Houdini startup."""
    global _hooked
    if not hou.isUIAvailable() or _hooked:
        return
    _hooked = True
    hou.hipFile.addEventCallback(_on_hip_event)

    state = {"n": 0}

    def _once():                    # wait until the UI exists, then run once
        state["n"] += 1
        if state["n"] < 5:
            return
        hou.ui.removeEventLoopCallback(_once)
        ensure()
        # the welcome dialog is modal and blocks redraws, so show it a little later,
        # after Houdini has drawn the new shelf tab
        later = {"n": 0}

        def _welcome():
            later["n"] += 1
            if later["n"] < 20:
                return
            hou.ui.removeEventLoopCallback(_welcome)
            from . import welcome
            welcome.maybe_show()

        hou.ui.addEventLoopCallback(_welcome)

    hou.ui.addEventLoopCallback(_once)
