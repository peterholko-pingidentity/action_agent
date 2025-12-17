"""
Action Agent - Identity & Access Management Executor

This agent handles identity and access management operations by interfacing with:
- PingOne MCP Server: For PingOne identity operations (TO BE ADDED)
- Microsoft Graph MCP Server: For Microsoft 365 identity and access operations (TO BE ADDED)

The Action Agent receives conversational context from a Chat Agent via A2A protocol
and executes the necessary operations across identity systems.

Architecture:
  Chat Agent (user input) → [A2A Protocol] → Action Agent → MCP Servers → Results
"""

import os
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv

from strands import Agent, tool
from strands.multiagent.a2a import A2AServer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ActionAgent:
    """
    Action Agent for executing identity and access management operations.

    This agent integrates with PingOne and Microsoft Graph via MCP servers
    to perform CRUD operations on identities, groups, roles, and access policies.

    The agent is exposed via A2A protocol to receive requests from a Chat Agent.
    """

    def __init__(
        self,
        model_provider: str = "bedrock",
        model_id: Optional[str] = None,
        temperature: float = 0.3,
        name: str = "Action Agent",
        version: str = "1.0.0",
        description: str = "An identity and access management executor that performs operations on PingOne and Microsoft Graph"
    ):
        """
        Initialize the Action Agent with model configuration.

        Args:
            model_provider: The LLM provider to use (bedrock, anthropic, openai, etc.)
            model_id: The specific model ID to use
            temperature: Temperature setting for model responses
            name: Name of the agent for A2A identification
            version: Version of the agent for A2A
            description: Description of the agent's capabilities
        """
        self.model_provider = model_provider
        self.model_id = model_id or os.getenv("MODEL_ID", "us.amazon.nova-pro-v1:0")
        self.temperature = temperature
        self.name = name
        self.version = version
        self.description = description

        self.agent = None
        self.a2a_server = None

        self._initialize_agent()
        self._initialize_a2a_server()

    def _initialize_agent(self):
        """Initialize the Strands agent with tools."""

        # Collect all tools
        all_tools = []

        # Add custom tools for coordination and logging
        all_tools.extend([
            self._create_log_action_tool(),
            self._create_validate_request_tool()
        ])

        # TODO: Add MCP tools here when PingOne and Microsoft Graph MCP servers are ready
        # Example:
        # pingone_tools = pingone_mcp_client.list_tools_sync()
        # msgraph_tools = msgraph_mcp_client.list_tools_sync()
        # all_tools.extend(pingone_tools)
        # all_tools.extend(msgraph_tools)

        # System prompt for the Action Agent
        system_prompt = """You are the Action Agent, an identity and access management executor.

Your role:
- Receive conversational context from a Chat Agent about identity operations
- Execute identity operations via PingOne and Microsoft Graph MCP servers
- Validate requests before execution
- Log all actions for audit compliance
- Return clear, concise results

Available systems (will be available when MCP servers are connected):
- PingOne: User management, groups, roles, authentication policies
- Microsoft Graph: Microsoft 365 users, groups, licenses, SharePoint, Teams

Always:
1. Validate requests before executing
2. Log all actions with appropriate details
3. Provide clear success/failure messages
4. Include relevant resource IDs in responses

For now, you can respond to requests and demonstrate your capabilities, but actual
identity operations will be available once the MCP servers are connected.
"""

        # Initialize the Strands agent
        if self.model_provider == "bedrock":
            from strands.models import BedrockModel
            model = BedrockModel(
                model_id=self.model_id,
                temperature=self.temperature,
                streaming=True
            )
            self.agent = Agent(
                name=self.name,
                description=self.description,
                model=model,
                tools=all_tools,
                system_prompt=system_prompt
            )
        else:
            # Use default model provider
            self.agent = Agent(
                name=self.name,
                description=self.description,
                tools=all_tools,
                system_prompt=system_prompt
            )

        logger.info(f"✓ Initialized {self.name} with {len(all_tools)} tools")

    def _initialize_a2a_server(self):
        """Initialize the A2A server to expose this agent for inter-agent communication."""

        # Create A2A server with the agent
        self.a2a_server = A2AServer(
            agent=self.agent,
            version=self.version
        )

        logger.info(f"✓ Initialized A2A server (version {self.version})")

    @staticmethod
    def _create_log_action_tool():
        """Create a tool for logging actions taken by the agent."""

        @tool
        def log_action(action: str, target: str, result: str, details: Dict[str, Any] = None) -> str:
            """
            Log an action performed by the Action Agent.

            Args:
                action: The action performed (e.g., 'create_user', 'assign_group')
                target: The target resource (e.g., user email, group name)
                result: The result of the action ('success', 'failure', 'pending')
                details: Additional details about the action

            Returns:
                Confirmation message
            """
            log_entry = {
                "action": action,
                "target": target,
                "result": result,
                "details": details or {}
            }
            # In production, this would write to a proper audit log
            logger.info(f"[ACTION LOG] {log_entry}")
            return f"Action logged: {action} on {target} - {result}"

        return log_action

    @staticmethod
    def _create_validate_request_tool():
        """Create a tool for validating requests before execution."""

        @tool
        def validate_request(request_type: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
            """
            Validate a request before executing it.

            Args:
                request_type: Type of request (e.g., 'create_user', 'grant_access')
                request_data: Data for the request

            Returns:
                Validation result with status and any errors
            """
            # Basic validation logic
            required_fields = {
                "create_user": ["email", "first_name", "last_name"],
                "grant_access": ["user_id", "resource_id"],
                "assign_group": ["user_id", "group_id"],
                "assign_license": ["user_id", "license_type"]
            }

            if request_type not in required_fields:
                return {
                    "valid": False,
                    "error": f"Unknown request type: {request_type}"
                }

            missing_fields = [
                field for field in required_fields[request_type]
                if field not in request_data
            ]

            if missing_fields:
                return {
                    "valid": False,
                    "error": f"Missing required fields: {', '.join(missing_fields)}"
                }

            return {
                "valid": True,
                "message": "Request validation passed"
            }

        return validate_request

    def serve(
        self,
        host: str = "127.0.0.1",
        port: int = 9000,
        http_url: Optional[str] = None
    ):
        """
        Start the A2A server to accept requests from Chat Agent.

        Args:
            host: Host address to bind to
            port: Port number to listen on
            http_url: Public URL for external access (optional)
        """
        if not self.a2a_server:
            raise RuntimeError("A2A server not initialized")

        print("\n" + "=" * 70)
        print(f"  {self.name} - A2A Server")
        print("=" * 70)
        print(f"\n  Version: {self.version}")
        print(f"  Address: http://{host}:{port}")
        if http_url:
            print(f"  Public URL: {http_url}")
        print(f"\n  Status: Ready to receive requests from Chat Agent")
        print(f"\n  Available capabilities:")
        print(f"    • Request validation")
        print(f"    • Action logging and audit trail")
        print(f"    • Conversational interface")
        print(f"\n  Pending integrations:")
        print(f"    ○ PingOne MCP Server (in development)")
        print(f"    ○ Microsoft Graph MCP Server (in development)")
        print("\n" + "=" * 70)
        print(f"  Listening for A2A requests...")
        print("=" * 70 + "\n")

        # Start the A2A server
        self.a2a_server.serve(host=host, port=port, http_url=http_url)


def main():
    """
    Main entry point for the Action Agent.

    Starts the A2A server to receive requests from Chat Agent.
    """
    # Get configuration from environment
    host = os.getenv("A2A_HOST", "127.0.0.1")
    port = int(os.getenv("A2A_PORT", "9000"))
    http_url = os.getenv("A2A_HTTP_URL")

    # Create and start the Action Agent
    action_agent = ActionAgent(
        model_provider=os.getenv("MODEL_PROVIDER", "bedrock"),
        model_id=os.getenv("MODEL_ID"),
        temperature=float(os.getenv("MODEL_TEMPERATURE", "0.3")),
        name="Action Agent",
        version="1.0.0"
    )

    # Start the A2A server
    action_agent.serve(host=host, port=port, http_url=http_url)


if __name__ == "__main__":
    main()
