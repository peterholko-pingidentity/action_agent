"""
Action Agent - Identity & Access Management A2A Server

Receives conversational context from Chat Agent via A2A protocol.
Calls PingOne MCP & Microsoft Graph MCP servers.
"""

import os
from strands import Agent, tool
from strands.multiagent.a2a import A2AServer


# Tools
@tool
def log_action(action: str, target: str, result: str, details: dict = None):
    """Log an action for audit trail."""
    print(f"[LOG] {action} on {target}: {result}")
    return f"Logged: {action} on {target}"


@tool
def validate_request(request_type: str, data: dict):
    """Validate request has required fields."""
    required = {
        "create_user": ["email", "first_name", "last_name"],
        "grant_access": ["user_id", "resource_id"],
        "assign_group": ["user_id", "group_id"],
    }

    if request_type not in required:
        return {"valid": False, "error": "Unknown request type"}

    missing = [f for f in required[request_type] if f not in data]
    if missing:
        return {"valid": False, "error": f"Missing: {', '.join(missing)}"}

    return {"valid": True}


# Create agent
agent = Agent(
    name="Action Agent",
    description="Identity & access management executor for PingOne and Microsoft Graph",
    tools=[log_action, validate_request],
    system_prompt="""You are the Action Agent. Execute identity operations via PingOne and Microsoft Graph MCP servers.
Always validate requests, log actions, and return clear results with resource IDs."""
)

# TODO: When MCP servers ready, add tools here:
# from strands.tools.mcp import MCPClient
# pingone_tools = pingone_mcp_client.list_tools_sync()
# msgraph_tools = msgraph_mcp_client.list_tools_sync()
# agent.tools.extend(pingone_tools)
# agent.tools.extend(msgraph_tools)

# Expose as A2A server
a2a_server = A2AServer(agent=agent, version="1.0.0")

# Start server
if __name__ == "__main__":
    host = os.getenv("A2A_HOST", "127.0.0.1")
    port = int(os.getenv("A2A_PORT", "9000"))

    print(f"\nAction Agent A2A Server")
    print(f"Address: http://{host}:{port}")
    print(f"Status: Ready for Chat Agent\n")

    a2a_server.serve(host=host, port=port)
