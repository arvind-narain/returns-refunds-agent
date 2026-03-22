#!/usr/bin/env python3
"""
Script to deploy agent to AgentCore Runtime.

This script:
1. Loads all configuration files
2. Configures runtime deployment settings
3. Deploys agent to AgentCore Runtime
4. Saves agent ARN to runtime_config.json
"""

import json
import os
from bedrock_agentcore_starter_toolkit import Runtime

print("=" * 80)
print("AGENTCORE RUNTIME DEPLOYMENT")
print("=" * 80)

# Step 1: Load all configuration files
print("\n1. Loading configuration files...")

config_files = {}

try:
    with open('memory_config.json') as f:
        config_files['memory'] = json.load(f)
    print("   ✓ memory_config.json")
except FileNotFoundError:
    print("   ✗ memory_config.json not found")
    exit(1)

try:
    with open('gateway_config.json') as f:
        config_files['gateway'] = json.load(f)
    print("   ✓ gateway_config.json")
except FileNotFoundError:
    print("   ✗ gateway_config.json not found")
    exit(1)

try:
    with open('cognito_config.json') as f:
        config_files['cognito'] = json.load(f)
    print("   ✓ cognito_config.json")
except FileNotFoundError:
    print("   ✗ cognito_config.json not found")
    exit(1)

try:
    with open('runtime_execution_role_config.json') as f:
        config_files['role'] = json.load(f)
    print("   ✓ runtime_execution_role_config.json")
except FileNotFoundError:
    print("   ✗ runtime_execution_role_config.json not found")
    exit(1)

try:
    with open('kb_config.json') as f:
        config_files['kb'] = json.load(f)
    print("   ✓ kb_config.json")
except FileNotFoundError:
    print("   ✗ kb_config.json not found")
    exit(1)

# Step 2: Initialize Runtime
print("\n2. Initializing Runtime...")
runtime = Runtime()
print("   ✓ Runtime initialized")

# Step 3: Configure runtime deployment
print("\n3. Configuring runtime deployment...")

# Build authorizer configuration for Cognito JWT
auth_config = {
    "customJWTAuthorizer": {
        "allowedClients": [config_files['cognito']["client_id"]],
        "discoveryUrl": config_files['cognito']["discovery_url"]
    }
}

runtime.configure(
    entrypoint="src/agents/17_runtime_agent.py",
    agent_name="returns_refunds_agent",
    execution_role=config_files['role']["role_arn"],
    auto_create_ecr=True,
    memory_mode="NO_MEMORY",
    requirements_file="requirements.txt",
    region="us-west-2",
    authorizer_configuration=auth_config
)

print("   ✓ Runtime configured")
print("   ✓ Configuration saved to .bedrock_agentcore.yaml")

# Step 4: Build environment variables
print("\n4. Building environment variables...")

env_vars = {
    "MEMORY_ID": config_files['memory']["memory_id"],
    "KNOWLEDGE_BASE_ID": config_files['kb']["knowledge_base_id"],
    "GATEWAY_URL": config_files['gateway']["gateway_url"],
    "COGNITO_CLIENT_ID": config_files['cognito']["client_id"],
    "COGNITO_CLIENT_SECRET": config_files['cognito']["client_secret"],
    "COGNITO_DISCOVERY_URL": config_files['cognito']["discovery_url"],
    "OAUTH_SCOPES": " ".join(config_files['cognito'].get("scopes", ["gateway-api/read", "gateway-api/write"])),
    # Policy Engine configuration
    "POLICY_FILE": "policies/default_policy.yaml",
    # Decision Logging configuration
    "ENABLE_DECISION_LOGGING": "true",
    "DECISION_LOG_TABLE": "returns-decision-log",
    "AWS_REGION": "us-west-2"
}

print("   Environment variables:")
for key in env_vars:
    if "SECRET" in key or "PASSWORD" in key:
        print(f"     {key}: ***")
    else:
        print(f"     {key}: {env_vars[key]}")

# Step 5: Launch agent to runtime
print("\n" + "=" * 80)
print("5. LAUNCHING AGENT TO AGENTCORE RUNTIME")
print("=" * 80)
print("\nThis process will:")
print("  1. Create CodeBuild project")
print("  2. Build Docker container from your agent code")
print("  3. Push container to Amazon ECR")
print("  4. Deploy to AgentCore Runtime")
print("\n⏱️  Expected time: 5-10 minutes")
print("\n☕ Grab a coffee while the deployment runs...")
print("=" * 80 + "\n")

try:
    launch_result = runtime.launch(
        env_vars=env_vars,
        auto_update_on_conflict=True
    )
    
    agent_arn = launch_result.agent_arn
    
    # Step 6: Save agent ARN to config
    print("\n6. Saving deployment configuration...")
    
    runtime_output_config = {
        "agent_arn": agent_arn,
        "agent_name": "returns_refunds_agent",
        "region": "us-west-2",
        "memory_id": config_files['memory']["memory_id"],
        "gateway_url": config_files['gateway']["gateway_url"],
        "knowledge_base_id": config_files['kb']["knowledge_base_id"],
        "entrypoint": "src/agents/17_runtime_agent.py"
    }
    
    with open('runtime_config.json', 'w') as f:
        json.dump(runtime_output_config, f, indent=2)
    
    print("   ✓ Configuration saved to runtime_config.json")
    
    # Success summary
    print("\n" + "=" * 80)
    print("✓ DEPLOYMENT INITIATED SUCCESSFULLY!")
    print("=" * 80)
    print(f"\nAgent ARN: {agent_arn}")
    print(f"Agent Name: returns_refunds_agent")
    print(f"Region: us-west-2")
    print(f"Entrypoint: src/agents/17_runtime_agent.py")
    
    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("\n1. Monitor deployment status:")
    print("   The agent is being built and deployed (5-10 minutes)")
    print("   Check status with: agentcore status")
    print("\n2. Wait for status to show 'READY'")
    print("\n3. Once READY, test your agent:")
    print("   agentcore invoke '{\"prompt\": \"Hello!\"}'")
    print("\n4. View logs:")
    print("   Check CloudWatch Logs for /aws/bedrock-agentcore/")
    print("\n" + "=" * 80)

except Exception as e:
    print(f"\n✗ Deployment failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
