"""Hotkey installer. Run INSIDE the Houdini GUI (needs hou.hotkeys).

    import network_shortcuts.installer as ins
    ins.plan()        # dry run: list keys and what they would overwrite
    ins.install()     # assign keys, then RESTART Houdini
    ins.uninstall()   # restore the exact keymap overrides file saved at install, then RESTART

Why the overrides file is edited directly: bindings that hou.hotkeys.addAssignment
adds for shelf-tool commands ("h.pane.wsheet.tool:<name>") live only in memory;
Houdini neither saves them nor dispatches them in the running session (observed in
22.0.466). Bindings read from Houdini.keymap2.overrides at startup do work, which
is how hand-made shelf-tool hotkeys are stored. So:
  1. the current overrides file is copied to a backup (never overwritten by a re-run),
  2. conflicting default/other bindings are removed through the API and saved,
  3. our tool bindings are appended to the saved file,
  4. after a restart Houdini loads them.
"""

import json
import os
import shutil

import hou

from . import config

CONTEXT = "h.pane.wsheet"          # Network Editor
OVERRIDES = "Houdini.keymap2.overrides"
BACKUP_NAME = "keymap_overrides_backup.json"
MARKER_NAME = "installed_keys.json"


def _symbol(action):
    return CONTEXT + ".tool:" + config.tool_name(action)


def _overrides_path():
    return os.path.join(hou.homeHoudiniDirectory(), OVERRIDES)


def _backup_path():
    return os.path.join(config.user_dir(), BACKUP_NAME)


def _marker_path():
    return os.path.join(config.user_dir(), MARKER_NAME)


def _classify(symbol, key):
    """Split findConflicts() into (overwritable, foreign) lists of (context, symbol)."""
    own, foreign = [], []
    for item in hou.hotkeys.findConflicts(CONTEXT, symbol, key):
        ctx, _, sym = item.partition("?")
        if sym == symbol:
            continue                      # ourselves
        (own if ctx == CONTEXT else foreign).append((ctx, sym))
    return own, foreign


def plan(cfg=None, verbose=True):
    """Return [(action, key, own_conflicts, foreign_conflicts)]; changes nothing."""
    cfg = cfg or config.load()
    rows = []
    for action, key in cfg["keys"].items():
        own, foreign = _classify(_symbol(action), key)
        rows.append((action, key, own, foreign))
        if verbose:
            note = "free"
            if own:
                note = "overwrites " + ", ".join(s for _, s in own)
            if foreign:
                note += " | also used in other contexts: " + ", ".join("%s?%s" % c for c in foreign)
            print("%-22s %-10s %s" % (action, key, note))
    return rows


def _strip_ours(path):
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    prefix = CONTEXT + ".tool:qns_"
    for ctx in data.get("contexts", []):
        if ctx["symbol"] == CONTEXT:
            ctx["bindings"] = [b for b in ctx["bindings"] if not b["action"].startswith(prefix)]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent="\t")


def _patch_file(path, bindings):
    """Replace/insert our tool bindings in the overrides JSON (Houdini must not rewrite it later)."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    ctx = next((c for c in data["contexts"] if c["symbol"] == CONTEXT), None)
    if ctx is None:
        ctx = {"symbol": CONTEXT, "bindings": []}
        data["contexts"].append(ctx)
    # drop every binding of ours first, so re-applying after a key change leaves no stale keys
    prefix = CONTEXT + ".tool:qns_"
    ctx["bindings"] = [b for b in ctx["bindings"] if not b["action"].startswith(prefix)]
    for sym, key in bindings.items():
        ctx["bindings"].append({"action": sym, "keys": [key]})
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent="\t")


def _restore_live_bindings(path):
    """Undo earlier conflict removals before planning a new layout, using the first
    backup rather than installed_keys.json so older installs are restored too."""
    if not os.path.isfile(path):
        return
    try:
        with open(path, "r", encoding="utf-8-sig") as fh:
            current = json.load(fh)
        with open(_backup_path(), "r", encoding="utf-8-sig") as fh:
            backup = json.load(fh)
        original = {b["action"]: b.get("keys", [])
                    for ctx in backup.get("contexts", []) if ctx.get("symbol") == CONTEXT
                    for b in ctx.get("bindings", [])}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("Network Shortcuts: could not read bindings to restore: %s" % exc)
        return
    prefix = CONTEXT + ".tool:qns_"
    for ctx in current.get("contexts", []):
        if ctx.get("symbol") != CONTEXT:
            continue
        for binding in ctx.get("bindings", []):
            sym = binding.get("action", "")
            if not sym or sym.startswith(prefix):
                continue
            try:
                if sym in original:
                    hou.hotkeys.clearAssignments(CONTEXT, sym)
                    for key in original[sym]:
                        hou.hotkeys.addAssignment(CONTEXT, sym, key)
                else:
                    hou.hotkeys.revertToDefaults(CONTEXT, sym, True)
            except Exception as exc:
                print("Network Shortcuts: could not restore %s: %s" % (sym, exc))


def install(cfg=None, overwrite=True):
    """Assign keys; restart Houdini afterwards. overwrite=False skips conflicting keys."""
    cfg = cfg or config.load()
    os.makedirs(config.user_dir(), exist_ok=True)
    path = _overrides_path()
    if not os.path.isfile(_backup_path()):          # keep the FIRST backup, never clobber it
        if os.path.isfile(path):
            shutil.copyfile(path, _backup_path())
            _strip_ours(_backup_path())      # never keep our own bindings in the "original"
        else:
            with open(_backup_path(), "w", encoding="utf-8") as fh:
                json.dump({"name": "Houdini", "version": 2, "contexts": []}, fh)

    _restore_live_bindings(path)
    bindings = {}
    for action, key, own, _foreign in plan(cfg, verbose=False):
        if own and not overwrite:
            print("skip %s (%s): in use by %s" % (action, key, ", ".join(s for _, s in own)))
            continue
        for ctx, sym in own:
            hou.hotkeys.removeAssignment(ctx, sym, key)
        bindings[_symbol(action)] = key
    hou.hotkeys.saveOverrides()
    _patch_file(path, bindings)
    with open(_marker_path(), "w", encoding="utf-8") as fh:
        json.dump({"keys": bindings}, fh, indent=2)
    print("Wrote %d bindings. RESTART Houdini to activate. Backup: %s" % (len(bindings), _backup_path()))


def uninstall():
    """Restore the keymap overrides saved before the first install. Restart Houdini afterwards."""
    if not os.path.isfile(_backup_path()):
        raise RuntimeError("No backup found at %s" % _backup_path())
    shutil.copyfile(_backup_path(), _overrides_path())
    os.remove(_backup_path())
    if os.path.isfile(_marker_path()):
        os.remove(_marker_path())
    print("Original keymap overrides restored. RESTART Houdini.")

