# AWS Bedrock AgentCore Deployment Guide

This guide explains how to deploy the Action Agent to AWS Bedrock AgentCore Runtime.

## Overview

The Action Agent can be deployed in two modes:
1. **A2A Server Mode** - For local development and testing
2. **Bedrock AgentCore Runtime Mode** - For production deployment on AWS

## Prerequisites

1. AWS Account with Bedrock AgentCore access
2. AWS CLI configured with appropriate credentials
3. Python 3.11 or later
4. Bedrock AgentCore Starter Toolkit

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Bedrock AgentCore Starter Toolkit

```bash
pip install bedrock-agentcore-starter-toolkit
```

## Deployment to Bedrock AgentCore

### Method 1: Using the Starter Toolkit (Recommended)

1. **Configure the deployment**:
   ```bash
   agentcore configure --entrypoint action_agent.py
   ```

2. **Set environment variables**:
   ```bash
   export MSGRAPH_MCP_URL="http://your-mcp-server-url:8000/mcp"
   ```

3. **Deploy to AWS**:
   ```bash
   agentcore launch
   ```

4. **Test the deployment**:
   ```bash
   agentcore invoke '{"prompt": "List all users in the organization"}'
   ```

### Method 2: Manual Lambda Deployment

1. **Package the application**:
   ```bash
   mkdir package
   pip install -r requirements.txt -t package/
   cp action_agent.py package/
   cd package
   zip -r ../action_agent.zip .
   cd ..
   ```

2. **Create Lambda function** (using AWS CLI):
   ```bash
   aws lambda create-function \
     --function-name action-agent \
     --runtime python3.11 \
     --handler action_agent.lambda_handler \
     --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-execution-role \
     --zip-file fileb://action_agent.zip \
     --environment Variables="{MSGRAPH_MCP_URL=http://your-mcp-url:8000/mcp,DEPLOYMENT_MODE=agentcore}" \
     --timeout 300 \
     --memory-size 512
   ```

3. **Create Bedrock AgentCore Runtime** and link it to the Lambda function through the AWS Console or CLI.

## Local Development (A2A Server Mode)

For local testing without deploying to AWS:

```bash
# Set to A2A mode (default)
export DEPLOYMENT_MODE=a2a
export MSGRAPH_MCP_URL="http://localhost:8000/mcp"

# Run the server
python action_agent.py
```

The A2A server will start on `http://127.0.0.1:9000`

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEPLOYMENT_MODE` | Deployment mode: `a2a` or `agentcore` | `a2a` |
| `MSGRAPH_MCP_URL` | Microsoft Graph MCP server URL | `http://100.28.229.240:8000/mcp` |
| `A2A_HOST` | A2A server host (A2A mode only) | `127.0.0.1` |
| `A2A_PORT` | A2A server port (A2A mode only) | `9000` |

## Testing the Deployed Agent

### Using the Bedrock AgentCore Runtime

```python
import boto3

client = boto3.client('bedrock-agentcore-runtime')

response = client.invoke_agent(
    agentId='your-agent-id',
    agentAliasId='your-alias-id',
    sessionId='test-session-123',
    inputText='Create a new user with email john.doe@example.com'
)

print(response)
```

### Using the agentcore CLI

```bash
agentcore invoke '{"prompt": "Create a user named John Doe with email john.doe@example.com"}'
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  AWS Bedrock AgentCore                  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │           Lambda Function (Action Agent)         │  │
│  │                                                  │  │
│  │  • Strands Agent Framework                      │  │
│  │  • MCP Tool Integration                         │  │
│  │  • Identity & Access Management Logic           │  │
│  └──────────────────────────────────────────────────┘  │
│                          │                              │
└──────────────────────────┼──────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   MCP Servers          │
              ├────────────────────────┤
              │ • Microsoft Graph MCP  │
              │ • PingOne MCP          │
              └────────────────────────┘
```

## Monitoring and Logs

View logs in CloudWatch:
```bash
aws logs tail /aws/lambda/action-agent --follow
```

Or use the agentcore CLI:
```bash
agentcore logs --follow
```

## Troubleshooting

### Common Issues

1. **MCP Connection Timeout**:
   - Ensure the MCP server URL is accessible from Lambda
   - If MCP servers are in a VPC, configure Lambda VPC settings
   - Check security groups and network ACLs

2. **Lambda Cold Start**:
   - The first invocation may be slow due to MCP client initialization
   - Consider using Lambda provisioned concurrency for production

3. **Import Errors**:
   - Ensure all dependencies are included in the deployment package
   - Verify Python version compatibility (3.11+)

## Security Considerations

1. **Environment Variables**: Use AWS Secrets Manager for sensitive credentials
2. **IAM Roles**: Follow principle of least privilege
3. **VPC Configuration**: Deploy in VPC if accessing internal resources
4. **Encryption**: Enable encryption at rest and in transit

## Additional Resources

- [AWS Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
- [Strands Agents Documentation](https://strandsagents.com/)
- [Bedrock AgentCore Starter Toolkit](https://github.com/aws/bedrock-agentcore-starter-toolkit)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
