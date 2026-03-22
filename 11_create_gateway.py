#!/usr/bin/env python3
"""
Script to create AgentCore Gateway.

Prerequisites:
- cognito_config.json (from Cognito setup)
- gateway_role_config.json (from IAM role setup)
"""

import json
import boto3

# Load configuration
with open('cognito_config.json') as f:
    cognito_config = json.load(f)
with open('gateway_role_config.json') as f:
    role_config = json.load(f)

# Initialize AgentCore control plane client
gateway_client = boto3.client("bedrock-agentcore-control", region_name='us-west-2')

# Build auth configuration for Cognito JWT
auth_config = {
    "customJWTAuthorizer": {
        "allowedClients": [cognito_config["client_id"]],
        "discoveryUrl": cognito_config["discovery_url"]
    }
}

# Create gateway
print("Creating AgentCore Gateway...")
create_response = gateway_client.create_gateway(
    name="ReturnsRefundsGateway",
    roleArn=role_config["role_arn"],
    protocolType="MCP",
    authorizerType="CUSTOM_JWT",
    authorizerConfiguration=auth_config,
    description="Gateway for returns and refunds agent to access order lookup service"
)

# Extract gateway details
gateway_id = create_response["gatewayId"]
gateway_url = create_response["gatewayUrl"]
gateway_arn = create_response["gatewayArn"]

# Save gateway config (using 'id' to match reference code pattern)
config = {
    "id": gateway_id,
    "gateway_id": gateway_id,  # Keep for backward compatibility
    "gateway_url": gateway_url,
    "gateway_arn": gateway_arn,
    "name": "ReturnsRefundsGateway",
    "region": "us-west-2"
}

with open('gateway_config.json', 'w') as f:
    json.dump(config, f, indent=2)

print(f"✓ Gateway created successfully!")
print(f"  Gateway ID: {gateway_id}")
print(f"  Gateway URL: {gateway_url}")
print(f"✓ Configuration saved to gateway_config.json")
