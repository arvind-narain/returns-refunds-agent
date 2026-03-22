#!/usr/bin/env python3
"""
Script to check AgentCore Runtime deployment status.

Monitors deployment status and displays current state.
"""

import json
import os
import time
import sys
from bedrock_agentcore_starter_toolkit import Runtime

print("=" * 80)
print("AGENTCORE RUNTIME STATUS CHECK")
print("=" * 80)

# Check if runtime config exists
if not os.path.exists('runtime_config.json'):
    print("\n❌ Error: Agent not deployed yet")
    print("Please run 19_deploy_agent.py first")
    exit(1)

# Load runtime config
with open('runtime_config.json') as f:
    runtime_output_config = json.load(f)

print(f"\nAgent ARN: {runtime_output_config['agent_arn']}")
print(f"Agent Name: {runtime_output_config['agent_name']}")
print(f"Region: {runtime_output_config['region']}")

# Load configuration files
try:
    with open('runtime_execution_role_config.json') as f:
        role_config = json.load(f)
    with open('cognito_config.json') as f:
        cognito_config = json.load(f)
except FileNotFoundError as e:
    print(f"\n❌ Error: Configuration file not found: {e}")
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

# Initialize Runtime
runtime = Runtime()

# Build authorizer configuration for Cognito JWT
auth_config = {
    "customJWTAuthorizer": {
        "allowedClients": [cognito_config["client_id"]],
        "discoveryUrl": cognito_config["discovery_url"]
    }
}

# Configure runtime (to load existing configuration)
print("\nLoading runtime configuration...")
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

# Check if user wants to monitor continuously
monitor_mode = len(sys.argv) > 1 and sys.argv[1] == "--monitor"

if monitor_mode:
    print("\n🔄 Monitoring mode enabled - will check status every 30 seconds")
    print("Press Ctrl+C to stop monitoring\n")

try:
    while True:
        print("\n" + "=" * 80)
        print(f"Checking status at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        try:
            status_response = runtime.status()
            status = status_response.endpoint["status"]
            
            print(f"\n📊 Agent Status: {status}")
            
            # Display endpoint details
            endpoint = status_response.endpoint
            print(f"\nEndpoint Details:")
            print(f"  Status: {endpoint.get('status', 'N/A')}")
            print(f"  Created: {endpoint.get('createdAt', 'N/A')}")
            print(f"  Updated: {endpoint.get('updatedAt', 'N/A')}")
            
            if status == "READY":
                print("\n" + "=" * 80)
                print("✅ Agent is READY to receive requests!")
                print("=" * 80)
                print("\nYour agent is fully deployed and operational.")
                print("\nNext steps:")
                print("  1. Test your agent:")
                print("     agentcore invoke '{\"prompt\": \"Hello!\"}'")
                print("\n  2. View logs:")
                print(f"     aws logs tail /aws/bedrock-agentcore/runtimes/{agent_name.replace('_', '-')}-* --follow")
                print("\n  3. Monitor in CloudWatch:")
                print("     https://console.aws.amazon.com/cloudwatch/home?region=us-west-2#gen-ai-observability/agent-core")
                break  # Exit monitoring loop when ready
                
            elif status in ["CREATING", "UPDATING"]:
                print("\n" + "=" * 80)
                print("⏳ Agent deployment in progress...")
                print("=" * 80)
                print("\nThe deployment is still running. This is normal.")
                if not monitor_mode:
                    print("Run this script with --monitor to continuously check status:")
                    print("  python3 20_check_status.py --monitor")
                    break
                else:
                    print("\nWaiting 30 seconds before next check...")
                    time.sleep(30)
                    
            elif status in ["CREATE_FAILED", "UPDATE_FAILED"]:
                print("\n" + "=" * 80)
                print("❌ Agent deployment failed!")
                print("=" * 80)
                print("\nCheck CloudWatch logs for details:")
                print(f"  Log group: /aws/bedrock-agentcore/runtimes/{agent_name.replace('_', '-')}-*")
                print("\nView logs with:")
                print(f"  aws logs tail /aws/bedrock-agentcore/runtimes/{agent_name.replace('_', '-')}-* --since 1h")
                break
                
            else:
                print(f"\n⚠️  Unknown status: {status}")
                print(f"\nFull endpoint details:")
                print(json.dumps(endpoint, indent=2, default=str))
                if not monitor_mode:
                    break
                else:
                    print("\nWaiting 30 seconds before next check...")
                    time.sleep(30)
                    
        except Exception as e:
            print(f"\n❌ Error checking status: {e}")
            if not monitor_mode:
                break
            else:
                print("\nWaiting 30 seconds before retry...")
                time.sleep(30)
        
        if not monitor_mode:
            break
            
except KeyboardInterrupt:
    print("\n\n⏹️  Monitoring stopped by user")
    print("=" * 80)
