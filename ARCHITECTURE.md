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
│  Coordinator    │      │  Policy Agent   │     │  Action Agent   │
│     Agent       │─────▶│  (validation)   │────▶│ (THIS COMPONENT)│
│ (orchestration) │      │                 │     │                 │
└─────────────────┘      └─────────────────┘     └────────┬────────┘
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
    - __init__(model_provider, model_id, temperature)
    - _initialize_mcp_clients()
    - _initialize_agent()
    - execute(instruction) -> str
    - execute_async(instruction) -> str
```

**Responsibilities:**
- Initialize and manage MCP client connections
- Configure the Strands agent with appropriate tools
- Execute instructions synchronously or asynchronously
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
1. Coordinator Agent
   │
   ├─▶ Validates requester identity
   ├─▶ Consults Policy Agent
   └─▶ Gets approvals (if needed)
       │
       ▼
2. Action Agent (receives instruction)
   │
   ├─▶ Validates request structure
   ├─▶ Loads appropriate MCP tools
   └─▶ LLM determines execution plan
       │
       ▼
3. MCP Server(s)
   │
   ├─▶ Executes API calls
   ├─▶ Handles authentication
   └─▶ Returns results
       │
       ▼
4. Action Agent
   │
   ├─▶ Logs all actions
   ├─▶ Aggregates results
   └─▶ Returns to Coordinator
```

### Example: New Employee Onboarding

```
Coordinator: "Onboard new.employee@example.com as Sales Rep"
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
    ├─▶ MS Graph MCP: add_to_group("Sales Team")
    │   └─▶ ✓ Added to group
    │
    └─▶ log_action("onboard", "new.employee@...", "success")
        └─▶ ✓ Logged

    Returns: "Successfully onboarded new.employee@example.com"
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

### With Coordinator Agent

**Input Format:**
```json
{
  "request_id": "REQ-2024-001",
  "requester": "hr@example.com",
  "approval_id": "APR-2024-123",
  "action": "onboard_employee",
  "parameters": {...},
  "signature": "cryptographic_signature"
}
```

**Output Format:**
```json
{
  "request_id": "REQ-2024-001",
  "status": "success",
  "actions_taken": [
    {
      "action": "create_user",
      "system": "pingone",
      "result": "success",
      "resource_id": "usr_abc123"
    }
  ],
  "timestamp": "2024-01-15T10:35:00Z"
}
```

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
