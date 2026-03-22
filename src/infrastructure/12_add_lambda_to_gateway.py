#!/usr/bin/env python3
"""
Script to add Lambda target to AgentCore Gateway.

Prerequisites:
- gateway_config.json (from gateway creation)
"""

import json
import boto3

# Load gateway configuration
with open('gateway_config.json') as f:
    gateway_config = json.load(f)

# Initialize AgentCore control plane client
gateway_client = boto3.client("bedrock-agentcore-control", region_name='us-west-2')

# Lambda ARN and tool schema (inlined from MCP call)
lambda_arn = "arn:aws:lambda:us-west-2:943657149005:function:OrderLookupFunction"
tool_schema = [
    {
        "name": "lookup_order",
        "description": "Look up order details by order ID. Returns order information including product name, purchase date, amount, and return eligibility status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID to look up (e.g., ORD-001, ORD-002, ORD-003)"
                }
            },
            "required": [
                "order_id"
            ]
        }
    }
]

# Build Lambda target configuration with MCP protocol
lambda_target_config = {
    "mcp": {
        "lambda": {
            "lambdaArn": lambda_arn,
            "toolSchema": {
                "inlinePayload": tool_schema
            }
        }
    }
}

# Use gateway's IAM role for Lambda invocation
credential_config = [{"credentialProviderType": "GATEWAY_IAM_ROLE"}]

# Create target
print("Adding Lambda target to gateway...")
print(f"  Gateway ID: {gateway_config['gateway_id']}")
print(f"  Target Name: OrderLookup")
print(f"  Lambda ARN: {lambda_arn}")

create_response = gateway_client.create_gateway_target(
    gatewayIdentifier=gateway_config["gateway_id"],
    name="OrderLookup",
    description="Lambda function that looks up order details for returns processing",
    targetConfiguration=lambda_target_config,
    credentialProviderConfigurations=credential_config
)

target_id = create_response["targetId"]

print(f"\n✓ Lambda target added successfully!")
print(f"  Target ID: {target_id}")
print(f"  Target Name: OrderLookup")
