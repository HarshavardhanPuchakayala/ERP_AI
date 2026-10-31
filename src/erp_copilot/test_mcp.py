
import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).resolve().parent / "mcp_server.py"


async def main():
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            listing = await session.list_tools()
            print("=== Tools exposed over MCP ===")
            for t in listing.tools:
                print(" -", t.name)

            print("\n=== Call: customers_who_owe(limit=2) ===")
            result = await session.call_tool("customers_who_owe", {"limit": 2})
            print(result.content[0].text)

            print("\n=== SAFETY: try a tool that must not exist ===")
            for bad in ("delete_invoice", "run_sql"):
                try:
                    res = await session.call_tool(bad, {"invoice_no": "SINV-0001"})
                    print(f"{bad}: isError={res.isError} ->", res.content[0].text[:120])
                except Exception as e:
                    print(f"{bad}: rejected ->", type(e).__name__)


asyncio.run(main())