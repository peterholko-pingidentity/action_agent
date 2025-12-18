"""
Action Agent - Identity & Access Management A2A Server

- Receives conversational context from a Chat Agent via A2A
- Uses MCP tools from PingOne and Microsoft Graph MCP servers
"""

import os
from strands import Agent, tool
from strands.multiagent.a2a import A2AServer
from strands.tools.mcp import MCPClient
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamable_http_client


# -------------------------------------------------------------------
# Helper tools
# -------------------------------------------------------------------

@tool
def log_action(action: str, target: str, result: str) -> str:
    """Log an action for audit trail."""
    print(f"[LOG] {action} on {target}: {result}")
    return f"Logged: {action} on {target}: {result}"


@tool
def validate_request(request_type: str, data: dict) -> dict:
    """Validate that a request has required fields."""
    required_fields = {
        "create_user": ["email", "first_name", "last_name"],
        "grant_access": ["user_id", "resource_id"],
        "assign_group": ["user_id", "group_id"],
    }

    fields = required_fields.get(request_type)
    if fields is None:
        return {"valid": False, "error": f"Unknown request_type: {request_type}"}

    missing = [f for f in fields if f not in data]
    if missing:
        return {"valid": False, "error": f"Missing fields: {', '.join(missing)}"}

    return {"valid": True}


# -------------------------------------------------------------------
# MCP client setup
# -------------------------------------------------------------------

#PINGONE_MCP_URL = os.getenv("PINGONE_MCP_URL")
MSGRAPH_MCP_URL = "http://100.28.229.240:8000/mcp"

if not MSGRAPH_MCP_URL:
    raise RuntimeError(
        "PINGONE_MCP_URL and MSGRAPH_MCP_URL must be set in environment"
    )


# Create MCP clients with HTTP transport
#pingone_client = MCPClient(lambda: sse_client(PINGONE_MCP_URL))
#msgraph_client = MCPClient(lambda: sse_client(MSGRAPH_MCP_URL))


streamable_http_mcp_client = MCPClient(
    lambda: streamable_http_client(MSGRAPH_MCP_URL)
)

# Load tools from MCP servers
try :
    with streamable_http_mcp_client:
        print("Hello")
        msgraph_tools = streamable_http_mcp_client.list_tools_sync()
        
except Exception as e: 
    print("Error entering MCP client:", e)


# -------------------------------------------------------------------
# Create Action Agent
# -------------------------------------------------------------------


all_tools = [
    log_action,
    validate_request,
    #*pingone_tools,
    *msgraph_tools,
]

print(all_tools)

agent = Agent(
    name="Action Agent",
    description="Executes identity & access operations via PingOne and Microsoft Graph",
    tools=all_tools,
    system_prompt=(
        "You are the Action Agent in an identity & access management system.\n"
        "- You receive structured requests (and conversational context) from a Chat Agent.\n"
        "- Use PingOne MCP tools for identity, auth, groups, and policies.\n"
        "- Use Microsoft Graph MCP tools for Microsoft 365 user and group operations.\n"
        "- Always validate requests with validate_request before making changes.\n"
        "- Always log important actions with log_action.\n"
        "- Return clear, concise results including any important IDs (user IDs, group IDs, etc.).\n"
        "- If a request is invalid, respond with a structured error message instead of guessing."
    ),
)

a2a_server = A2AServer(agent=agent, version="1.0.0")


# -------------------------------------------------------------------
# Start server
# -------------------------------------------------------------------

if __name__ == "__main__":
    host = os.getenv("A2A_HOST", "127.0.0.1")
    port = int(os.getenv("A2A_PORT", "9000"))

    print(f"\nAction Agent A2A Server")
    print(f"Address: http://{host}:{port}")
    #print(f"PingOne MCP: {PINGONE_MCP_URL}")
    print(f"MS Graph MCP: {MSGRAPH_MCP_URL}")
    print(f"Tools loaded: {len(all_tools)}\n")

    a2a_server.serve(host=host, port=port)
