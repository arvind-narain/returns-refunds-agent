#!/usr/bin/env python3
"""
Test the deployed agent's policy engine integration
"""

import json
import requests
from bedrock_agentcore_starter_toolkit import Runtime
import yaml

print("=" * 80)
print("TESTING POLICY ENGINE IN PRODUCTION")
print("=" * 80)

# Load configurations
with open('runtime_config.json') as f:
    runtime_config_data = json.load(f)

with open('cognito_config.json') as f:
    cognito_config = json.load(f)

with open('runtime_execution_role_config.json') as f:
    role_config = json.load(f)

with open('.bedrock_agentcore.yaml') as f:
    bedrock_config = yaml.safe_load(f)

default_agent = bedrock_config.get('default_agent')
agent_config = bedrock_config.get('agents', {}).get(default_agent, {})
agent_name = agent_config.get('name')
entrypoint = agent_config.get('entrypoint')

# Get OAuth token
print("\n1. Getting OAuth token...")
token_endpoint = cognito_config["token_endpoint"]
oauth_scopes = " ".join(cognito_config.get("scopes", ["gateway-api/read", "gateway-api/write"]))

response = requests.post(
    token_endpoint,
    data={
        "grant_type": "client_credentials",
        "client_id": cognito_config["client_id"],
        "client_secret": cognito_config["client_secret"],
        "scope": oauth_scopes
    },
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)

bearer_token = response.json()["access_token"]
print("   ✓ Token obtained")

# Initialize Runtime
print("\n2. Initializing Runtime...")
runtime = Runtime()

auth_config = {
    "customJWTAuthorizer": {
        "allowedClients": [cognito_config["client_id"]],
        "discoveryUrl": cognito_config["discovery_url"]
    }
}

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

# Test scenarios
test_scenarios = [
    {
        "name": "Electronics within window",
        "prompt": "I bought a laptop on March 1, 2026. Can I return it today? It's still unopened.",
        "expected": "eligible"
    },
    {
        "name": "Calculate refund for opened item",
        "prompt": "I have an item that cost $100. It's opened but unused. I changed my mind. How much refund will I get?",
        "expected": "restocking fee"
    },
    {
        "name": "Get policy information",
        "prompt": "What's your current return policy version and when was it last updated?",
        "expected": "policy version"
    }
]

print("\n" + "=" * 80)
print("RUNNING TEST SCENARIOS")
print("=" * 80)

for i, scenario in enumerate(test_scenarios, 1):
    print(f"\n{i}. {scenario['name']}")
    print(f"   Prompt: {scenario['prompt']}")
    print(f"   Expected: {scenario['expected']}")
    print("   " + "-" * 76)
    
    try:
        payload = {
            "prompt": scenario['prompt'],
            "actor_id": "test_user"
        }
        
        response = runtime.invoke(payload, bearer_token=bearer_token)
        response_text = response.get('response', '')
        
        print(f"   Response: {response_text[:200]}...")
        print(f"   ✓ Test completed")
        
    except Exception as e:
        print(f"   ✗ Error: {e}")

print("\n" + "=" * 80)
print("✓ ALL TESTS COMPLETED")
print("=" * 80)
print("\nCheck CloudWatch Logs to verify:")
print("  1. Policy engine is being called")
print("  2. Decisions are being logged")
print("  3. Policy version is included in responses")
print("\nLog group: /aws/bedrock-agentcore/runtimes/returns_refunds_agent-Gig9iD6daP-DEFAULT")
print("Decision log group: /aws/returns-agent/decisions")
print("=" * 80)
