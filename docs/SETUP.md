# Setup Guide

Complete setup instructions for deploying the Returns & Refunds Agent.

## Prerequisites

### AWS Account Setup

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
3. **Bedrock Model Access** - Request access to Claude Sonnet 4.5
4. **Python 3.10+** installed

### Required AWS Permissions

Your IAM user/role needs permissions for:
- Amazon Bedrock (model invocation)
- AgentCore (runtime, memory, gateway)
- IAM (role creation)
- Lambda (function creation)
- Cognito (user pool management)
- CloudWatch (logs and metrics)
- X-Ray (tracing)
- ECR (container registry)

## Installation Steps

### 1. Clone Repository

```bash
git clone https://github.com/arvind-narain/returns-refunds-agent.git
cd returns-refunds-agent
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure AWS CLI

```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Default region: us-west-2
# Default output format: json
```

### 4. Verify Bedrock Access

```bash
aws bedrock list-foundation-models --region us-west-2
```

## Deployment Sequence

Follow these scripts in order:

### Phase 1: Memory Setup

```bash
# Create AgentCore Memory
python3 src/infrastructure/03_create_memory.py

# Seed with sample data
python3 src/infrastructure/04_seed_memory.py

# Test memory retrieval
python3 src/tests/05_test_memory.py
```

### Phase 2: Authentication

```bash
# Create Cognito User Pool
python3 src/infrastructure/08_create_cognito.py
```

### Phase 3: IAM Roles

```bash
# Create Gateway execution role
python3 src/infrastructure/09_create_gateway_role.py

# Create Runtime execution role
python3 src/infrastructure/16_create_runtime_role.py
```

### Phase 4: Gateway Setup

```bash
# Create Lambda function
python3 src/infrastructure/10_create_lambda.py

# Create Gateway
python3 src/infrastructure/11_create_gateway.py

# Add Lambda to Gateway
python3 src/infrastructure/12_add_lambda_to_gateway.py

# Verify targets
python3 src/infrastructure/13_list_gateway_targets.py
```

### Phase 5: Agent Deployment

```bash
# Deploy to AgentCore Runtime
python3 scripts/19_deploy_agent.py

# Monitor deployment (5-10 minutes)
python3 scripts/20_check_status.py

# Or monitor continuously
python3 scripts/20_check_status.py --monitor
```

### Phase 6: Testing

```bash
# Test deployed agent
python3 scripts/21_invoke_agent.py
```

### Phase 7: UI Launch

```bash
# Install Streamlit dependencies
pip install -r requirements_streamlit.txt

# Launch UI
cd src/ui
./run_streamlit.sh
```

## Configuration Files

After deployment, you'll have these configuration files:

- `memory_config.json` - Memory resource ID
- `cognito_config.json` - Cognito credentials
- `gateway_config.json` - Gateway URL and ID
- `gateway_role_config.json` - Gateway IAM role ARN
- `lambda_config.json` - Lambda function ARN
- `runtime_execution_role_config.json` - Runtime IAM role ARN
- `runtime_config.json` - Deployed agent ARN
- `kb_config.json` - Knowledge Base ID

**⚠️ Important:** These files contain sensitive information and are excluded from Git.

## Troubleshooting

### Deployment Fails

1. Check AWS credentials: `aws sts get-caller-identity`
2. Verify region: `us-west-2`
3. Check CloudWatch logs: `python3 scripts/23_get_logs_info.py`

### Agent Not Ready

1. Check status: `python3 scripts/20_check_status.py`
2. Wait 5-10 minutes for deployment
3. View logs for errors

### Authentication Errors

1. Verify Cognito configuration
2. Check OAuth token generation
3. Ensure discovery URL is correct (IDP format)

### Memory Not Working

1. Verify memory ID in config
2. Check memory creation status
3. Wait 20-30 seconds after seeding for processing

## Next Steps

- [Usage Guide](USAGE.md) - Learn how to use the agent
- [Architecture](ARCHITECTURE.md) - Understand the system design
- [API Reference](API.md) - Detailed API documentation
