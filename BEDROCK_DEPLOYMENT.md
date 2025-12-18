# AWS Bedrock Agentcore Deployment Guide

This guide explains how to deploy the Action Agent on AWS Bedrock Agentcore **without using AWS Lambda**. The agent runs as a containerized REST API that Bedrock Agents can call directly.

## Architecture Overview

```
AWS Bedrock Agent
       ↓
   (HTTPS API Call)
       ↓
AWS App Runner / ECS / EKS
       ↓
Action Agent Container (FastAPI)
       ↓
MCP Servers (PingOne, MS Graph)
```

## Key Changes from A2A Version

- **Replaced**: A2A Server → FastAPI REST API
- **Added**: Bedrock Agent request/response format handlers
- **Added**: OpenAPI schema endpoint for Bedrock configuration
- **Added**: Health check endpoint for container orchestration
- **Port**: Changed from 9000 to 8080 (container standard)
- **Host**: Changed from 127.0.0.1 to 0.0.0.0 (for containerization)

## Prerequisites

1. AWS Account with Bedrock access
2. Docker installed locally (for building)
3. AWS CLI configured
4. Access to MCP servers (PingOne, MS Graph)

## Deployment Options

### Option 1: AWS App Runner (Recommended - Simplest)

AWS App Runner is the easiest way to deploy containerized applications without managing infrastructure.

#### Step 1: Build and Push Docker Image

```bash
# Build the Docker image
docker build -t action-agent-bedrock .

# Tag for ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Create ECR repository
aws ecr create-repository --repository-name action-agent-bedrock --region us-east-1

# Tag and push
docker tag action-agent-bedrock:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/action-agent-bedrock:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/action-agent-bedrock:latest
```

#### Step 2: Create App Runner Service

```bash
aws apprunner create-service \
  --service-name action-agent-bedrock \
  --source-configuration '{
    "ImageRepository": {
      "ImageIdentifier": "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/action-agent-bedrock:latest",
      "ImageRepositoryType": "ECR",
      "ImageConfiguration": {
        "Port": "8080",
        "RuntimeEnvironmentVariables": {
          "MSGRAPH_MCP_URL": "http://your-msgraph-mcp-server:8000/mcp"
        }
      }
    },
    "AutoDeploymentsEnabled": true
  }' \
  --instance-configuration '{
    "Cpu": "1 vCPU",
    "Memory": "2 GB"
  }' \
  --health-check-configuration '{
    "Protocol": "HTTP",
    "Path": "/health",
    "Interval": 10,
    "Timeout": 5,
    "HealthyThreshold": 1,
    "UnhealthyThreshold": 5
  }' \
  --region us-east-1
```

#### Step 3: Get the Service URL

```bash
aws apprunner list-services --region us-east-1
# Note the ServiceUrl from the output
```

### Option 2: AWS ECS with Fargate

#### Step 1: Create ECS Task Definition

```json
{
  "family": "action-agent-bedrock",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "action-agent",
      "image": "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/action-agent-bedrock:latest",
      "portMappings": [
        {
          "containerPort": 8080,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "MSGRAPH_MCP_URL",
          "value": "http://your-msgraph-mcp-server:8000/mcp"
        }
      ],
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      },
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/action-agent-bedrock",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

#### Step 2: Create ECS Service with ALB

```bash
# Create ALB target group
aws elbv2 create-target-group \
  --name action-agent-tg \
  --protocol HTTP \
  --port 8080 \
  --vpc-id YOUR_VPC_ID \
  --target-type ip \
  --health-check-path /health

# Create ECS service
aws ecs create-service \
  --cluster your-cluster \
  --service-name action-agent-bedrock \
  --task-definition action-agent-bedrock \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=action-agent,containerPort=8080"
```

### Option 3: AWS EKS (For Advanced Kubernetes Users)

See `k8s-deployment.yaml` for Kubernetes manifests.

## Configure AWS Bedrock Agent

### Step 1: Get OpenAPI Schema

```bash
# Get the schema from your deployed service
curl https://your-service-url/schema > action-agent-schema.json
```

### Step 2: Create Bedrock Agent

1. Go to AWS Bedrock Console → Agents
2. Click "Create Agent"
3. Configure basic settings:
   - Name: "IAM Action Agent"
   - Description: "Identity & Access Management operations"
   - Foundation model: Claude 3.5 Sonnet (or your preferred model)

### Step 3: Create Action Group

1. In your Bedrock Agent, click "Add Action Group"
2. Configure:
   - **Name**: `iam-actions`
   - **Action group type**: Define with API schemas
   - **Action group schema**: Upload the `action-agent-schema.json`
   - **Action group executor**: Select "Return control" or use a Lambda if you need additional orchestration
   - **API endpoint**: Enter your App Runner/ALB URL (e.g., `https://your-service.us-east-1.awsapprunner.com/`)

### Step 4: Configure Authentication (if needed)

If your API requires authentication:

1. Create an AWS Secrets Manager secret with API key
2. Configure the action group to use the secret

### Step 5: Test the Agent

1. Use the Bedrock Agent test console
2. Try commands like:
   - "Create a new user with email john@example.com"
   - "List all groups in our organization"
   - "Grant access to resource X for user Y"

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `BEDROCK_HOST` | Host to bind to | `0.0.0.0` | No |
| `BEDROCK_PORT` | Port to listen on | `8080` | No |
| `MSGRAPH_MCP_URL` | MS Graph MCP server URL | - | Yes |
| `PINGONE_MCP_URL` | PingOne MCP server URL | - | Optional |

## API Endpoints

### POST /
Main endpoint for Bedrock Agent action invocations.

**Request Format (sent by Bedrock)**:
```json
{
  "messageVersion": "1.0",
  "agent": {...},
  "inputText": "Create a user with email john@example.com",
  "sessionId": "session-123",
  "actionGroup": "iam-actions",
  "function": "create_user",
  "parameters": [
    {"name": "email", "type": "string", "value": "john@example.com"},
    {"name": "first_name", "type": "string", "value": "John"},
    {"name": "last_name", "type": "string", "value": "Doe"}
  ]
}
```

**Response Format**:
```json
{
  "messageVersion": "1.0",
  "response": {
    "actionGroup": "iam-actions",
    "function": "create_user",
    "functionResponse": {
      "responseBody": {
        "TEXT": {
          "body": "User created successfully with ID: user-123"
        }
      }
    }
  }
}
```

### GET /health
Health check endpoint for container orchestration.

**Response**:
```json
{
  "status": "healthy",
  "tools": 10,
  "msgraph_mcp": "http://msgraph-server:8000/mcp"
}
```

### GET /schema
Returns OpenAPI schema for Bedrock Agent configuration.

## Monitoring and Logging

### CloudWatch Logs

Logs are automatically sent to CloudWatch:
- App Runner: `/aws/apprunner/action-agent-bedrock/`
- ECS: `/ecs/action-agent-bedrock`

### Key Log Messages

```
[Bedrock Request] Function: create_user
[Bedrock Request] Parameters: [...]
[Bedrock Response] User created successfully
[Error] Connection timeout to MCP server
```

### CloudWatch Metrics

Monitor these metrics:
- Request count
- Response time (p50, p95, p99)
- Error rate
- Health check status

## Scaling

### App Runner
- Auto-scales based on traffic (1-25 instances by default)
- Configure with `MaxConcurrency` and `MaxSize`

### ECS
- Configure auto-scaling policies based on CPU/memory
- Recommended: 2-10 tasks for production

## Security Best Practices

1. **VPC Configuration**: Deploy in private subnets with NAT gateway
2. **Security Groups**: Allow only HTTPS inbound from Bedrock
3. **IAM Roles**: Grant minimal permissions needed for MCP access
4. **Secrets**: Store MCP credentials in AWS Secrets Manager
5. **TLS**: Use ALB with ACM certificate for HTTPS
6. **API Authentication**: Add API key validation if needed

## Troubleshooting

### Agent Returns Errors

Check CloudWatch logs for:
```bash
aws logs tail /aws/apprunner/action-agent-bedrock --follow
```

### Health Check Failing

```bash
# Test locally
curl http://localhost:8080/health

# Test in AWS
curl https://your-service-url/health
```

### MCP Connection Issues

Verify MCP server is accessible from container:
```bash
# Check security groups
# Verify MCP_URL is correct
# Test MCP endpoint directly
```

### Bedrock Agent Not Calling API

1. Verify action group endpoint URL is correct
2. Check security group allows inbound from Bedrock
3. Verify OpenAPI schema matches your API
4. Check CloudWatch logs for Bedrock Agent errors

## Cost Optimization

- **App Runner**: ~$25-50/month for small workloads
- **ECS Fargate**: ~$30-60/month for 2 tasks (512 CPU, 1GB memory)
- Use Fargate Spot for non-production (70% savings)

## Next Steps

1. Deploy to staging environment
2. Test all IAM operations
3. Configure monitoring and alerts
4. Deploy to production
5. Document your specific action group schemas
6. Set up CI/CD pipeline for updates

## Support

For issues or questions:
- Check CloudWatch logs first
- Review Bedrock Agent execution logs
- Test endpoints directly with curl
- Verify MCP server connectivity
