# Houdini Network Shortcuts

One key press creates a node at the mouse cursor in the Network Editor. The same key makes a different node in SOP and VOP (`M` = **Merge** in SOP, **Multiply** in VOP), like the quick-add workflow of Blender Geometry Nodes / Unreal.

No auto-wiring. Only SOP and VOP networks react; other networks are left alone.

## Status (please read)

Developed and tested only on **Houdini 22.0.466 (Windows)**. It uses the Houdini 20.5+ hotkey API, but other versions have not been tested.

| Part | State |
|---|---|
| Node creation, SOP/VOP switching, Constant types, config validation | `hython tests/test_runtime.py`: 0 failures (stub editor, so cursor position is not covered). |
| Pressing a key creates the node at the cursor in SOP and VOP networks | Confirmed by hand by the author in Houdini 22.0.466. |
| Key settings window, enable/disable, custom nodes, auto shelf tab | Driven from a script in an isolated Houdini 22.0.466 GUI session (restart persistence, restore to the byte-identical keymap file, node pickers). Clicking through it by hand has only been partly done. |

## Install

1. Download the zip from the Releases page and unzip it anywhere (you can delete the folder after installing). Then:
   - **Windows**: double-click `install.bat` (uses Houdini's own Python; no Python install needed).
   - **Any OS**: `python install.py` (or `hython install.py` from your Houdini's `bin` folder).

   It copies the tool to `<houdini prefs>/network_shortcuts_pkg` and writes one file, `<houdini prefs>/packages/network_shortcuts.json`. It installs into your newest Houdini; `--list` shows the Houdini folders it found, `--houdini-dir <folder>` picks one, `--all` installs into every Houdini 20.5+ it finds. Run it again to **update** (your settings are kept). Houdini older than 20.5 is skipped.
2. Start Houdini. The **Network Shortcuts** shelf tab is put last in the first shelf set and opened at startup and after every file load / new file (Houdini has no API to select a tab, but it selects the last tab of a shelf set when the set changes, which is what this relies on). Turn this off with the checkbox in the settings window.
3. Click **NS: Customize keys...** on that tab, then **Enable / Apply keys**, then restart Houdini once.
4. Remove: **Disable (restore original keys)** in the same window, restart Houdini, then run `install.bat --uninstall` (or `python install.py --uninstall`). It refuses while the keys are still enabled. Your settings are kept; add `--purge` to delete them too.

The default layout **overwrites Houdini's own single-key bindings in the Network Editor** (e.g. `P` toggles the parameter dialog, `G` is Home Selected). Disable restores the keymap you had before your first Enable (a copy is kept in `<houdini prefs>/network_shortcuts/`).

Note: adding the shelf tab edits your shelf set, which Houdini stores in your `default.shelf` (the same thing the `+` button on the shelf does). The shelf and tools of this package themselves live in the package folder.

## Default keys

| Key | SOP | VOP |
|---|---|---|
| `M` | Merge | Multiply |
| `W` | Attribute Wrangle | |
| `G` | Group Expression | |
| `V` | Attribute VOP | Combine (Floats to Vector) |
| `B` | Blast | Bind |
| `T` | Transform | |
| `C` | Copy to Points | Clamp |
| `X` | Scatter | Mix |
| `S` | Switch | Subtract |
| `N` | Null | Null |
| `A` | Attribute Create | Add |
| `D` | Attribute Delete | Divide |
| `O` | Object Merge | |
| `R` | Resample | Random |
| `P` | | Parameter |
| `F` | | Fit Range |
| `Q` | | Compare |
| `1` `2` `3` `4` | | Constant Float / Vector2 / Vector3 / Vector4 |

## Customize

### Key settings window (easiest)

**NS: Customize keys...** opens a table of every action.

- Click a Key box and press the key you want; the clear button in the box removes it.
- The last column shows which Houdini Network Editor key a choice would overwrite. Two actions on the same key turn red and block Apply.
- **Add custom node...**: enter a label and pick a SOP node and a VOP node from searchable lists (either can be `(none)`), then give it a key.
- Your own nodes have a **Delete** button in the last column (removed for good when you press Enable / Apply keys).
- **Reset keys to defaults**, **Enable / Apply keys**, **Disable (restore original keys)** and a status line (ENABLED / DISABLED). Apply and Disable need a Houdini restart.

### Editing user.json by hand

`<houdini prefs>/network_shortcuts/user.json` (written by the window; you can edit it too):

```json
{
  "keys": { "transform": "Shift+T", "null": null },
  "auto_shelf": true,
  "actions": {
    "custom_remesh": { "label": "Remesh", "sop": { "type": "remesh::2.0" } }
  }
}
```

- `keys`: action → key; `null` removes a binding. A key used twice is rejected.
- `actions`: your own actions; `sop` and/or `vop` with `type` (string or fallback list) and optional `parms`.
- Actions added this way get a tool in `<houdini prefs>/toolbar/network_shortcuts_custom.shelf` (written by the window).

## Layout

```
config/actions.json         action -> node per network
config/keys.json            default keys
python/network_shortcuts/   config.py runtime.py installer.py ui.py autoshelf.py shelf.py
python3.*libs/uiready.py    startup hook (shelf tab); coexists with other packages
toolbar/                    generated shelf (package-local)
install.py / install.bat    installer (copy, update, uninstall)
tools/make_release.py       builds dist/<name>-<version>.zip
tests/test_runtime.py       hython tests
```

Build a release zip: `python tools/make_release.py`. Run the tests: `hython tests/test_runtime.py`.

If you change `config/actions.json`, regenerate the shelf with hython: `hython python/network_shortcuts/shelf.py`.

License: MIT
