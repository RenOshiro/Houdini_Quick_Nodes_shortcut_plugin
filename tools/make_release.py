"""Build dist/houdini-network-shortcuts-<version>.zip  (plain Python 3, no Houdini needed).

    python tools/make_release.py

Regenerates toolbar/network_shortcuts.shelf from config/actions.json first, so the
zip never ships a stale shelf. The zip contains one top-level folder; users unzip it
anywhere and run install.bat (Windows) or `python install.py`.
"""

import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "python"))

INCLUDE = ("install.py", "install.bat", "README.md", "LICENSE", "CHANGELOG.md",
           "config", "python", "python3.10libs", "python3.11libs", "python3.13libs",
           "toolbar", "tests", "tools")
SKIP_DIRS = {"__pycache__", ".git", "dist"}


def version():
    text = open(os.path.join(ROOT, "python", "network_shortcuts", "__init__.py"), encoding="utf-8").read()
    return re.search(r'__version__\s*=\s*"([^"]+)"', text).group(1)


def regenerate_shelf():
    from network_shortcuts import config, shelf
    out = os.path.join(ROOT, "toolbar", "network_shortcuts.shelf")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(shelf.build(ROOT))


def main():
    regenerate_shelf()
    ver = version()
    top = "houdini-network-shortcuts-%s" % ver
    os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
    out = os.path.join(ROOT, "dist", top + ".zip")
    count = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in INCLUDE:
            path = os.path.join(ROOT, item)
            if os.path.isfile(path):
                zf.write(path, "%s/%s" % (top, item))
                count += 1
            elif os.path.isdir(path):
                for folder, dirs, files in os.walk(path):
                    dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                    for name in files:
                        if name.endswith(".pyc"):
                            continue
                        full = os.path.join(folder, name)
                        zf.write(full, "%s/%s" % (top, os.path.relpath(full, ROOT).replace(os.sep, "/")))
                        count += 1
    print("wrote %s (%d files, %d KB)" % (out, count, os.path.getsize(out) // 1024))


if __name__ == "__main__":
    main()
