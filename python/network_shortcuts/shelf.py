"""Generate toolbar/network_shortcuts.shelf from config/actions.json.

Run outside Houdini:  python python/network_shortcuts/shelf.py
The .shelf lives inside the package, so the user's default.shelf is never touched.
"""

import os
import sys
from xml.sax.saxutils import quoteattr

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from network_shortcuts import config  # noqa: E402

SCRIPT = "import network_shortcuts\nnetwork_shortcuts.run(%r)\n"


ADMIN_TOOLS = [
    ("qns_admin_keys", "NS: Customize keys...",
     "import network_shortcuts.ui as ui\nui.show()\n"),
]


def build(root):
    cfg = config.load(root=root, user_path=os.devnull)
    tools = []
    for name, spec in cfg["actions"].items():
        label = spec.get("label", name)
        tools.append(
            '  <tool name=%s label=%s icon="MISC_python">\n'
            "    <script scriptType=\"python\"><![CDATA[%s]]></script>\n"
            "  </tool>\n" % (quoteattr(config.tool_name(name)), quoteattr("NS: " + label),
                             SCRIPT % name))
    for tname, label, body in ADMIN_TOOLS:
        tools.append(
            '  <tool name=%s label=%s icon="MISC_python">\n'
            "    <script scriptType=\"python\"><![CDATA[%s]]></script>\n"
            "  </tool>\n" % (quoteattr(tname), quoteattr(label), body))
    tool_refs = "".join('    <memberTool name=%s/>\n' % quoteattr(t[0]) for t in ADMIN_TOOLS)
    tool_refs += "".join('    <memberTool name=%s/>\n' % quoteattr(config.tool_name(n))
                        for n in cfg["actions"])
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<shelfDocument>\n'
            + "".join(tools)
            + '  <toolshelf name="network_shortcuts" label="Network Shortcuts">\n'
            + tool_refs + "  </toolshelf>\n</shelfDocument>\n")


def build_user(actions):
    """Shelf for user-defined actions (written by the key settings window)."""
    tools = []
    for name, spec in actions.items():
        tools.append(
            '  <tool name=%s label=%s icon="MISC_python">\n'
            "    <script scriptType=\"python\"><![CDATA[%s]]></script>\n"
            "  </tool>\n" % (quoteattr(config.tool_name(name)),
                             quoteattr("NS: " + spec.get("label", name)), SCRIPT % name))
    refs = "".join('    <memberTool name=%s/>\n' % quoteattr(config.tool_name(n)) for n in actions)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<shelfDocument>\n' + "".join(tools)
            + '  <toolshelf name="network_shortcuts_custom" label="Network Shortcuts (custom)">\n'
            + refs + "  </toolshelf>\n</shelfDocument>\n")


if __name__ == "__main__":
    root = config.root_dir()
    out = os.path.join(root, "toolbar", "network_shortcuts.shelf")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(build(root))
    print("wrote", out)

