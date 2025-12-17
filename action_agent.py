"""
Action Agent - Identity & Access Management Executor

This agent handles identity and access management operations by interfacing with:
- PingOne MCP Server: For PingOne identity operations
- Microsoft Graph MCP Server: For Microsoft 365 identity and access operations

The Action Agent receives instructions from the Coordinator Agent and executes
the necessary operations across identity systems.
"""

import os
import asyncio
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

from strands import Agent, tool
from strands.tools.mcp import MCPClient
from mcp import stdio_client, StdioServerParameters


# Load environment variables
load_dotenv()


class ActionAgent:
    """
    Action Agent for executing identity and access management operations.

    This agent integrates with PingOne and Microsoft Graph via MCP servers
    to perform CRUD operations on identities, groups, roles, and access policies.
    """

    def __init__(
        self,
        model_provider: str = "bedrock",
        model_id: Optional[str] = None,
        temperature: float = 0.3
    ):
        """
        Initialize the Action Agent with model configuration and MCP clients.

        Args:
            model_provider: The LLM provider to use (bedrock, anthropic, openai, etc.)
            model_id: The specific model ID to use
            temperature: Temperature setting for model responses
        """
        self.model_provider = model_provider
        self.model_id = model_id or os.getenv("MODEL_ID", "us.amazon.nova-pro-v1:0")
        self.temperature = temperature

        # Initialize MCP clients
        self.pingone_client = None
        self.msgraph_client = None
        self.agent = None

        self._initialize_mcp_clients()
        self._initialize_agent()

    def _initialize_mcp_clients(self):
        """Initialize MCP clients for PingOne and Microsoft Graph."""

        # PingOne MCP Client
        pingone_command = os.getenv("PINGONE_MCP_COMMAND", "uvx")
        pingone_args = os.getenv("PINGONE_MCP_ARGS", "pingone-mcp-server").split()

        self.pingone_client = MCPClient(
            lambda: stdio_client(StdioServerParameters(
                command=pingone_command,
                args=pingone_args
            ))
        )

        # Microsoft Graph MCP Client
        msgraph_command = os.getenv("MSGRAPH_MCP_COMMAND", "uvx")
        msgraph_args = os.getenv("MSGRAPH_MCP_ARGS", "msgraph-mcp-server").split()

        self.msgraph_client = MCPClient(
            lambda: stdio_client(StdioServerParameters(
                command=msgraph_command,
                args=msgraph_args
            ))
        )

    def _initialize_agent(self):
        """Initialize the Strands agent with tools from MCP servers."""

        # Collect all tools from MCP servers
        all_tools = []

        # Add custom tools for coordination and logging
        all_tools.extend([
            self._create_log_action_tool(),
            self._create_validate_request_tool()
        ])

        # Initialize the Strands agent
        if self.model_provider == "bedrock":
            from strands.models import BedrockModel
            model = BedrockModel(
                model_id=self.model_id,
                temperature=self.temperature,
                streaming=True
            )
            self.agent = Agent(model=model, tools=all_tools)
        else:
            # Use default model provider
            self.agent = Agent(tools=all_tools)

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
            print(f"[ACTION LOG] {log_entry}")
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
                "assign_group": ["user_id", "group_id"]
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

    def execute(self, instruction: str) -> str:
        """
        Execute an instruction from the Coordinator Agent.

        Args:
            instruction: The instruction to execute (e.g., "Create user john.doe@example.com")

        Returns:
            Result of the execution
        """
        if not self.agent:
            return "Error: Agent not initialized"

        # Execute the instruction using the agent
        with self.pingone_client, self.msgraph_client:
            # Get tools from MCP servers
            pingone_tools = self.pingone_client.list_tools_sync()
            msgraph_tools = self.msgraph_client.list_tools_sync()

            # Add MCP tools to agent
            self.agent.tools.extend(pingone_tools)
            self.agent.tools.extend(msgraph_tools)

            # Execute instruction
            response = self.agent(instruction)

            return response

    async def execute_async(self, instruction: str) -> str:
        """
        Asynchronously execute an instruction from the Coordinator Agent.

        Args:
            instruction: The instruction to execute

        Returns:
            Result of the execution
        """
        if not self.agent:
            return "Error: Agent not initialized"

        # Execute the instruction asynchronously
        async with self.pingone_client, self.msgraph_client:
            # Get tools from MCP servers
            pingone_tools = await self.pingone_client.list_tools()
            msgraph_tools = await self.msgraph_client.list_tools()

            # Add MCP tools to agent
            self.agent.tools.extend(pingone_tools)
            self.agent.tools.extend(msgraph_tools)

            # Execute instruction
            response = await self.agent.async_call(instruction)

            return response


def main():
    """
    Main entry point for the Action Agent.

    This demonstrates basic usage of the Action Agent.
    """
    print("Initializing Action Agent...")

    # Create the Action Agent
    agent = ActionAgent(
        model_provider=os.getenv("MODEL_PROVIDER", "bedrock"),
        model_id=os.getenv("MODEL_ID"),
        temperature=float(os.getenv("MODEL_TEMPERATURE", "0.3"))
    )

    print("Action Agent initialized successfully!")
    print("\nAction Agent is ready to receive instructions from the Coordinator Agent.")
    print("\nExample instructions:")
    print("  - Create user john.doe@example.com in PingOne")
    print("  - Assign user to Sales group in Microsoft 365")
    print("  - Grant user access to SharePoint site")

    # Example usage (comment out in production)
    # response = agent.execute("List all available tools")
    # print(f"\nResponse: {response}")


if __name__ == "__main__":
    main()
