"""Run with hython:  hython tests/test_runtime.py
Tests config loading and node creation in real SOP/VOP networks using a stub
editor (hython has no UI, so hotkeys/cursor are not covered)."""

import os
import sys
import tempfile
import json
from unittest.mock import Mock, patch

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

# Python scripts get the editor context, run in any network, and take precedence over nodes.
script = "hou.ui.seen(hou, editor, parent, kind, cursor)"
python_cfg = {"actions": {"script": {"label": "Script", "python": script,
                                     "sop": {"type": "no_such_node"}}}}
for kind, ed in (("sop", sop_ed), ("vop", vop_ed), (None, obj_ed), (None, None)):
    status = Mock()
    with patch.object(config, "load", return_value=python_cfg), \
            patch.object(runtime, "find_network_editor") as find_editor, \
            patch.object(hou, "ui", status, create=True):
        if ed is None:
            find_editor.side_effect = runtime.ShortcutError("No Network Editor found")
        else:
            find_editor.return_value = ed
        runtime.run("script")
        expected = (hou, ed, ed.pwd() if ed is not None else None, kind,
                    ed.cursorPosition() if ed is not None else None)
        check(status.seen.call_args is not None and status.seen.call_args.args == expected,
              "Python action sees variables in %s" % (ed.pwd().path() if ed else "no editor"))
        check(not status.setStatusMessage.called, "successful Python action has no error status")

for code in ("raise RuntimeError('script failed')", "raise SystemExit('script failed')",
             "if broken syntax"):
    python_cfg = {"actions": {"script": {"python": code}}}
    status = Mock()
    with patch.object(config, "load", return_value=python_cfg), \
            patch.object(runtime, "find_network_editor", return_value=sop_ed), \
            patch.object(hou, "ui", status, create=True):
        try:
            runtime.run("script")
            call = status.setStatusMessage.call_args
            check(call is not None and call.kwargs.get("severity") == hou.severityType.Error
                  and ("script failed" in call.args[0] if "script failed" in code
                       else "syntax" in call.args[0]), "Python error is reported without raising: " + code)
        except BaseException:
            check(False, "Python error must not raise: " + code)

# Bad parm value fails loudly
bad = {"actions": {"x": {"vop": {"type": "constant", "parms": {"consttype": "nope"}}}}}
try:
    runtime.create("x", cfg=dict(cfg, actions=bad["actions"]), editor=vop_ed)
    check(False, "bad menu value should raise")
except runtime.ShortcutError:
    check(True, "bad menu value raises ShortcutError")

# Config validation
config.validate_action("script", {"python": "hou.ui.displayMessage('hi')"})
check(True, "Python-only action validates")
for value in ("", "   ", None, 42, [], {}):
    try:
        config.validate_action("script", {"python": value, "sop": {"type": "null"}})
        check(False, "invalid Python value should be rejected: %r" % (value,))
    except ValueError:
        check(True, "invalid Python value rejected: %r" % (value,))

for broken, label in (({"keys": {"nope": "Z"}}, "unknown action"),
                      ({"keys": {"wrangle": "M"}}, "duplicate key")):
    with tempfile.NamedTemporaryFile("w", suffix=".json", dir=ROOT, delete=False) as fh:
        json.dump(broken, fh)
    try:
        config.load(user_path=fh.name)
        check(False, label + " should be rejected")
    except ValueError:
        check(True, label + " rejected")
    finally:
        os.remove(fh.name)

print("\n%d failure(s)" % len(failures))
sys.exit(1 if failures else 0)

