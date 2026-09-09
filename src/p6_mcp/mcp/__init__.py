"""MCP adapter layer. Contains no business logic — every tool is a thin
translation between MCP arguments and the services package.

``build_server`` is imported lazily (see ``p6_mcp.mcp.server``) so importing
submodules such as ``p6_mcp.mcp.context`` does not require the whole tree.
"""

__all__ = ["build_server"]


def __getattr__(name: str) -> object:
    if name == "build_server":
        from p6_mcp.mcp.server import build_server

        return build_server
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
