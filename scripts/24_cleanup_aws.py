#!/usr/bin/env python3
"""
Cleanup Script: Safely delete all AWS resources created for the Returns/Refunds Agent

This script deletes resources in the correct order to avoid dependency errors:
1. Runtime agent (deployed agent)
2. Gateway targets and gateway
3. Memory resource
4. Lambda function
5. Cognito user pool and domain
6. IAM roles and policies
7. ECR repository

Region: us-west-2
"""

import json
import time
import boto3
from pathlib import Path
from typing import Dict, Any, Optional

# Configuration
REGION = "us-west-2"
CONFIG_DIR = Path(".")

# Color codes for terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"


def load_config(filename: str) -> Optional[Dict[str, Any]]:
    """Load configuration from JSON file"""
    config_path = CONFIG_DIR / filename
    if not config_path.exists():
        return None
    
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"{YELLOW}Warning: Could not load {filename}: {e}{RESET}")
        return None


def safe_delete(resource_name: str, delete_func, *args, **kwargs):
    """Safely delete a resource with error handling"""
    try:
        print(f"{BLUE}Deleting {resource_name}...{RESET}")
        result = delete_func(*args, **kwargs)
        print(f"{GREEN}✓ Deleted {resource_name}{RESET}")
        return True
    except Exception as e:
        error_msg = str(e)
        if "ResourceNotFoundException" in error_msg or "NotFound" in error_msg or "does not exist" in error_msg.lower():
            print(f"{YELLOW}⊘ {resource_name} not found (already deleted){RESET}")
        else:
            print(f"{RED}✗ Failed to delete {resource_name}: {e}{RESET}")
        return False


def delete_runtime_agent(config: Dict[str, Any]):
    """Delete AgentCore Runtime agent"""
    if not config:
        print(f"{YELLOW}No runtime config found{RESET}")
        return
    
    client = boto3.client('bedrock-agentcore-control', region_name=REGION)
    agent_arn = config.get('agent_arn')
    
    if agent_arn:
        # Extract agent runtime ID from ARN
        agent_runtime_id = agent_arn.split('/')[-1]
        safe_delete(
            f"Runtime Agent ({agent_runtime_id})",
            client.delete_agent_runtime,
            agentRuntimeId=agent_runtime_id
        )


def delete_gateway_and_targets(config: Dict[str, Any]):
    """Delete Gateway targets and gateway"""
    if not config:
        print(f"{YELLOW}No gateway config found{RESET}")
        return
    
    client = boto3.client('bedrock-agentcore-control', region_name=REGION)
    gateway_id = config.get('gateway_id')
    
    if not gateway_id:
        return
    
    # List and delete all targets first
    try:
        print(f"{BLUE}Listing gateway targets...{RESET}")
        response = client.list_gateway_targets(gatewayIdentifier=gateway_id)
        targets = response.get('targets', [])
        
        for target in targets:
            target_id = target.get('targetId')
            target_name = target.get('name', target_id)
            safe_delete(
                f"Gateway Target ({target_name})",
                client.delete_gateway_target,
                gatewayIdentifier=gateway_id,
                targetId=target_id
            )
    except Exception as e:
        print(f"{YELLOW}Could not list gateway targets: {e}{RESET}")
    
    # Delete gateway
    safe_delete(
        f"Gateway ({gateway_id})",
        client.delete_gateway,
        gatewayIdentifier=gateway_id
    )


def delete_memory_resource(config: Dict[str, Any]):
    """Delete AgentCore Memory resource"""
    if not config:
        print(f"{YELLOW}No memory config found{RESET}")
        return
    
    from bedrock_agentcore_starter_toolkit.operations.memory.manager import MemoryManager
    
    memory_id = config.get('memory_id')
    if memory_id:
        manager = MemoryManager(region=REGION)
        safe_delete(
            f"Memory Resource ({memory_id})",
            manager.delete_memory,
            memory_id=memory_id
        )


def delete_lambda_function(config: Dict[str, Any]):
    """Delete Lambda function"""
    if not config:
        print(f"{YELLOW}No lambda config found{RESET}")
        return
    
    client = boto3.client('lambda', region_name=REGION)
    function_name = config.get('function_name')
    
    if function_name:
        safe_delete(
            f"Lambda Function ({function_name})",
            client.delete_function,
            FunctionName=function_name
        )


def delete_cognito_resources(config: Dict[str, Any]):
    """Delete Cognito user pool and domain"""
    if not config:
        print(f"{YELLOW}No cognito config found{RESET}")
        return
    
    client = boto3.client('cognito-idp', region_name=REGION)
    user_pool_id = config.get('user_pool_id')
    domain_prefix = config.get('domain_prefix')
    
    # Delete domain first
    if domain_prefix:
        safe_delete(
            f"Cognito Domain ({domain_prefix})",
            client.delete_user_pool_domain,
            Domain=domain_prefix,
            UserPoolId=user_pool_id
        )
        # Wait for domain deletion
        time.sleep(2)
    
    # Delete user pool
    if user_pool_id:
        safe_delete(
            f"Cognito User Pool ({user_pool_id})",
            client.delete_user_pool,
            UserPoolId=user_pool_id
        )


def delete_iam_role_and_policy(role_config: Dict[str, Any]):
    """Delete IAM role and its attached policies"""
    if not role_config:
        return
    
    client = boto3.client('iam', region_name=REGION)
    role_name = role_config.get('role_name')
    policy_arn = role_config.get('policy_arn')
    
    if not role_name:
        return
    
    try:
        # List and detach all attached policies
        print(f"{BLUE}Detaching policies from role {role_name}...{RESET}")
        response = client.list_attached_role_policies(RoleName=role_name)
        
        for policy in response.get('AttachedPolicies', []):
            policy_arn_to_detach = policy['PolicyArn']
            safe_delete(
                f"Policy attachment ({policy['PolicyName']})",
                client.detach_role_policy,
                RoleName=role_name,
                PolicyArn=policy_arn_to_detach
            )
    except Exception as e:
        print(f"{YELLOW}Could not list attached policies: {e}{RESET}")
    
    # Delete custom policy if exists
    if policy_arn:
        safe_delete(
            f"IAM Policy ({policy_arn.split('/')[-1]})",
            client.delete_policy,
            PolicyArn=policy_arn
        )
    
    # Delete role
    if role_name:
        safe_delete(
            f"IAM Role ({role_name})",
            client.delete_role,
            RoleName=role_name
        )


def delete_ecr_repository():
    """Delete ECR repository"""
    client = boto3.client('ecr', region_name=REGION)
    
    # Try common repository names
    repo_names = [
        'returns-refunds-agent',
        'returns_refunds_agent',
        'agentcore-runtime'
    ]
    
    for repo_name in repo_names:
        try:
            # Check if repository exists
            client.describe_repositories(repositoryNames=[repo_name])
            # If it exists, delete it
            safe_delete(
                f"ECR Repository ({repo_name})",
                client.delete_repository,
                repositoryName=repo_name,
                force=True  # Delete even if it contains images
            )
            break  # Stop after first successful deletion
        except client.exceptions.RepositoryNotFoundException:
            continue
        except Exception as e:
            print(f"{YELLOW}Could not check/delete ECR repository {repo_name}: {e}{RESET}")


def main():
    """Main cleanup function"""
    print(f"\n{RED}{'='*70}{RESET}")
    print(f"{RED}AWS RESOURCE CLEANUP - RETURNS/REFUNDS AGENT{RESET}")
    print(f"{RED}{'='*70}{RESET}\n")
    
    print(f"{YELLOW}This will delete the following resources in us-west-2:{RESET}")
    print(f"  • Runtime agent (deployed agent)")
    print(f"  • Gateway and its targets")
    print(f"  • Memory resource (customer data)")
    print(f"  • Lambda function")
    print(f"  • Cognito user pool (authentication)")
    print(f"  • IAM roles and policies")
    print(f"  • ECR repository (Docker images)")
    
    print(f"\n{RED}⚠️  WARNING: This action cannot be undone!{RESET}")
    print(f"{YELLOW}You have 5 seconds to cancel (Ctrl+C)...{RESET}\n")
    
    try:
        for i in range(5, 0, -1):
            print(f"{i}...", end=" ", flush=True)
            time.sleep(1)
        print("\n")
    except KeyboardInterrupt:
        print(f"\n\n{GREEN}Cleanup cancelled by user{RESET}")
        return
    
    print(f"{BLUE}Starting cleanup...{RESET}\n")
    
    # Load configurations
    runtime_config = load_config('runtime_config.json')
    gateway_config = load_config('gateway_config.json')
    memory_config = load_config('memory_config.json')
    lambda_config = load_config('lambda_config.json')
    cognito_config = load_config('cognito_config.json')
    runtime_role_config = load_config('runtime_execution_role_config.json')
    gateway_role_config = load_config('gateway_role_config.json')
    
    # Delete resources in order (respecting dependencies)
    print(f"\n{BLUE}Step 1: Deleting Runtime Agent{RESET}")
    delete_runtime_agent(runtime_config)
    
    print(f"\n{BLUE}Step 2: Deleting Gateway and Targets{RESET}")
    delete_gateway_and_targets(gateway_config)
    
    print(f"\n{BLUE}Step 3: Deleting Memory Resource{RESET}")
    delete_memory_resource(memory_config)
    
    print(f"\n{BLUE}Step 4: Deleting Lambda Function{RESET}")
    delete_lambda_function(lambda_config)
    
    print(f"\n{BLUE}Step 5: Deleting Cognito Resources{RESET}")
    delete_cognito_resources(cognito_config)
    
    print(f"\n{BLUE}Step 6: Deleting IAM Roles and Policies{RESET}")
    delete_iam_role_and_policy(runtime_role_config)
    delete_iam_role_and_policy(gateway_role_config)
    
    print(f"\n{BLUE}Step 7: Deleting ECR Repository{RESET}")
    delete_ecr_repository()
    
    print(f"\n{GREEN}{'='*70}{RESET}")
    print(f"{GREEN}Cleanup complete!{RESET}")
    print(f"{GREEN}{'='*70}{RESET}\n")
    
    print(f"{YELLOW}Note: Some resources may take a few minutes to fully delete.{RESET}")
    print(f"{YELLOW}Config files have been preserved for reference.{RESET}\n")


if __name__ == "__main__":
    main()
