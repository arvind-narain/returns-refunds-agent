#!/usr/bin/env python3
"""
Script to list AgentCore Gateway targets.

Prerequisites:
- gateway_config.json (from gateway creation)
"""

import json
import boto3

# Load configuration
with open('gateway_config.json') as f:
    gateway_config = json.load(f)

# Initialize AgentCore control plane client
gateway_client = boto3.client("bedrock-agentcore-control", region_name='us-west-2')

# List targets using correct API method
print(f"Listing targets for gateway: {gateway_config['gateway_id']}")
response = gateway_client.list_gateway_targets(
    gatewayIdentifier=gateway_config["gateway_id"]
)

targets = response.get("items", [])

print(f"\n✓ Found {len(targets)} target(s):")
for i, target in enumerate(targets, 1):
    print(f"\n{i}. {target.get('name', 'N/A')}")
    print(f"   Target ID: {target.get('targetId', 'N/A')}")
    print(f"   Status: {target.get('status', 'unknown')}")
    print(f"   Description: {target.get('description', 'N/A')}")
