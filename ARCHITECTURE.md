# Action Agent - Architecture Documentation

## System Overview

The Action Agent is the execution component of the Identity-Aware AI Access Broker multi-agent system. It serves as the bridge between high-level identity management requests and actual operations on identity systems.

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Identity-Aware AI Access Broker              │
│                         (Multi-Agent System)                     │
└─────────────────────────────────────────────────────────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐      ┌─────────────────┐     ┌─────────────────┐
│   Chat Agent    │      │  Policy Agent   │     │  Action Agent   │
│ (user input)    │──A2A─▶  (validation)   │     │ (THIS COMPONENT)│
│                 │      │                 │     │    (A2A Server) │
└─────────┬───────┘      └─────────────────┘     └────────┬────────┘
          │                                               │
          │                                               │
          └──────────────A2A Protocol─────────────────────┘
                                                           │
                              ┌────────────────────────────┼────────────┐
                              │                            │            │
                              ▼                            ▼            ▼
                    ┌──────────────────┐        ┌──────────────────┐  ...
                    │  PingOne MCP     │        │ MS Graph MCP     │
                    │     Server       │        │     Server       │
                    └────────┬─────────┘        └────────┬─────────┘
                             │                           │
                             ▼                           ▼
                    ┌──────────────────┐        ┌──────────────────┐
                    │  PingOne API     │        │ Microsoft Graph  │
                    │                  │        │      API         │
                    └──────────────────┘        └──────────────────┘
```

## Core Components

### 1. ActionAgent Class

The main class that encapsulates all functionality:

```python
class ActionAgent:
    - __init__(model_provider, model_id, temperature, name, version)
    - _initialize_mcp_clients()
    - _initialize_agent()
    - _initialize_a2a_server()
    - execute(instruction) -> str
    - execute_async(instruction) -> str
    - serve(host, port, http_url)
```

**Responsibilities:**
- Initialize and manage MCP client connections
- Configure the Strands agent with appropriate tools
- Expose A2A server for inter-agent communication
- Execute instructions from Chat Agent via A2A protocol
- Coordinate between multiple identity systems

### 2. MCP Client Management

Two primary MCP clients are maintained:

**PingOne MCP Client:**
- Connects to PingOne identity platform
- Provides CRUD operations for users, groups, roles
- Handles PingOne-specific identity operations

**Microsoft Graph MCP Client:**
- Connects to Microsoft 365 via Graph API
- Manages users, groups, licenses, SharePoint, Teams
- Handles Microsoft-specific access operations

### 3. Built-in Tools

**log_action Tool:**
```python
@tool
def log_action(action, target, result, details):
    # Logs all actions for audit compliance
    # In production: writes to secure audit log
```

**validate_request Tool:**
```python
@tool
def validate_request(request_type, request_data):
    # Validates request structure before execution
    # Ensures required fields are present
```

### 4. Model Provider Abstraction

Supports multiple LLM providers through Strands SDK:
- AWS Bedrock (default: Nova Pro)
- Anthropic Claude
- OpenAI GPT
- Google Gemini
- Ollama (local)

## Data Flow

### Typical Request Flow

```
1. User → Chat Agent
   │
   └─▶ User inputs natural language request
       │
       ▼
2. Chat Agent
   │
   ├─▶ Processes conversational context
   ├─▶ Determines need for identity operations
   └─▶ Sends to Action Agent via A2A
       │
       ▼
3. Action Agent (receives via A2A)
   │
   ├─▶ Validates request structure
   ├─▶ Loads appropriate MCP tools
   └─▶ LLM determines execution plan
       │
       ▼
4. MCP Server(s)
   │
   ├─▶ Executes API calls
   ├─▶ Handles authentication
   └─▶ Returns results
       │
       ▼
5. Action Agent
   │
   ├─▶ Logs all actions
   ├─▶ Aggregates results
   └─▶ Returns to Chat Agent via A2A
       │
       ▼
6. Chat Agent
   │
   └─▶ Formats user-friendly response
```

### Example: New Employee Onboarding

```
User: "I need to onboard Sarah Johnson as a Marketing Manager"
    │
    ▼
Chat Agent: (via A2A to Action Agent)
    "Create user sarah.johnson@example.com with role Marketing Manager,
     assign to Marketing Team, grant E3 license"
    │
    ▼
Action Agent:
    │
    ├─▶ validate_request("create_user", {...})
    │   └─▶ ✓ Valid
    │
    ├─▶ PingOne MCP: create_user(...)
    │   └─▶ ✓ User created (user_id: abc123)
    │
    ├─▶ MS Graph MCP: create_user(...)
    │   └─▶ ✓ User created (user_id: xyz789)
    │
    ├─▶ MS Graph MCP: assign_license("E3")
    │   └─▶ ✓ License assigned
    │
    ├─▶ MS Graph MCP: add_to_group("Marketing Team")
    │   └─▶ ✓ Added to group
    │
    └─▶ log_action("onboard", "sarah.johnson@...", "success")
        └─▶ ✓ Logged
    │
    ▼ (Returns via A2A)
Chat Agent: "✓ Successfully onboarded Sarah Johnson!
            Created accounts in PingOne and Microsoft 365,
            assigned to Marketing Team, granted E3 license."
```

## Security Architecture

### Authentication & Authorization

1. **MCP Server Authentication:**
   - Each MCP server handles its own authentication
   - Credentials stored securely (AWS Secrets Manager, etc.)
   - No credentials in Action Agent code

2. **Request Validation:**
   - All requests validated before execution
   - Required fields checked
   - Request types must match known patterns

3. **Audit Logging:**
   - All actions logged with:
     - Action type
     - Target resource
     - Result (success/failure)
     - Timestamp
     - Requester (from Coordinator)
     - Approval ID (if applicable)

### Least Privilege Principle

- MCP servers run with minimal required permissions
- Action Agent cannot modify its own configuration
- No direct database access (only through MCP servers)

## Scalability Considerations

### Async Execution

The agent supports asynchronous execution for high-throughput scenarios:

```python
# Multiple requests in parallel
tasks = [
    agent.execute_async("Create user A"),
    agent.execute_async("Create user B"),
    agent.execute_async("Create user C")
]
results = await asyncio.gather(*tasks)
```

### Connection Pooling

MCP clients support connection pooling for efficient resource usage:

```python
# Reuse connections across requests
with pingone_client, msgraph_client:
    for instruction in instructions:
        result = agent.execute(instruction)
```

### Error Handling

Robust error handling at multiple levels:

1. **Request Validation:** Catch malformed requests early
2. **MCP Client Errors:** Handle API failures gracefully
3. **LLM Errors:** Retry with exponential backoff
4. **Logging Errors:** Ensure audit trail even on failure

## Integration Points

### With Chat Agent (A2A Protocol)

**Chat Agent Setup:**
```python
from strands import Agent
from strands_tools.a2a_client import A2AClientToolProvider

# Connect to Action Agent
a2a_provider = A2AClientToolProvider(
    known_agent_urls=["http://127.0.0.1:9000"]
)

# Chat Agent automatically gets Action Agent tools
chat_agent = Agent(
    name="Chat Agent",
    tools=a2a_provider.tools
)
```

**Communication Flow:**
1. Chat Agent receives user input
2. Chat Agent sends natural language request to Action Agent via A2A
3. Action Agent executes operations via MCP servers
4. Action Agent returns structured results via A2A
5. Chat Agent formats user-friendly response

**A2A Message Format:**
The A2A protocol handles message serialization automatically. Chat Agent sends natural language text, and Action Agent responds with execution results.

### With Policy Agent

While Action Agent doesn't directly interact with Policy Agent, it respects policy decisions by:
- Only executing approved requests
- Validating approval IDs
- Logging for policy audit trails

## Configuration Management

### Environment-Based Configuration

All configuration through environment variables:
- `MODEL_PROVIDER`: Which LLM to use
- `MODEL_ID`: Specific model version
- `MODEL_TEMPERATURE`: LLM temperature setting
- `PINGONE_MCP_*`: PingOne MCP server config
- `MSGRAPH_MCP_*`: MS Graph MCP server config

### Secrets Management

Credentials never in code:
- AWS credentials from IAM roles or ~/.aws/credentials
- API keys from environment or secret managers
- MCP servers handle their own credential management

## Future Enhancements

### Planned Features

1. **Additional MCP Servers:**
   - BeyondTrust MCP Server
   - Cloudflare MCP Server
   - Generic SCIM MCP Server

2. **Advanced Logging:**
   - Structured logging with correlation IDs
   - Integration with SIEM systems
   - Real-time alerting on failures

3. **Rollback Capabilities:**
   - Automatic rollback on partial failures
   - Compensation transactions
   - State checkpointing

4. **Performance Optimizations:**
   - Request batching
   - Caching of frequently accessed data
   - Predictive pre-loading of MCP tools

## Testing Strategy

### Unit Tests

- Test each tool independently
- Mock MCP server responses
- Validate request validation logic

### Integration Tests

- Test with actual MCP servers (dev environment)
- End-to-end flows
- Error scenarios

### Performance Tests

- Load testing with concurrent requests
- MCP connection pool efficiency
- LLM response time benchmarks

## Deployment

### Prerequisites

- Python 3.9+ runtime
- Access to LLM provider (AWS Bedrock, etc.)
- PingOne and Microsoft Graph credentials
- MCP servers deployed and accessible

### Deployment Options

1. **Standalone Process:** Run as independent Python process
2. **Container:** Deploy as Docker container
3. **Serverless:** AWS Lambda with longer timeout
4. **Kubernetes:** For high availability and scaling

## Monitoring & Observability

### Key Metrics

- Request success/failure rates
- MCP server response times
- LLM token usage and costs
- Queue depths (if async)
- Error rates by type

### Health Checks

- MCP server connectivity
- LLM provider availability
- Tool discovery success
- Recent request success rate

## Conclusion

The Action Agent is designed as a robust, scalable, and secure execution engine for identity operations. Its architecture emphasizes:

- **Separation of Concerns:** Clear boundaries between orchestration and execution
- **Security First:** Audit logging, request validation, least privilege
- **Flexibility:** Multiple LLM providers, extensible MCP architecture
- **Reliability:** Error handling, async support, comprehensive testing
