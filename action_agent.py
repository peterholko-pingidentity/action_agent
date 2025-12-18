"""
Action Agent - Identity & Access Management for AWS Bedrock Agentcore

- Receives requests from AWS Bedrock Agents via REST API
- Uses MCP tools from PingOne and Microsoft Graph MCP servers
- No Lambda required - runs as containerized API endpoint
"""

import os
import json
from typing import Dict, List, Any
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
from strands import Agent, tool
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
        "- You receive structured requests from AWS Bedrock Agents.\n"
        "- Use PingOne MCP tools for identity, auth, groups, and policies.\n"
        "- Use Microsoft Graph MCP tools for Microsoft 365 user and group operations.\n"
        "- Always validate requests with validate_request before making changes.\n"
        "- Always log important actions with log_action.\n"
        "- Return clear, concise results including any important IDs (user IDs, group IDs, etc.).\n"
        "- If a request is invalid, respond with a structured error message instead of guessing."
    ),
)


# -------------------------------------------------------------------
# FastAPI app for Bedrock Agent integration
# -------------------------------------------------------------------

app = FastAPI(
    title="Action Agent for AWS Bedrock",
    description="Identity & Access Management actions for AWS Bedrock Agents",
    version="1.0.0"
)


def format_bedrock_response(
    action_group: str,
    function: str,
    response_body: str
) -> Dict[str, Any]:
    """Format response in AWS Bedrock Agent expected format."""
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": action_group,
            "function": function,
            "functionResponse": {
                "responseBody": {
                    "TEXT": {
                        "body": response_body
                    }
                }
            }
        }
    }


def parse_bedrock_parameters(parameters: List[Dict[str, str]]) -> Dict[str, Any]:
    """Parse Bedrock Agent parameters into a dictionary."""
    result = {}
    for param in parameters:
        name = param.get("name")
        value = param.get("value")
        if name and value:
            # Try to parse JSON values
            try:
                result[name] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                result[name] = value
    return result


@app.post("/")
async def bedrock_action_handler(request: Request):
    """
    Main handler for AWS Bedrock Agent action group invocations.

    Bedrock sends requests in this format:
    {
        "messageVersion": "1.0",
        "agent": {...},
        "inputText": "user's natural language input",
        "sessionId": "unique-session-id",
        "actionGroup": "action-group-name",
        "function": "function-name",
        "parameters": [
            {"name": "param1", "type": "string", "value": "value1"},
            ...
        ]
    }
    """
    try:
        body = await request.json()

        action_group = body.get("actionGroup", "unknown")
        function_name = body.get("function", "unknown")
        parameters = body.get("parameters", [])
        input_text = body.get("inputText", "")
        session_id = body.get("sessionId", "")

        print(f"\n[Bedrock Request] Function: {function_name}")
        print(f"[Bedrock Request] Parameters: {parameters}")
        print(f"[Bedrock Request] Input: {input_text}")

        # Parse parameters
        params = parse_bedrock_parameters(parameters)

        # Build prompt for the agent
        prompt = f"Execute {function_name} with parameters: {json.dumps(params)}"
        if input_text:
            prompt = f"{input_text}\n\nFunction to execute: {function_name}\nParameters: {json.dumps(params)}"

        # Execute agent
        result = agent.run(prompt)

        # Format response for Bedrock
        response = format_bedrock_response(
            action_group=action_group,
            function=function_name,
            response_body=result
        )

        print(f"[Bedrock Response] {result}\n")

        return JSONResponse(content=response)

    except Exception as e:
        print(f"[Error] {str(e)}")
        # Return error in Bedrock format
        error_response = format_bedrock_response(
            action_group=body.get("actionGroup", "unknown"),
            function=body.get("function", "unknown"),
            response_body=f"Error: {str(e)}"
        )
        return JSONResponse(content=error_response, status_code=200)


@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {
        "status": "healthy",
        "tools": len(all_tools),
        "msgraph_mcp": MSGRAPH_MCP_URL
    }


@app.get("/schema")
async def get_schema():
    """
    Return OpenAPI schema for AWS Bedrock Agent action group configuration.
    This schema should be uploaded to Bedrock when creating the action group.
    """
    schema = {
        "openapi": "3.0.0",
        "info": {
            "title": "Action Agent API",
            "description": "Identity & Access Management operations",
            "version": "1.0.0"
        },
        "paths": {
            "/": {
                "post": {
                    "summary": "Execute IAM actions",
                    "description": "Execute identity and access management operations",
                    "operationId": "executeAction",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/BedrockRequest"
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Successful operation",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/BedrockResponse"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "BedrockRequest": {
                    "type": "object",
                    "properties": {
                        "messageVersion": {"type": "string"},
                        "inputText": {"type": "string"},
                        "sessionId": {"type": "string"},
                        "actionGroup": {"type": "string"},
                        "function": {"type": "string"},
                        "parameters": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "type": {"type": "string"},
                                    "value": {"type": "string"}
                                }
                            }
                        }
                    }
                },
                "BedrockResponse": {
                    "type": "object",
                    "properties": {
                        "messageVersion": {"type": "string"},
                        "response": {
                            "type": "object",
                            "properties": {
                                "actionGroup": {"type": "string"},
                                "function": {"type": "string"},
                                "functionResponse": {
                                    "type": "object",
                                    "properties": {
                                        "responseBody": {
                                            "type": "object",
                                            "properties": {
                                                "TEXT": {
                                                    "type": "object",
                                                    "properties": {
                                                        "body": {"type": "string"}
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    return JSONResponse(content=schema)


# -------------------------------------------------------------------
# Start server
# -------------------------------------------------------------------

if __name__ == "__main__":
    host = os.getenv("BEDROCK_HOST", "0.0.0.0")
    port = int(os.getenv("BEDROCK_PORT", "8080"))

    print(f"\n╔═══════════════════════════════════════════════════════════╗")
    print(f"║  Action Agent for AWS Bedrock Agentcore                   ║")
    print(f"╚═══════════════════════════════════════════════════════════╝")
    print(f"\n🌐 API Endpoint: http://{host}:{port}")
    print(f"🏥 Health Check: http://{host}:{port}/health")
    print(f"📋 OpenAPI Schema: http://{host}:{port}/schema")
    #print(f"🔐 PingOne MCP: {PINGONE_MCP_URL}")
    print(f"📊 MS Graph MCP: {MSGRAPH_MCP_URL}")
    print(f"🔧 Tools loaded: {len(all_tools)}")
    print(f"\n💡 Deploy as containerized API - No Lambda required!")
    print(f"   Configure Bedrock Agent action group to call this endpoint\n")

    uvicorn.run(app, host=host, port=port)
