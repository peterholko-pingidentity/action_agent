# Action Agent - Identity & Access Management Executor

The Action Agent is a component of the Identity-Aware AI Access Broker multi-agent system. It handles the execution of identity and access management operations across PingOne and Microsoft 365 environments.

## Overview

The Action Agent receives conversational context from a Chat Agent via A2A (Agent-to-Agent) protocol and executes identity operations through MCP (Model Context Protocol) servers:

- **PingOne MCP Server**: Manages PingOne identity operations
- **Microsoft Graph MCP Server**: Manages Microsoft 365 identity and access operations

## Architecture

```
┌──────────────┐
│  User Input  │
└──────┬───────┘
       │
       ▼
┌─────────────────────┐
│   Chat Agent        │
│ (user interaction)  │
└──────────┬──────────┘
           │
           │ A2A Protocol
           ▼
┌─────────────────────┐
│   Action Agent      │
│  (this component)   │
└─────┬─────────┬─────┘
      │         │
      │         │ MCP Protocol
      ▼         ▼
┌─────────┐ ┌──────────────┐
│ PingOne │ │ MS Graph MCP │
│   MCP   │ │    Server    │
└─────────┘ └──────────────┘
```

## Features

- **A2A Protocol**: Exposes as A2A server for inter-agent communication
- **Multi-System Integration**: Seamlessly operates across PingOne and Microsoft 365
- **Model-Agnostic**: Supports AWS Bedrock, Anthropic, OpenAI, and other LLM providers
- **MCP Native**: Direct integration with MCP servers for tool discovery
- **Audit Logging**: Built-in logging of all actions for compliance
- **Request Validation**: Pre-execution validation of requests

## Installation

### Prerequisites

- Python 3.9+
- Access to PingOne and Microsoft Graph APIs
- AWS credentials (if using Bedrock) or API keys for other providers

### Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd action_agent
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Set up MCP servers**:

   You'll need to set up the PingOne and Microsoft Graph MCP servers. These are typically installed as separate packages:

   ```bash
   # Example - actual commands depend on MCP server implementations
   uvx pingone-mcp-server
   uvx msgraph-mcp-server
   ```

5. **Start the Action Agent A2A server**:

   ```bash
   python action_agent.py
   ```

   This starts the A2A server on `http://127.0.0.1:9000` (configurable via environment variables)

## Configuration

Edit the `.env` file to configure your Action Agent:

```env
# Model Provider (bedrock, anthropic, openai)
MODEL_PROVIDER=bedrock
MODEL_ID=us.amazon.nova-pro-v1:0
MODEL_TEMPERATURE=0.3

# AWS Configuration (for Bedrock)
AWS_REGION=us-east-1
AWS_PROFILE=default

# A2A Server Configuration
A2A_HOST=127.0.0.1
A2A_PORT=9000
# A2A_HTTP_URL=https://action-agent.example.com  # Optional

# MCP Server Commands
PINGONE_MCP_COMMAND=uvx
PINGONE_MCP_ARGS=pingone-mcp-server

MSGRAPH_MCP_COMMAND=uvx
MSGRAPH_MCP_ARGS=msgraph-mcp-server
```

## Usage

### Starting the Action Agent Server

```bash
# Start the A2A server
python action_agent.py
```

The Action Agent will start an A2A server and wait for requests from the Chat Agent.

### Chat Agent Integration (A2A Client)

The Chat Agent communicates with the Action Agent using A2A protocol:

```python
from strands import Agent
from strands_tools.a2a_client import A2AClientToolProvider

# Connect to Action Agent
a2a_provider = A2AClientToolProvider(
    known_agent_urls=["http://127.0.0.1:9000"]
)

# Create Chat Agent with Action Agent tools
chat_agent = Agent(
    name="Chat Agent",
    tools=a2a_provider.tools,
    system_prompt="You help users with identity and access management..."
)

# User request flows through Chat Agent to Action Agent
response = await chat_agent.async_call(
    "Create user john.doe@example.com for the Sales team"
)
```

See `chat_agent_example.py` for complete examples.

### Example Instructions

The Action Agent can handle various identity management tasks:

```python
# User Creation
agent.execute("Create user jane.smith@example.com in PingOne")

# Group Assignment
agent.execute("Add user john.doe@example.com to the Sales group in Microsoft 365")

# Access Grant
agent.execute("Grant user jane.smith@example.com access to SharePoint Sales site")

# License Assignment
agent.execute("Assign Microsoft 365 E5 license to john.doe@example.com")

# Role Assignment
agent.execute("Assign Directory Reader role to service account")
```

### Async Usage

For better performance in high-throughput scenarios:

```python
import asyncio
from action_agent import ActionAgent

async def main():
    agent = ActionAgent()
    response = await agent.execute_async(
        "Create user and assign to default groups"
    )
    print(response)

asyncio.run(main())
```

## Integration with Coordinator Agent

The Action Agent is designed to receive signed execution instructions from the Coordinator Agent:

```python
# Example from Coordinator Agent side
instruction = {
    "action": "create_user",
    "target_system": "pingone",
    "parameters": {
        "email": "new.employee@example.com",
        "first_name": "New",
        "last_name": "Employee",
        "role": "Sales Representative"
    },
    "requester": "hr@example.com",
    "approval_id": "APR-12345"
}

# Coordinator sends to Action Agent
response = action_agent.execute(
    f"Execute: {instruction}"
)
```

## Built-in Tools

The Action Agent includes several built-in tools:

### log_action

Logs all actions for audit purposes:

```python
log_action(
    action="create_user",
    target="john.doe@example.com",
    result="success",
    details={"system": "pingone", "user_id": "usr_123"}
)
```

### validate_request

Validates requests before execution:

```python
validate_request(
    request_type="create_user",
    request_data={
        "email": "john.doe@example.com",
        "first_name": "John",
        "last_name": "Doe"
    }
)
```

## Security Considerations

- **Authentication**: Ensure MCP servers are properly authenticated
- **Authorization**: Validate that requests come from authorized Coordinator Agents
- **Audit Logging**: All actions are logged for compliance
- **Least Privilege**: MCP servers should operate with minimal required permissions
- **Encryption**: Use encrypted connections for all MCP communications

## Troubleshooting

### MCP Server Connection Issues

If you encounter connection issues with MCP servers:

1. Verify MCP servers are running:
   ```bash
   ps aux | grep mcp-server
   ```

2. Check MCP server logs for errors

3. Verify environment variables are set correctly

### Model Provider Issues

For AWS Bedrock:
- Ensure AWS credentials are configured
- Verify model access is granted in AWS console
- Check region settings

For Anthropic/OpenAI:
- Verify API keys are set correctly
- Check rate limits and quotas

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

```bash
black action_agent.py
flake8 action_agent.py
```

## Related Components

This Action Agent works as part of the larger Identity-Aware AI Access Broker system:

- **Coordinator Agent**: Orchestrates workflows and sends instructions to Action Agent
- **Policy Agent**: Evaluates policies and triggers human-in-the-loop approvals
- **PingOne MCP Server**: Provides PingOne identity operations
- **Microsoft Graph MCP Server**: Provides Microsoft 365 operations

## License

[Your License Here]

## Support

For issues and questions, please open an issue in the repository.
