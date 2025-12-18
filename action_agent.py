"""
Action Agent - Identity & Access Management A2A Server

- Receives conversational context from a Chat Agent via A2A
- Uses MCP tools from PingOne and Microsoft Graph MCP servers
"""

import os
from contextlib import asynccontextmanager
from strands import Agent, tool
from strands.multiagent.a2a import A2AServer
from strands.tools.mcp import MCPClient
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamable_http_client
import uvicorn
from fastapi import FastAPI  

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
        "MSGRAPH_MCP_URL must be set in environment"
    )


# Create MCP client with HTTP transport
streamable_http_mcp_client = MCPClient(
    lambda: streamable_http_client(MSGRAPH_MCP_URL)
)

# -------------------------------------------------------------------
# Global variables for agent and server
# -------------------------------------------------------------------

agent = None
a2a_server = None

# -------------------------------------------------------------------
# FastAPI Lifespan - Keep MCP client session open
# -------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage MCP client lifecycle - keep session open while app runs."""
    global agent, a2a_server

    print("Starting MCP client session...")

    # Enter the MCP client context and keep it open
    streamable_http_mcp_client.__enter__()

    try:
        print("MCP client session started successfully")

        # Load tools from MCP server (now that session is active)
        msgraph_tools = streamable_http_mcp_client.list_tools_sync()

        all_tools = [
            log_action,
            validate_request,
            *msgraph_tools,
        ]

        print(f"Loaded {len(all_tools)} tools: {[t.name if hasattr(t, 'name') else str(t) for t in all_tools]}")

        runtime_url = os.environ.get('AGENTCORE_RUNTIME_URL', 'http://127.0.0.1:9000/')

        # Create agent with MCP tools
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

        # Create A2A server
        a2a_server = A2AServer(agent=agent, http_url=runtime_url, serve_at_root=True, version="1.0.0")

        # Mount the A2A server routes
        app.mount("/", a2a_server.to_fastapi_app())

        print("Action Agent ready and MCP client session active")

        yield  # App runs here with MCP client active
    finally:
        print("Shutting down MCP client session...")
        streamable_http_mcp_client.__exit__(None, None, None)
        print("MCP client session closed")


# -------------------------------------------------------------------
# FastAPI App
# -------------------------------------------------------------------

app = FastAPI(lifespan=lifespan)

@app.get("/ping")
def ping():
    return {"status": "healthy"}

if __name__ == "__main__":
    host, port = "0.0.0.0", 9000
    uvicorn.run(app, host=host, port=port)
