"""Run with hython:  hython tests/test_runtime.py
Tests config loading and node creation in real SOP/VOP networks using a stub
editor (hython has no UI, so hotkeys/cursor are not covered)."""

import os
import sys
import tempfile
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "python"))

import hou  # noqa: E402
from network_shortcuts import config, runtime  # noqa: E402


class StubEditor(object):
    def __init__(self, parent):
        self._p = parent

    def pwd(self):
        return self._p

    def cursorPosition(self):
        return hou.Vector2(3, 4)


failures = []


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        failures.append(msg)


geo = hou.node("/obj").createNode("geo")
sop_ed = StubEditor(geo)
avop = geo.createNode("attribvop")
vop_ed = StubEditor(avop)

cfg = config.load(user_path=os.devnull)
check(len(cfg["keys"]) == 21 and cfg["auto_shelf"] is True, "default config loads (%d keys)" % len(cfg["keys"]))

cfg = config.load(user_path=os.devnull)

# Every action creates the right node (or nothing) in each network
for action, spec in cfg["actions"].items():
    for kind, ed in (("sop", sop_ed), ("vop", vop_ed)):
        node = runtime.create(action, cfg=cfg, editor=ed)
        if kind in spec:
            wanted = spec[kind]["type"]
            wanted = [wanted] if isinstance(wanted, str) else wanted
            # createNode("x") resolves to the newest version, e.g. "x::2.0"
            check(node is not None
                  and (node.type().name() in wanted
                       or node.type().name().split("::")[0] in [w.split("::")[0] for w in wanted]),
                  "%s in %s -> %s" % (action, kind, node.type().name() if node else None))
        else:
            check(node is None, "%s in %s -> nothing" % (action, kind))

# Same key, different node per network
check(runtime.create("merge_multiply", cfg, sop_ed).type().name() == "merge", "M in SOP = merge")
check(runtime.create("merge_multiply", cfg, vop_ed).type().name() == "multiply", "M in VOP = multiply")

# Constant types
for action, token in (("const_float", "float"), ("const_vector2", "float2"),
                      ("const_vector3", "float3"), ("const_vector4", "float4")):
    node = runtime.create(action, cfg, vop_ed)
    check(node.parm("consttype").evalAsString() == token, "%s sets consttype=%s" % (action, token))

# Unsupported network is a no-op
obj_ed = StubEditor(hou.node("/obj"))
check(runtime.create("merge_multiply", cfg, obj_ed) is None, "/obj network is ignored")

# Bad parm value fails loudly
bad = {"actions": {"x": {"vop": {"type": "constant", "parms": {"consttype": "nope"}}}}}
try:
    runtime.create("x", cfg=dict(cfg, actions=bad["actions"]), editor=vop_ed)
    check(False, "bad menu value should raise")
except runtime.ShortcutError:
    check(True, "bad menu value raises ShortcutError")

# Config validation
for broken, label in (({"keys": {"nope": "Z"}}, "unknown action"),
                      ({"keys": {"wrangle": "M"}}, "duplicate key")):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(broken, fh)
    try:
        config.load(user_path=fh.name)
        check(False, label + " should be rejected")
    except ValueError:
        check(True, label + " rejected")

print("\n%d failure(s)" % len(failures))
sys.exit(1 if failures else 0)

