#!/usr/bin/env python3
"""
Script to invoke deployed AgentCore Runtime agent.

This script:
1. Loads Cognito credentials
2. Gets OAuth token for authentication
3. Invokes the deployed agent
4. Displays the response
"""

import json
import os
import requests
from bedrock_agentcore_starter_toolkit import Runtime

print("=" * 80)
print("INVOKE AGENTCORE RUNTIME AGENT")
print("=" * 80)

# Check if runtime config exists
if not os.path.exists('runtime_config.json'):
    print("\n❌ Error: Agent not deployed yet")
    print("Please run 19_deploy_agent.py first")
    exit(1)

# Load configuration
print("\n1. Loading configuration files...")
try:
    with open('runtime_config.json') as f:
        runtime_output_config = json.load(f)
    print("   ✓ runtime_config.json")
    
    with open('cognito_config.json') as f:
        cognito_config = json.load(f)
    print("   ✓ cognito_config.json")
    
    with open('runtime_execution_role_config.json') as f:
        role_config = json.load(f)
    print("   ✓ runtime_execution_role_config.json")
except FileNotFoundError as e:
    print(f"   ✗ Configuration file not found: {e}")
    exit(1)

# Load .bedrock_agentcore.yaml to get agent name and entrypoint
if not os.path.exists('.bedrock_agentcore.yaml'):
    print("\n❌ Error: .bedrock_agentcore.yaml not found")
    print("Please run 19_deploy_agent.py first")
    exit(1)

import yaml
with open('.bedrock_agentcore.yaml') as f:
    runtime_config = yaml.safe_load(f)

default_agent = runtime_config.get('default_agent')
agent_config = runtime_config.get('agents', {}).get(default_agent, {})
agent_name = agent_config.get('name')
entrypoint = agent_config.get('entrypoint')

# Step 2: Generate OAuth bearer token
print("\n2. Generating OAuth bearer token...")

# Use token endpoint from config
token_endpoint = cognito_config["token_endpoint"]

# Get OAuth scopes
oauth_scopes = " ".join(cognito_config.get("scopes", ["gateway-api/read", "gateway-api/write"]))

# Request token using client credentials flow
try:
    response = requests.post(
        token_endpoint,
        data={
            "grant_type": "client_credentials",
            "client_id": cognito_config["client_id"],
            "client_secret": cognito_config["client_secret"],
            "scope": oauth_scopes
        },
        headers={
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )
    
    if response.status_code != 200:
        print(f"   ✗ Failed to get OAuth token: {response.text}")
        exit(1)
    
    bearer_token = response.json()["access_token"]
    print("   ✓ OAuth token obtained")
except Exception as e:
    print(f"   ✗ Error getting OAuth token: {e}")
    exit(1)

# Step 3: Initialize Runtime
print("\n3. Initializing Runtime...")
runtime = Runtime()

# Build authorizer configuration for Cognito JWT
auth_config = {
    "customJWTAuthorizer": {
        "allowedClients": [cognito_config["client_id"]],
        "discoveryUrl": cognito_config["discovery_url"]
    }
}

# Configure runtime (to load existing configuration)
runtime.configure(
    entrypoint=entrypoint,
    agent_name=agent_name,
    execution_role=role_config["role_arn"],
    auto_create_ecr=True,
    memory_mode="NO_MEMORY",
    requirements_file="requirements.txt",
    region="us-west-2",
    authorizer_configuration=auth_config
)
print("   ✓ Runtime configured")

# Step 4: Invoke agent
print("\n4. Invoking agent...")
print(f"   Agent ARN: {runtime_output_config['agent_arn']}")
print(f"   Actor ID: user_001")
print(f"   Prompt: 'Can you look up my order ORD-001 and help me with a return?'")

payload = {
    "prompt": "Can you look up my order ORD-001 and help me with a return?",
    "actor_id": "user_001"
}

try:
    print("\n   Sending request to agent...")
    response = runtime.invoke(
        payload,
        bearer_token=bearer_token
    )
    
    print("\n" + "=" * 80)
    print("✅ AGENT RESPONSE")
    print("=" * 80)
    print(response)
    print("=" * 80)
    
    print("\n✓ Agent invocation completed successfully!")
    
except Exception as e:
    print("\n" + "=" * 80)
    print("❌ ERROR INVOKING AGENT")
    print("=" * 80)
    print(f"Error: {e}")
    print("\nTroubleshooting:")
    print("  1. Check agent status:")
    print("     python3 20_check_status.py")
    print("\n  2. Verify agent is in READY state")
    print("\n  3. Check CloudWatch logs:")
    print(f"     aws logs tail /aws/bedrock-agentcore/runtimes/{agent_name.replace('_', '-')}-* --since 10m")
    print("\n  4. Verify OAuth token is valid")
    print("=" * 80)
    import traceback
    traceback.print_exc()
    exit(1)
