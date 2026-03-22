#!/usr/bin/env python3
"""
Script to create IAM role for AgentCore Gateway.

This script creates:
- IAM role that the gateway can assume
- Trust policy allowing AgentCore Gateway service to assume the role
- Permissions to invoke Lambda functions
- Saves role ARN to gateway_role_config.json
"""

import boto3
import json
import time
import uuid

# Configuration
REGION = "us-west-2"
ROLE_NAME = f"AgentCoreGatewayRole-{uuid.uuid4().hex[:8]}"

print("=" * 80)
print("CREATING IAM ROLE FOR AGENTCORE GATEWAY")
print("=" * 80)
print()
print(f"Region: {REGION}")
print(f"Role Name: {ROLE_NAME}")
print()

# Create IAM client
iam_client = boto3.client('iam', region_name=REGION)
sts_client = boto3.client('sts', region_name=REGION)

# Get account ID
try:
    account_id = sts_client.get_caller_identity()['Account']
    print(f"✓ AWS Account ID: {account_id}")
    print()
except Exception as e:
    print(f"✗ Failed to get account ID: {e}")
    exit(1)

# ============================================================================
# STEP 1: Create IAM Role with Trust Policy
# ============================================================================

print("=" * 80)
print("STEP 1: Creating IAM Role")
print("=" * 80)
print()

# Trust policy - allows AgentCore Gateway service to assume this role
trust_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "bedrock-agentcore.amazonaws.com"
            },
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {
                    "aws:SourceAccount": account_id
                }
            }
        }
    ]
}

print("Trust Policy:")
print(json.dumps(trust_policy, indent=2))
print()

try:
    role_response = iam_client.create_role(
        RoleName=ROLE_NAME,
        AssumeRolePolicyDocument=json.dumps(trust_policy),
        Description="IAM role for AgentCore Gateway to invoke Lambda functions",
        Tags=[
            {
                'Key': 'Purpose',
                'Value': 'AgentCoreGateway'
            },
            {
                'Key': 'ManagedBy',
                'Value': 'Script'
            }
        ]
    )
    
    role_arn = role_response['Role']['Arn']
    print(f"✓ IAM Role created: {ROLE_NAME}")
    print(f"✓ Role ARN: {role_arn}")
    print()
    
except Exception as e:
    print(f"✗ Failed to create IAM role: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# ============================================================================
# STEP 2: Attach Lambda Invoke Policy
# ============================================================================

print("=" * 80)
print("STEP 2: Attaching Lambda Invoke Policy")
print("=" * 80)
print()

# Inline policy for Lambda invocation
lambda_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunction"
            ],
            "Resource": f"arn:aws:lambda:{REGION}:{account_id}:function:*"
        }
    ]
}

print("Lambda Invoke Policy:")
print(json.dumps(lambda_policy, indent=2))
print()

try:
    iam_client.put_role_policy(
        RoleName=ROLE_NAME,
        PolicyName="LambdaInvokePolicy",
        PolicyDocument=json.dumps(lambda_policy)
    )
    
    print("✓ Lambda invoke policy attached")
    print()
    
except Exception as e:
    print(f"✗ Failed to attach policy: {e}")
    import traceback
    traceback.print_exc()
    # Clean up role
    try:
        iam_client.delete_role(RoleName=ROLE_NAME)
    except:
        pass
    exit(1)

# ============================================================================
# STEP 3: Wait for IAM Propagation
# ============================================================================

print("=" * 80)
print("STEP 3: Waiting for IAM Propagation")
print("=" * 80)
print()
print("⏳ Waiting 10 seconds for IAM changes to propagate...")
time.sleep(10)
print("✓ IAM propagation complete")
print()

# ============================================================================
# STEP 4: Verify Role
# ============================================================================

print("=" * 80)
print("STEP 4: Verifying Role")
print("=" * 80)
print()

try:
    role_details = iam_client.get_role(RoleName=ROLE_NAME)
    print(f"✓ Role verified: {role_details['Role']['RoleName']}")
    print(f"✓ Role ARN: {role_details['Role']['Arn']}")
    print()
    
except Exception as e:
    print(f"✗ Failed to verify role: {e}")
    exit(1)

# ============================================================================
# STEP 5: Save Configuration
# ============================================================================

print("=" * 80)
print("STEP 5: Saving Configuration")
print("=" * 80)
print()

config = {
    "role_arn": role_arn,
    "role_name": ROLE_NAME,
    "region": REGION,
    "account_id": account_id,
    "permissions": [
        "lambda:InvokeFunction"
    ]
}

try:
    with open('gateway_role_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print("✓ Configuration saved to gateway_role_config.json")
    print()
    
except Exception as e:
    print(f"✗ Failed to save configuration: {e}")
    exit(1)

# ============================================================================
# SUMMARY
# ============================================================================

print("=" * 80)
print("✅ GATEWAY IAM ROLE CREATED SUCCESSFULLY")
print("=" * 80)
print()
print("IAM Role Details:")
print(f"  Role Name: {ROLE_NAME}")
print(f"  Role ARN: {role_arn}")
print(f"  Account ID: {account_id}")
print()
print("Permissions Granted:")
print("  ✓ Invoke Lambda functions in this account")
print()
print("Trust Policy:")
print("  ✓ AgentCore Gateway service can assume this role")
print()
print("Configuration saved to: gateway_role_config.json")
print()
print("=" * 80)
print("NEXT STEPS:")
print("=" * 80)
print()
print("1. Create Lambda functions for your gateway targets")
print("2. Create AgentCore Gateway using this role ARN")
print("3. The gateway will use this role to invoke your Lambda functions")
print()
print("=" * 80)
