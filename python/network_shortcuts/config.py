"""Config loading: shipped actions + default keys + optional user overrides.

Pure Python (no `hou` import) so it can be unit-tested outside Houdini.

Layers, later wins:
    config/actions.json            shipped actions (action -> node per network)
    config/keys.json               shipped default key layout
    <user dir>/user.json           user overrides (see README)

user.json example:
    {
      "keys": {"transform": "Shift+T", "null": null},
      "actions": {
        "my_remesh": {"label": "Remesh", "sop": {"type": "remesh"}}
      }
    }
A key of null removes that binding.
"""

import json
import os

ROOT_ENV = "NETWORK_SHORTCUTS"
NETWORKS = ("sop", "vop")


def root_dir():
    root = os.environ.get(ROOT_ENV)
    if root:
        return root
    # <root>/python/network_shortcuts/config.py -> <root>
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def user_dir():
    base = os.environ.get("HOUDINI_USER_PREF_DIR")
    if not base:
        try:
            import hou
            base = hou.homeHoudiniDirectory()
        except Exception:
            base = os.path.join(os.path.expanduser("~"), ".network_shortcuts_fallback")
    return os.path.join(base, "network_shortcuts")


def _load(path, required=True):
    if not os.path.isfile(path):
        if required:
            raise FileNotFoundError(path)
        return {}
    with open(path, "r", encoding="utf-8-sig") as fh:     # tolerate a BOM (Windows Notepad)
        return json.load(fh)


def validate_action(name, spec):
    if not isinstance(spec, dict):
        raise ValueError("action %r must be an object" % name)
    found = False
    for net in NETWORKS:
        node = spec.get(net)
        if node is None:
            continue
        found = True
        types = node.get("type")
        if isinstance(types, str):
            types = [types]
        if not types or not all(isinstance(t, str) and t for t in types):
            raise ValueError("action %r: %s.type must be a string or list of strings" % (name, net))
        if not isinstance(node.get("parms", {}), dict):
            raise ValueError("action %r: %s.parms must be an object" % (name, net))
    if not found:
        raise ValueError("action %r defines none of %s" % (name, NETWORKS))


def load(root=None, user_path=None):
    """Return dict(actions, keys, auto_shelf). Raises ValueError on bad config."""
    root = root or root_dir()
    user_path = user_path or os.path.join(user_dir(), "user.json")
    user = _load(user_path, required=False)

    actions = dict(_load(os.path.join(root, "config", "actions.json"))["actions"])
    actions.update(user.get("actions", {}))
    for name, spec in actions.items():
        validate_action(name, spec)

    keys = dict(_load(os.path.join(root, "config", "keys.json"))["keys"])
    for action, key in user.get("keys", {}).items():
        if key is None:
            keys.pop(action, None)
        else:
            keys[action] = key

    unknown = sorted(a for a in keys if a not in actions)
    if unknown:
        raise ValueError("keys refer to unknown actions: %s" % unknown)

    seen = {}
    for action, key in keys.items():
        norm = normalize_key(key)
        if norm in seen:
            raise ValueError("key %r is assigned to both %r and %r" % (key, seen[norm], action))
        seen[norm] = action
    return {"actions": actions, "keys": keys, "auto_shelf": bool(user.get("auto_shelf", True))}


def normalize_key(key):
    parts = [p.strip() for p in str(key).split("+")]
    mods = sorted(p.capitalize() for p in parts[:-1])
    return "+".join(mods + [parts[-1].upper() if len(parts[-1]) == 1 else parts[-1]])


def tool_name(action):
    return "qns_" + action

