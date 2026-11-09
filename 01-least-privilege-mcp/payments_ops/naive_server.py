"""Naive baseline: a generic SQL tool pair over a read-write database.

This is deliberately what a quick first version looks like. It exists only so
the scoped server has something to be compared against. Never deploy it.
"""

import shutil
import sqlite3
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

SOURCE_DB = Path(__file__).resolve().parent.parent / "data" / "payments.db"
NAIVE_DB = Path(__file__).resolve().parent.parent / "data" / "naive.db"

mcp = MCPServer("payments-ops-naive")


def _connect() -> sqlite3.Connection:
    # Read-write connection to the whole database.
    return sqlite3.connect(NAIVE_DB)


@mcp.tool()
def query(sql: str) -> list[list]:
    """Run any SQL against the payments database and return the rows."""
    con = _connect()
    try:
        rows = con.execute(sql).fetchall()
        con.commit()
        return [list(r) for r in rows]
    except Exception as e:
        raise ToolError(str(e))
    finally:
        con.close()


@mcp.tool()
def execute(sql: str) -> dict:
    """Run any SQL statement that changes data (insert, update, delete, ...)."""
    con = _connect()
    try:
        cur = con.execute(sql)
        con.commit()
        return {"rows_affected": cur.rowcount}
    except Exception as e:
        raise ToolError(str(e))
    finally:
        con.close()


if __name__ == "__main__":
    # Fresh copy on every start, so each attack run begins from the same data
    # and the real dataset is never touched.
    shutil.copyfile(SOURCE_DB, NAIVE_DB)
    mcp.run()