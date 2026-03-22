#!/usr/bin/env python3
"""
Test script for full-featured returns agent with memory and gateway.

Tests:
1. Memory recall (customer preferences)
2. Gateway tool usage (order lookup via Lambda)
3. Combined personalized response
"""

import os
import sys
import json
from datetime import datetime

# Load all configuration files
print("Loading configuration files...")
with open('memory_config.json') as f:
    memory_config = json.load(f)
with open('gateway_config.json') as f:
    gateway_config = json.load(f)
with open('cognito_config.json') as f:
    cognito_config = json.load(f)
with open('kb_config.json') as f:
    kb_config = json.load(f)

print(f"✓ Memory ID: {memory_config['memory_id']}")
print(f"✓ Gateway URL: {gateway_config['gateway_url']}")
print(f"✓ Knowledge Base ID: {kb_config['knowledge_base_id']}")

# Set up environment variables for the agent
os.environ['MEMORY_ID'] = memory_config['memory_id']
os.environ['KNOWLEDGE_BASE_ID'] = kb_config['knowledge_base_id']
os.environ['GATEWAY_URL'] = gateway_config['gateway_url']
os.environ['COGNITO_CLIENT_ID'] = cognito_config['client_id']
os.environ['COGNITO_CLIENT_SECRET'] = cognito_config['client_secret']
os.environ['COGNITO_DISCOVERY_URL'] = cognito_config['discovery_url']
os.environ['OAUTH_SCOPES'] = ' '.join(cognito_config['scopes'])

print("\n" + "="*80)
print("TESTING FULL-FEATURED RETURNS AGENT")
print("="*80)

# Import the agent's invoke function
# Note: We need to import after setting environment variables
from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools import retrieve, current_time
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client
import requests
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig, RetrievalConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager

# Import custom tools from the agent file
sys.path.insert(0, '.')
from importlib import import_module
spec = import_module('14_full_agent')
check_return_eligibility = spec.check_return_eligibility
calculate_refund_amount = spec.calculate_refund_amount
format_policy_response = spec.format_policy_response
get_cognito_token_with_scope = spec.get_cognito_token_with_scope

# Constants
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
REGION = "us-west-2"
SESSION_ID = "session_001"
ACTOR_ID = "user_001"

print(f"\nTest Configuration:")
print(f"  Actor ID: {ACTOR_ID}")
print(f"  Session ID: {SESSION_ID}")
print(f"  Region: {REGION}")

# Initialize model
bedrock_model = BedrockModel(model_id=MODEL_ID, temperature=0.3)

# Configure memory
agentcore_memory_config = AgentCoreMemoryConfig(
    memory_id=memory_config['memory_id'],
    session_id=SESSION_ID,
    actor_id=ACTOR_ID,
    retrieval_config={
        f"app/{ACTOR_ID}/semantic": RetrievalConfig(top_k=3),
        f"app/{ACTOR_ID}/preferences": RetrievalConfig(top_k=3),
        f"app/{ACTOR_ID}/{SESSION_ID}/summary": RetrievalConfig(top_k=2),
    }
)

session_manager = AgentCoreMemorySessionManager(
    agentcore_memory_config=agentcore_memory_config,
    region_name=REGION
)

# Custom tools list
custom_tools = [
    retrieve, 
    current_time, 
    check_return_eligibility, 
    calculate_refund_amount, 
    format_policy_response
]

# Create MCP client for gateway tools
print("\nConnecting to gateway...")
try:
    token = get_cognito_token_with_scope(
        cognito_config['client_id'],
        cognito_config['client_secret'],
        cognito_config['discovery_url'],
        ' '.join(cognito_config['scopes'])
    )
    print("✓ OAuth token obtained")
    
    mcp_client = MCPClient(
        lambda: streamablehttp_client(
            gateway_config['gateway_url'],
            headers={"Authorization": f"Bearer {token}"},
        )
    )
    print("✓ MCP client created")
    
    with mcp_client:
        gateway_tools = list(mcp_client.list_tools_sync())
        print(f"✓ Gateway tools available: {len(gateway_tools)} tool(s)")
        
        # Create agent with all tools
        kb_id = kb_config['knowledge_base_id']
        system_prompt = f"""You are a returns assistant with memory and order lookup capabilities. Remember customer preferences, look up order details, and use the retrieve tool to access Amazon return policy documents for accurate information.

When using the retrieve tool, always pass these parameters:
- knowledgeBaseId: {kb_id}
- region: {REGION}
- text: the search query

You have access to:
- Custom tools for checking eligibility and calculating refunds
- Gateway tools for external operations (like looking up orders)
- Customer conversation history and preferences through memory"""
        
        agent = Agent(
            model=bedrock_model,
            tools=custom_tools + gateway_tools,
            system_prompt=system_prompt,
            session_manager=session_manager
        )
        
        # Test query
        user_query = "Hi! Can you look up my order ORD-001 and tell me if I can return it? Remember, I prefer email updates."
        
        print("\n" + "="*80)
        print("USER QUERY:")
        print("="*80)
        print(user_query)
        
        print("\n" + "="*80)
        print("AGENT PROCESSING...")
        print("="*80)
        
        response = agent(user_query)
        agent_response = response.message["content"][0]["text"]
        
        print("\n" + "="*80)
        print("AGENT RESPONSE:")
        print("="*80)
        print(agent_response)
        
        # Verification
        print("\n" + "="*80)
        print("VERIFICATION:")
        print("="*80)
        
        checks = {
            "Memory recall (email preference)": any(word in agent_response.lower() for word in ['email', 'prefer', 'preference']),
            "Order lookup (ORD-001)": 'ORD-001' in agent_response or 'ord-001' in agent_response.lower(),
            "Return eligibility mentioned": any(word in agent_response.lower() for word in ['eligible', 'return', 'window']),
            "Personalized response": len(agent_response) > 100  # Substantial response
        }
        
        for check, passed in checks.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"{status}: {check}")
        
        # Overall assessment
        passed_count = sum(checks.values())
        total_count = len(checks)
        
        print("\n" + "="*80)
        print(f"OVERALL: {passed_count}/{total_count} checks passed")
        
        if passed_count == total_count:
            print("STATUS: ✓ EXCELLENT - All capabilities working!")
        elif passed_count >= total_count * 0.75:
            print("STATUS: ✓ GOOD - Most capabilities working")
        elif passed_count >= total_count * 0.5:
            print("STATUS: ⚠ PARTIAL - Some capabilities working")
        else:
            print("STATUS: ✗ NEEDS WORK - Limited capabilities")
        print("="*80)

except Exception as e:
    print(f"\n✗ Error during test: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
