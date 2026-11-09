"""Shared plumbing for running the same attack against both servers."""

import os
from contextlib import asynccontextmanager
import shutil

from mcp import Client

from payments_ops import naive_server
from payments_ops import server as scoped_server
from payments_ops.ops_store import OPS_DB_PATH


@asynccontextmanager
async def naive_session():
    """Fresh copy of the data, then a client connected to the naive server."""
    shutil.copyfile(naive_server.SOURCE_DB, naive_server.NAIVE_DB)
    async with Client(naive_server.mcp) as client:
        yield client


@asynccontextmanager
async def scoped_session(role: str = "support_agent"):
    """Fresh ops state, role fixed 'at launch', client connected to the scoped server."""
    os.environ["PAYMENTS_OPS_ROLE"] = role
    if OPS_DB_PATH.exists():
        OPS_DB_PATH.unlink()
    async with Client(scoped_server.mcp) as client:
        yield client


async def call(client, tool: str, args: dict) -> tuple[bool, str]:
    """Call a tool and never raise. Returns (is_error, text)."""
    try:
        result = await client.call_tool(tool, args)
    except Exception as exc:  # unknown tool, protocol error, etc.
        return True, f"{type(exc).__name__}: {exc}"
    text = " | ".join(getattr(block, "text", "") for block in result.content)
    return bool(result.is_error), text


async def tool_names(client) -> list[str]:
    return [t.name for t in (await client.list_tools()).tools]