#!/usr/bin/env python3
"""
Script to create Lambda function for order lookup.

This Lambda function:
- Looks up order details by order ID
- Returns order information including return eligibility
- Uses mock data with 3 sample orders
- Will be exposed as a tool through AgentCore Gateway
"""

import boto3
import json
import time
import zipfile
import io
from datetime import datetime, timedelta

# Configuration
REGION = "us-west-2"
FUNCTION_NAME = "OrderLookupFunction"

print("=" * 80)
print("CREATING LAMBDA FUNCTION FOR ORDER LOOKUP")
print("=" * 80)
print()
print(f"Region: {REGION}")
print(f"Function Name: {FUNCTION_NAME}")
print()

# Create clients
lambda_client = boto3.client('lambda', region_name=REGION)
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
# STEP 1: Create Lambda Execution Role
# ============================================================================

print("=" * 80)
print("STEP 1: Creating Lambda Execution Role")
print("=" * 80)
print()

LAMBDA_ROLE_NAME = f"{FUNCTION_NAME}Role"

# Trust policy for Lambda
lambda_trust_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}

try:
    # Try to create the role
    role_response = iam_client.create_role(
        RoleName=LAMBDA_ROLE_NAME,
        AssumeRolePolicyDocument=json.dumps(lambda_trust_policy),
        Description=f"Execution role for {FUNCTION_NAME}",
        Tags=[
            {'Key': 'Purpose', 'Value': 'LambdaExecution'},
            {'Key': 'Function', 'Value': FUNCTION_NAME}
        ]
    )
    lambda_role_arn = role_response['Role']['Arn']
    print(f"✓ Created new role: {LAMBDA_ROLE_NAME}")
    
    # Attach basic Lambda execution policy
    iam_client.attach_role_policy(
        RoleName=LAMBDA_ROLE_NAME,
        PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
    )
    print(f"✓ Attached AWSLambdaBasicExecutionRole policy")
    
    # Wait for role to propagate
    print("⏳ Waiting 10 seconds for IAM role to propagate...")
    time.sleep(10)
    
except iam_client.exceptions.EntityAlreadyExistsException:
    # Role already exists, get its ARN
    role_response = iam_client.get_role(RoleName=LAMBDA_ROLE_NAME)
    lambda_role_arn = role_response['Role']['Arn']
    print(f"✓ Using existing role: {LAMBDA_ROLE_NAME}")
except Exception as e:
    print(f"✗ Failed to create/get Lambda role: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print(f"✓ Lambda Role ARN: {lambda_role_arn}")
print()

# ============================================================================
# STEP 2: Create Lambda Function Code
# ============================================================================

print("=" * 80)
print("STEP 2: Creating Lambda Function Code")
print("=" * 80)
print()

# Lambda function code with mock order data
lambda_code = '''
import json
from datetime import datetime, timedelta

# Mock order database
ORDERS = {
    "ORD-001": {
        "order_id": "ORD-001",
        "product_name": "Dell XPS 15 Laptop",
        "purchase_date": (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d"),
        "amount": 1299.99,
        "category": "electronics",
        "condition": "unopened",
        "return_eligible": True,
        "return_window_days": 90,
        "days_remaining": 75
    },
    "ORD-002": {
        "order_id": "ORD-002",
        "product_name": "iPhone 13 Pro",
        "purchase_date": (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d"),
        "amount": 999.99,
        "category": "electronics",
        "condition": "opened",
        "return_eligible": False,
        "return_window_days": 30,
        "days_remaining": 0,
        "reason": "Return window expired (30 days for phones)"
    },
    "ORD-003": {
        "order_id": "ORD-003",
        "product_name": "Samsung Galaxy Tab S8",
        "purchase_date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
        "amount": 649.99,
        "category": "electronics",
        "condition": "defective",
        "return_eligible": True,
        "return_window_days": 90,
        "days_remaining": 85,
        "issue": "Screen flickering - defective unit"
    }
}

def lambda_handler(event, context):
    """
    Look up order details by order ID.
    
    Args:
        event: Contains 'order_id' parameter
        context: Lambda context
        
    Returns:
        Order details including return eligibility
    """
    try:
        # Extract order_id from event
        order_id = event.get('order_id', '').strip().upper()
        
        if not order_id:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing order_id parameter',
                    'message': 'Please provide an order_id (e.g., ORD-001)'
                })
            }
        
        # Look up order
        if order_id in ORDERS:
            order = ORDERS[order_id]
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'order': order
                })
            }
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'success': False,
                    'error': 'Order not found',
                    'message': f'Order {order_id} does not exist',
                    'available_orders': list(ORDERS.keys())
                })
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }
'''

# Create deployment package
print("Creating deployment package...")
zip_buffer = io.BytesIO()
with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
    zip_file.writestr('lambda_function.py', lambda_code)

deployment_package = zip_buffer.getvalue()
print(f"✓ Deployment package created ({len(deployment_package)} bytes)")
print()

# ============================================================================
# STEP 3: Create Lambda Function
# ============================================================================

print("=" * 80)
print("STEP 3: Creating Lambda Function")
print("=" * 80)
print()

try:
    # Try to create the function
    function_response = lambda_client.create_function(
        FunctionName=FUNCTION_NAME,
        Runtime='python3.12',
        Role=lambda_role_arn,
        Handler='lambda_function.lambda_handler',
        Code={'ZipFile': deployment_package},
        Description='Order lookup function for AgentCore Gateway',
        Timeout=30,
        MemorySize=128,
        Tags={
            'Purpose': 'AgentCoreGateway',
            'Tool': 'lookup_order'
        }
    )
    
    function_arn = function_response['FunctionArn']
    print(f"✓ Lambda function created: {FUNCTION_NAME}")
    print(f"✓ Function ARN: {function_arn}")
    
except lambda_client.exceptions.ResourceConflictException:
    # Function already exists, update its code
    print(f"⚠️  Function {FUNCTION_NAME} already exists, updating code...")
    
    update_response = lambda_client.update_function_code(
        FunctionName=FUNCTION_NAME,
        ZipFile=deployment_package
    )
    
    function_arn = update_response['FunctionArn']
    print(f"✓ Lambda function code updated: {FUNCTION_NAME}")
    print(f"✓ Function ARN: {function_arn}")
    
except Exception as e:
    print(f"✗ Failed to create Lambda function: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print()

# ============================================================================
# STEP 4: Wait for Function to be Active
# ============================================================================

print("=" * 80)
print("STEP 4: Waiting for Function to be Active")
print("=" * 80)
print()

print("⏳ Waiting for Lambda function to be ready...")
time.sleep(5)

try:
    function_config = lambda_client.get_function(FunctionName=FUNCTION_NAME)
    state = function_config['Configuration']['State']
    print(f"✓ Function state: {state}")
    print()
except Exception as e:
    print(f"⚠️  Could not verify function state: {e}")
    print()

# ============================================================================
# STEP 5: Create Tool Schema
# ============================================================================

print("=" * 80)
print("STEP 5: Creating Tool Schema")
print("=" * 80)
print()

tool_schema = {
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
        "required": ["order_id"]
    }
}

print("Tool Schema:")
print(json.dumps(tool_schema, indent=2))
print()

# ============================================================================
# STEP 6: Save Configuration
# ============================================================================

print("=" * 80)
print("STEP 6: Saving Configuration")
print("=" * 80)
print()

config = {
    "function_name": FUNCTION_NAME,
    "function_arn": function_arn,
    "region": REGION,
    "tool_schema": tool_schema,
    "sample_orders": ["ORD-001", "ORD-002", "ORD-003"],
    "order_details": {
        "ORD-001": "Recent laptop (15 days old) - eligible for return",
        "ORD-002": "Old phone (45 days old) - return window expired",
        "ORD-003": "Defective tablet (5 days old) - eligible for return"
    }
}

try:
    with open('lambda_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print("✓ Configuration saved to lambda_config.json")
    print()
    
except Exception as e:
    print(f"✗ Failed to save configuration: {e}")
    exit(1)

# ============================================================================
# SUMMARY
# ============================================================================

print("=" * 80)
print("✅ LAMBDA FUNCTION CREATED SUCCESSFULLY")
print("=" * 80)
print()
print("Lambda Function Details:")
print(f"  Function Name: {FUNCTION_NAME}")
print(f"  Function ARN: {function_arn}")
print(f"  Runtime: Python 3.12")
print(f"  Handler: lambda_function.lambda_handler")
print()
print("Tool Details:")
print(f"  Tool Name: lookup_order")
print(f"  Purpose: Look up order details by order ID")
print()
print("Sample Orders:")
print("  • ORD-001: Dell XPS 15 Laptop (15 days old, eligible)")
print("  • ORD-002: iPhone 13 Pro (45 days old, expired)")
print("  • ORD-003: Samsung Galaxy Tab S8 (5 days old, defective, eligible)")
print()
print("Configuration saved to: lambda_config.json")
print()
print("=" * 80)
print("NEXT STEPS:")
print("=" * 80)
print()
print("1. Test the Lambda function with sample order IDs")
print("2. Create AgentCore Gateway with this Lambda as a target")
print("3. Your agent will be able to look up order details using the gateway")
print()
print("=" * 80)
