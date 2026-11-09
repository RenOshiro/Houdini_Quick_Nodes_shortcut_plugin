# Runs once the Houdini UI is ready (the package puts this folder on HOUDINI_PATH).
try:
    import network_shortcuts.autoshelf as _qns_autoshelf
    _qns_autoshelf.start()
except Exception as _qns_exc:
    print("Network Shortcuts: startup hook failed: %s" % _qns_exc)