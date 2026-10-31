
from mcp.server.fastmcp import FastMCP

from tools import TOOL_FUNCTIONS

mcp = FastMCP("erp-copilot")


for func in TOOL_FUNCTIONS.values():
    mcp.tool()(func)

if __name__ == "__main__":
    mcp.run()  