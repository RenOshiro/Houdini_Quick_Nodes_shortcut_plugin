"""Install / update / remove Network Shortcuts. Plain Python 3, no Houdini session needed.

    python install.py                  # install into the newest Houdini prefs folder found
    python install.py --list           # show the Houdini prefs folders found
    python install.py --houdini-dir "C:/Users/me/Documents/houdini22.0"
    python install.py --all            # every Houdini >= 20.5 found
    python install.py --uninstall      # remove (disable the keys first, see README)
    python install.py --link           # developers: point the package at this folder instead of copying

Windows without Python: double-click install.bat (uses Houdini's own hython).

What it does: copies the tool into <prefs>/network_shortcuts_pkg and writes ONE file,
<prefs>/packages/network_shortcuts.json. It never edits default.shelf, hotkey files or
other packages. Your settings (<prefs>/network_shortcuts/user.json) are kept on update.
"""

import argparse
import glob
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_FILE = "network_shortcuts.json"
COPY_DIR = "network_shortcuts_pkg"
USER_DIR = "network_shortcuts"
MIN_VERSION = (20, 5)
COPY_ITEMS = ("config", "python", "python3.10libs", "python3.11libs", "python3.13libs",
              "toolbar", "LICENSE", "README.md")


def documents_dir():
    if sys.platform == "win32":
        try:                                     # follows OneDrive / redirected Documents
            import ctypes
            buf = ctypes.c_wchar_p()
            # FOLDERID_Documents {FDD39AD0-238F-46AF-ADB4-6C85480369C7} as a little-endian GUID
            folder_id = ctypes.create_string_buffer(
                bytes.fromhex("D09AD3FD8F23AF46ADB46C85480369C7"))
            if ctypes.windll.shell32.SHGetKnownFolderPath(folder_id, 0, None, ctypes.byref(buf)) == 0:
                return buf.value
        except Exception:
            pass
    return os.path.join(os.path.expanduser("~"), "Documents")


def find_pref_dirs():
    """[((major, minor), path)] sorted oldest -> newest."""
    found = []
    if sys.platform == "darwin":
        base = os.path.join(os.path.expanduser("~"), "Library", "Preferences", "houdini")
        pattern, rx = os.path.join(base, "[0-9]*.[0-9]*"), r"(\d+)\.(\d+)$"
    elif sys.platform == "win32":
        pattern, rx = os.path.join(documents_dir(), "houdini[0-9]*.[0-9]*"), r"houdini(\d+)\.(\d+)$"
    else:
        pattern, rx = os.path.join(os.path.expanduser("~"), "houdini[0-9]*.[0-9]*"), r"houdini(\d+)\.(\d+)$"
    for path in glob.glob(pattern):
        m = re.search(rx, path)
        if m and os.path.isdir(path):
            found.append(((int(m.group(1)), int(m.group(2))), path))
    return sorted(found)


def version_of(path):
    m = re.search(r"(\d+)\.(\d+)$", path.rstrip("/\\"))
    return (int(m.group(1)), int(m.group(2))) if m else None


def copy_package(dest):
    if os.path.isdir(dest):
        shutil.rmtree(dest)                      # our own folder: drop stale files from older versions
    os.makedirs(dest)
    for item in COPY_ITEMS:
        src = os.path.join(HERE, item)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(dest, item),
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        elif os.path.isfile(src):
            shutil.copy2(src, os.path.join(dest, item))


def write_package_file(pref, root):
    root = root.replace("\\", "/")
    data = {
        "enable": True,
        "path": root,
        "env": [
            {"NETWORK_SHORTCUTS": root},
            {"PYTHONPATH": {"method": "prepend", "value": root + "/python"}},
        ],
    }
    target = os.path.join(pref, "packages", PKG_FILE)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    return target


def keys_enabled(pref):
    return os.path.isfile(os.path.join(pref, USER_DIR, "installed_keys.json"))


def install(pref, link=False):
    dest = HERE if link else os.path.join(pref, COPY_DIR)
    if not link:
        copy_package(dest)
    target = write_package_file(pref, dest)
    print("Installed into", pref)
    print("  package file:", target)
    print("  tool folder :", dest)


def uninstall(pref, force=False, purge=False):
    if keys_enabled(pref) and not force:
        print("SKIPPED %s: the keys are still enabled." % pref)
        print("  Open Houdini > Network Shortcuts tab > Customize keys... > Disable (restore original keys),")
        print("  restart Houdini, then run this again. (--force removes the tool anyway; your original")
        print("  keys stay in %s)" % os.path.join(pref, USER_DIR, "keymap_overrides_backup.json"))
        return False
    removed = []
    target = os.path.join(pref, "packages", PKG_FILE)
    if os.path.isfile(target):
        os.remove(target)
        removed.append(target)
    dest = os.path.join(pref, COPY_DIR)
    if os.path.isdir(dest):
        shutil.rmtree(dest)
        removed.append(dest)
    if purge:
        for extra in (os.path.join(pref, USER_DIR),
                      os.path.join(pref, "toolbar", "network_shortcuts_custom.shelf")):
            if os.path.isdir(extra):
                shutil.rmtree(extra)
                removed.append(extra)
            elif os.path.isfile(extra):
                os.remove(extra)
                removed.append(extra)
    print("Removed:" if removed else "Nothing to remove in", *removed or [pref], sep="\n  ")
    if not purge:
        print("Kept your settings in %s (use --purge to delete them too)." % os.path.join(pref, USER_DIR))
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--houdini-dir", help="a Houdini preferences folder, e.g. .../houdini22.0")
    ap.add_argument("--all", action="store_true", help="every Houdini >= 20.5 found")
    ap.add_argument("--list", action="store_true", help="list Houdini prefs folders and exit")
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--purge", action="store_true", help="with --uninstall: also delete your settings")
    ap.add_argument("--force", action="store_true", help="skip safety checks (old Houdini, keys enabled)")
    ap.add_argument("--link", action="store_true", help="use this folder in place instead of copying")
    args = ap.parse_args()

    found = find_pref_dirs()
    if args.list:
        for ver, path in found:
            print("%d.%d  %s%s" % (ver[0], ver[1], path, "" if ver >= MIN_VERSION else "  (too old)"))
        if not found:
            print("No Houdini preferences folders found.")
        return

    if args.houdini_dir:
        targets = [args.houdini_dir]
    elif args.all:
        targets = [p for v, p in found if v >= MIN_VERSION]
    elif found:
        targets = [found[-1][1]]
    else:
        targets = []
    if not targets:
        sys.exit("No Houdini preferences folder found. Start Houdini once, or pass --houdini-dir.")

    for pref in targets:
        if not os.path.isdir(pref):
            sys.exit("Not a folder: %s" % pref)
        ver = version_of(pref)
        if args.uninstall:
            uninstall(pref, args.force, args.purge)
            continue
        if ver and ver < MIN_VERSION and not args.force:
            print("SKIPPED %s: Houdini %d.%d is older than 20.5 (the hotkey API differs). --force to try." % ((pref,) + ver))
            continue
        install(pref, args.link)
    if not args.uninstall:
        print("\nNext: start Houdini, open the Network Shortcuts shelf tab, click 'NS: Customize keys...',")
        print("press 'Enable / Apply keys', then restart Houdini once.")


if __name__ == "__main__":
    main()
