#!/usr/bin/env python3
"""
Script to create Cognito User Pool for AgentCore Gateway authentication.

This script sets up:
- Cognito User Pool (secure login system)
- User Pool Domain (for OAuth endpoints)
- App Client (for machine-to-machine authentication)
- OAuth 2.0 configuration with client credentials flow

Credentials are saved to cognito_config.json for gateway setup.
"""

import boto3
import json
import time
import uuid

# Configuration
REGION = "us-west-2"
POOL_NAME = f"returns-gateway-pool-{uuid.uuid4().hex[:8]}"
DOMAIN_PREFIX = f"returns-gateway-{uuid.uuid4().hex[:8]}"
CLIENT_NAME = "returns-gateway-client"

print("=" * 80)
print("CREATING COGNITO USER POOL FOR GATEWAY AUTHENTICATION")
print("=" * 80)
print()
print(f"Region: {REGION}")
print(f"User Pool Name: {POOL_NAME}")
print(f"Domain Prefix: {DOMAIN_PREFIX}")
print(f"App Client Name: {CLIENT_NAME}")
print()

# Create Cognito client
cognito_client = boto3.client('cognito-idp', region_name=REGION)

# ============================================================================
# STEP 1: Create User Pool
# ============================================================================

print("=" * 80)
print("STEP 1: Creating Cognito User Pool")
print("=" * 80)
print()

try:
    user_pool_response = cognito_client.create_user_pool(
        PoolName=POOL_NAME,
        Policies={
            'PasswordPolicy': {
                'MinimumLength': 8,
                'RequireUppercase': False,
                'RequireLowercase': False,
                'RequireNumbers': False,
                'RequireSymbols': False
            }
        },
        AutoVerifiedAttributes=[],
        Schema=[
            {
                'Name': 'email',
                'AttributeDataType': 'String',
                'Mutable': True,
                'Required': False
            }
        ]
    )
    
    user_pool_id = user_pool_response['UserPool']['Id']
    print(f"✓ User Pool created: {user_pool_id}")
    print()
    
except Exception as e:
    print(f"✗ Failed to create User Pool: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# ============================================================================
# STEP 2: Create User Pool Domain
# ============================================================================

print("=" * 80)
print("STEP 2: Creating User Pool Domain")
print("=" * 80)
print()
print(f"Domain Prefix: {DOMAIN_PREFIX}")
print()

try:
    domain_response = cognito_client.create_user_pool_domain(
        Domain=DOMAIN_PREFIX,
        UserPoolId=user_pool_id
    )
    
    print(f"✓ Domain created: {DOMAIN_PREFIX}.auth.{REGION}.amazoncognito.com")
    print()
    
    # Wait for domain to be ready
    print("⏳ Waiting for domain to become active (10 seconds)...")
    time.sleep(10)
    print("✓ Domain should be active")
    print()
    
except Exception as e:
    print(f"✗ Failed to create domain: {e}")
    import traceback
    traceback.print_exc()
    # Clean up user pool
    try:
        cognito_client.delete_user_pool(UserPoolId=user_pool_id)
    except:
        pass
    exit(1)

# ============================================================================
# STEP 3: Create Resource Server (for OAuth scopes)
# ============================================================================

print("=" * 80)
print("STEP 3: Creating Resource Server")
print("=" * 80)
print()

try:
    resource_server_response = cognito_client.create_resource_server(
        UserPoolId=user_pool_id,
        Identifier='gateway-api',
        Name='Gateway API',
        Scopes=[
            {
                'ScopeName': 'read',
                'ScopeDescription': 'Read access to gateway'
            },
            {
                'ScopeName': 'write',
                'ScopeDescription': 'Write access to gateway'
            }
        ]
    )
    
    print("✓ Resource Server created with scopes: read, write")
    print()
    
except Exception as e:
    print(f"✗ Failed to create resource server: {e}")
    import traceback
    traceback.print_exc()
    # Clean up
    try:
        cognito_client.delete_user_pool_domain(Domain=DOMAIN_PREFIX, UserPoolId=user_pool_id)
        cognito_client.delete_user_pool(UserPoolId=user_pool_id)
    except:
        pass
    exit(1)

# ============================================================================
# STEP 4: Create App Client
# ============================================================================

print("=" * 80)
print("STEP 4: Creating App Client")
print("=" * 80)
print()

try:
    app_client_response = cognito_client.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=CLIENT_NAME,
        GenerateSecret=True,  # Required for client credentials flow
        ExplicitAuthFlows=[],  # No user authentication flows
        AllowedOAuthFlows=['client_credentials'],  # Machine-to-machine
        AllowedOAuthScopes=[
            'gateway-api/read',
            'gateway-api/write'
        ],
        AllowedOAuthFlowsUserPoolClient=True,
        SupportedIdentityProviders=['COGNITO']
    )
    
    client_id = app_client_response['UserPoolClient']['ClientId']
    print(f"✓ App Client created: {client_id}")
    print()
    
except Exception as e:
    print(f"✗ Failed to create app client: {e}")
    import traceback
    traceback.print_exc()
    # Clean up
    try:
        cognito_client.delete_user_pool_domain(Domain=DOMAIN_PREFIX, UserPoolId=user_pool_id)
        cognito_client.delete_user_pool(UserPoolId=user_pool_id)
    except:
        pass
    exit(1)

# ============================================================================
# STEP 5: Get Client Secret
# ============================================================================

print("=" * 80)
print("STEP 5: Retrieving Client Secret")
print("=" * 80)
print()

try:
    client_details = cognito_client.describe_user_pool_client(
        UserPoolId=user_pool_id,
        ClientId=client_id
    )
    
    client_secret = client_details['UserPoolClient']['ClientSecret']
    print("✓ Client secret retrieved")
    print()
    
except Exception as e:
    print(f"✗ Failed to retrieve client secret: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# ============================================================================
# STEP 6: Build Configuration
# ============================================================================

print("=" * 80)
print("STEP 6: Building Configuration")
print("=" * 80)
print()

# Build OAuth token endpoint
token_endpoint = f"https://{DOMAIN_PREFIX}.auth.{REGION}.amazoncognito.com/oauth2/token"

# CRITICAL: Use IDP-based discovery URL (NOT hosted UI domain)
discovery_url = f"https://cognito-idp.{REGION}.amazonaws.com/{user_pool_id}/.well-known/openid-configuration"

# Create configuration
config = {
    "user_pool_id": user_pool_id,
    "domain_prefix": DOMAIN_PREFIX,
    "client_id": client_id,
    "client_secret": client_secret,
    "token_endpoint": token_endpoint,
    "discovery_url": discovery_url,
    "region": REGION,
    "scopes": ["gateway-api/read", "gateway-api/write"]
}

# Save to file
try:
    with open('cognito_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print("✓ Configuration saved to cognito_config.json")
    print()
    
except Exception as e:
    print(f"✗ Failed to save configuration: {e}")
    exit(1)

# ============================================================================
# SUMMARY
# ============================================================================

print("=" * 80)
print("✅ COGNITO SETUP COMPLETE")
print("=" * 80)
print()
print("Cognito User Pool Configuration:")
print(f"  User Pool ID: {user_pool_id}")
print(f"  Domain Prefix: {DOMAIN_PREFIX}")
print(f"  Client ID: {client_id}")
print(f"  Client Secret: {client_secret[:10]}...{client_secret[-10:]}")
print()
print("OAuth Endpoints:")
print(f"  Token Endpoint: {token_endpoint}")
print(f"  Discovery URL: {discovery_url}")
print()
print("OAuth Scopes:")
print("  • gateway-api/read")
print("  • gateway-api/write")
print()
print("Configuration saved to: cognito_config.json")
print()
print("=" * 80)
print("NEXT STEPS:")
print("=" * 80)
print()
print("1. Use this configuration to create an AgentCore Gateway")
print("2. The gateway will use these credentials for OAuth authentication")
print("3. Agents will get access tokens to call gateway tools securely")
print()
print("=" * 80)
