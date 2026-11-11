# Changelog

## 0.4.0
- Custom Python script actions, with access to the current Network Editor and network.
- Changed: the Parameter node now defaults to `Ctrl+P`, so Houdini's own `P` (show parameter dialog) is kept.
- Fixed: re-applying keys now restores Houdini keys that are no longer replaced.

## 0.3.0
- First start after installing shows a welcome window with a one-click **Turn on keys now** button.
- README rewritten as a 3-step quick start with screenshots; added a Japanese README.
- The release zip has a fixed name (houdini-network-shortcuts.zip), so the download link in the README always points to the latest version.

## 0.2.0
- One default key layout (presets removed); `Reset keys to defaults` in the window.
- Key settings window: change keys, conflict display, enable / disable (restores your original keymap), custom nodes picked from lists, delete custom nodes.
- The Network Shortcuts shelf tab is opened automatically at startup and after file load / new file.
- Installer: copies the tool into your Houdini prefs folder, installs / updates / uninstalls, supports several Houdini versions, `install.bat` for Windows.
- Tested on Houdini 22.0.466 (Windows) only.

## 0.1.0
- First version: one-key node creation for SOP / VOP, hotkey installer.
