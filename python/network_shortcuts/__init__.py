"""Network Shortcuts: one-key node creation for Houdini SOP / VOP networks."""

__version__ = "0.3.0"


def run(action):
    from . import runtime
    return runtime.run(action)
