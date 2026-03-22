"""
AgentCore Runtime Agent: returns_agent_runtime
Production-ready returns assistant with comprehensive error handling

This agent is ready to deploy to AgentCore Runtime with:
1. BedrockAgentCoreApp entrypoint
2. Memory integration
3. Gateway tools
4. Knowledge Base access
5. Custom tools: check_return_eligibility, calculate_refund_amount, format_policy_response
6. Comprehensive error handling and logging
"""

import os
import json
import logging
from datetime import datetime
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools import retrieve
from strands_tools import current_time
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client
import requests
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig, RetrievalConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
REGION = "us-west-2"
SESSION_ID = "default-session"
ACTOR_ID = "default-actor"

# Initialize app only (don't initialize model at module level)
app = BedrockAgentCoreApp()

# Environment variables - loaded at runtime, not at module import
# These will be accessed inside the invoke function
kb_id = os.environ.get("KNOWLEDGE_BASE_ID", "YOUR_KB_ID_HERE")
logger.info(f"✓ Knowledge Base ID: {kb_id}")

# ============================================================================
# CUSTOM TOOLS
# ============================================================================

@tool
def check_return_eligibility(purchase_date: str, item_category: str, order_id: str) -> dict:
    """Check if an item is eligible for return based on purchase date and category"""
    try:
        purchase_dt = datetime.strptime(purchase_date, '%Y-%m-%d')
        days_since_purchase = (datetime.now() - purchase_dt).days
        
        # Define return windows by category
        return_windows = {
            'electronics': 90,
            'clothing': 30,
            'books': 30,
            'home': 30,
            'toys': 30,
            'default': 30
        }
        
        # Non-returnable categories
        non_returnable = ['perishables', 'digital', 'gift_cards', 'personalized']
        
        category_lower = item_category.lower()
        
        if category_lower in non_returnable:
            return {
                'eligible': False,
                'reason': f'{item_category} items are not eligible for return',
                'order_id': order_id,
                'days_since_purchase': days_since_purchase
            }
        
        window = return_windows.get(category_lower, return_windows['default'])
        
        if days_since_purchase <= window:
            return {
                'eligible': True,
                'reason': f'Item is within {window}-day return window',
                'order_id': order_id,
                'days_since_purchase': days_since_purchase,
                'days_remaining': window - days_since_purchase
            }
        else:
            return {
                'eligible': False,
                'reason': f'Return window of {window} days has expired',
                'order_id': order_id,
                'days_since_purchase': days_since_purchase
            }
    except ValueError as e:
        logger.error(f"Date parsing error in check_return_eligibility: {e}")
        return {
            'eligible': False,
            'reason': 'Invalid date format. Please use YYYY-MM-DD',
            'order_id': order_id
        }
    except Exception as e:
        logger.error(f"Unexpected error in check_return_eligibility: {e}")
        return {
            'eligible': False,
            'reason': f'Error checking eligibility: {str(e)}',
            'order_id': order_id
        }

@tool
def calculate_refund_amount(original_price: float, item_condition: str, return_reason: str) -> dict:
    """Calculate refund amount based on price, condition, and return reason"""
    try:
        condition_lower = item_condition.lower()
        reason_lower = return_reason.lower()
        
        refund_percentage = 100
        restocking_fee = 0
        shipping_refund = True
        
        # Defective or wrong item - full refund
        if reason_lower in ['defective', 'wrong_item']:
            refund_percentage = 100
            restocking_fee = 0
            shipping_refund = True
        # Changed mind - depends on condition
        else:
            if condition_lower == 'unopened':
                refund_percentage = 100
                restocking_fee = 0
            elif condition_lower == 'opened_unused':
                refund_percentage = 100
                restocking_fee = original_price * 0.15  # 15% restocking fee
            elif condition_lower == 'used':
                refund_percentage = 80
                restocking_fee = original_price * 0.20  # 20% restocking fee
            elif condition_lower == 'damaged':
                refund_percentage = 50
                restocking_fee = 0
            else:
                refund_percentage = 100
                restocking_fee = 0
            
            shipping_refund = False
        
        refund_amount = (original_price * refund_percentage / 100) - restocking_fee
        refund_amount = max(0, refund_amount)  # Ensure non-negative
        
        return {
            'original_price': original_price,
            'refund_amount': round(refund_amount, 2),
            'refund_percentage': refund_percentage,
            'restocking_fee': round(restocking_fee, 2),
            'shipping_refunded': shipping_refund,
            'item_condition': item_condition,
            'return_reason': return_reason
        }
    except Exception as e:
        logger.error(f"Error in calculate_refund_amount: {e}")
        return {
            'error': f'Error calculating refund: {str(e)}',
            'original_price': original_price,
            'item_condition': item_condition,
            'return_reason': return_reason
        }

@tool
def format_policy_response(policy_text: str, category: str = 'general') -> str:
    """Format policy information in a customer-friendly way"""
    try:
        formatted = f"📋 Return Policy Information ({category.title()})\n"
        formatted += "=" * 50 + "\n\n"
        
        # Split into sections if possible
        sections = policy_text.split('\n\n')
        
        for i, section in enumerate(sections, 1):
            if section.strip():
                # Check if it's a header (short line, no punctuation at end)
                if len(section) < 60 and not section.strip().endswith('.'):
                    formatted += f"\n📌 {section.strip()}\n"
                    formatted += "-" * 40 + "\n"
                else:
                    # Format as bullet points if multiple sentences
                    sentences = [s.strip() for s in section.split('.') if s.strip()]
                    if len(sentences) > 1:
                        for sentence in sentences:
                            if sentence:
                                formatted += f"  • {sentence}.\n"
                    else:
                        formatted += f"  {section.strip()}\n"
                formatted += "\n"
        
        formatted += "\n" + "=" * 50 + "\n"
        formatted += "💡 Tip: Contact customer service for specific questions about your order.\n"
        
        return formatted
    except Exception as e:
        logger.error(f"Error in format_policy_response: {e}")
        return f"Error formatting policy: {str(e)}\n\nOriginal text:\n{policy_text}"

# ============================================================================
# GATEWAY HELPER FUNCTIONS
# ============================================================================

def get_cognito_token_with_scope(client_id, client_secret, discovery_url, scope):
    """Get Cognito bearer token with a specific OAuth scope"""
    try:
        # Extract token endpoint from discovery URL
        discovery_response = requests.get(discovery_url, timeout=10)
        discovery_response.raise_for_status()
        token_endpoint = discovery_response.json()['token_endpoint']
        
        # Get token using client credentials flow
        response = requests.post(
            token_endpoint,
            data={
                'grant_type': 'client_credentials',
                'client_id': client_id,
                'client_secret': client_secret,
                'scope': scope
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=10
        )
        
        response.raise_for_status()
        return response.json()["access_token"]
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error getting Cognito token: {e}")
        raise
    except KeyError as e:
        logger.error(f"Invalid response from Cognito: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting Cognito token: {e}")
        raise

def create_mcp_client():
    """Create MCP client for gateway access with error handling"""
    try:
        # Get environment variables
        gateway_url = os.environ.get("GATEWAY_URL")
        cognito_client_id = os.environ.get("COGNITO_CLIENT_ID")
        cognito_client_secret = os.environ.get("COGNITO_CLIENT_SECRET")
        cognito_discovery_url = os.environ.get("COGNITO_DISCOVERY_URL")
        oauth_scopes = os.environ.get("OAUTH_SCOPES", "gateway-api/read gateway-api/write")
        
        if not all([gateway_url, cognito_client_id, cognito_client_secret, cognito_discovery_url]):
            logger.warning("Gateway configuration incomplete - gateway tools will not be available")
            return None
        
        logger.info("Obtaining OAuth token for gateway access...")
        token = get_cognito_token_with_scope(
            cognito_client_id,
            cognito_client_secret,
            cognito_discovery_url,
            oauth_scopes
        )
        
        logger.info("Creating MCP client...")
        return MCPClient(
            lambda: streamablehttp_client(
                gateway_url,
                headers={"Authorization": f"Bearer {token}"},
            )
        )
    except Exception as e:
        logger.error(f"Failed to create MCP client: {e}")
        return None

system_prompt = f"""Production returns assistant with full memory and gateway capabilities. Use the retrieve tool to access Amazon return policy documents for accurate information.

When using the retrieve tool, always pass these parameters:
- knowledgeBaseId: {kb_id}
- region: {REGION}
- text: the search query

You have access to:
- Custom tools for checking eligibility and calculating refunds
- Gateway tools for external operations (like looking up orders)
- Customer conversation history and preferences through memory"""

@app.entrypoint
def invoke(payload, context=None):
    """AgentCore Runtime entrypoint with comprehensive error handling"""
    try:
        logger.info("=== Agent Invocation Started ===")
        logger.info(f"Payload: {json.dumps(payload, default=str)}")
        
        # Initialize model inside the function (not at module level)
        logger.info("Initializing Bedrock model...")
        bedrock_model = BedrockModel(model_id=MODEL_ID, temperature=0.3)
        
        # Get environment variables
        memory_id = os.environ.get("MEMORY_ID")
        if not memory_id:
            error_msg = "Error: MEMORY_ID environment variable is required"
            logger.error(error_msg)
            return error_msg
        
        session_id = context.session_id if context else SESSION_ID
        actor_id = payload.get("actor_id", ACTOR_ID)
        
        logger.info(f"Session ID: {session_id}, Actor ID: {actor_id}")
        
        # Configure memory with retrieval settings
        logger.info("Configuring memory...")
        agentcore_memory_config = AgentCoreMemoryConfig(
            memory_id=memory_id,
            session_id=session_id,
            actor_id=actor_id,
            retrieval_config={
                f"app/{actor_id}/semantic": RetrievalConfig(top_k=3),
                f"app/{actor_id}/preferences": RetrievalConfig(top_k=3),
                f"app/{actor_id}/{session_id}/summary": RetrievalConfig(top_k=2),
            }
        )
        
        session_manager = AgentCoreMemorySessionManager(
            agentcore_memory_config=agentcore_memory_config,
            region_name=REGION
        )
        
        # Custom tools list - ALL tools from original agent
        custom_tools = [
            retrieve, 
            current_time, 
            check_return_eligibility, 
            calculate_refund_amount, 
            format_policy_response
        ]
        logger.info(f"Loaded {len(custom_tools)} custom tools")
        
        # Try to create MCP client for gateway tools
        mcp_client = create_mcp_client()
        
        if mcp_client:
            try:
                logger.info("Gateway client available - loading gateway tools...")
                # Keep MCP client active during agent execution
                with mcp_client:
                    # Get gateway tools from MCP client
                    gateway_tools = list(mcp_client.list_tools_sync())
                    logger.info(f"Loaded {len(gateway_tools)} gateway tools")
                    
                    # Create agent with all tools
                    agent = Agent(
                        model=bedrock_model,
                        tools=custom_tools + gateway_tools,
                        system_prompt=system_prompt,
                        session_manager=session_manager
                    )
                    
                    user_input = payload.get("prompt", "")
                    logger.info(f"Processing user input: {user_input[:100]}...")
                    
                    response = agent(user_input)
                    result = response.message["content"][0]["text"]
                    
                    logger.info("=== Agent Invocation Completed Successfully ===")
                    return result
                    
            except Exception as e:
                logger.warning(f"Failed to use gateway tools: {e}")
                logger.info("Falling back to agent without gateway tools")
                # Fall back to agent without gateway tools
        else:
            logger.info("Gateway client not available - proceeding without gateway tools")
        
        # Create agent without gateway tools (fallback)
        agent = Agent(
            model=bedrock_model,
            tools=custom_tools,
            system_prompt=system_prompt,
            session_manager=session_manager
        )
        
        user_input = payload.get("prompt", "")
        logger.info(f"Processing user input: {user_input[:100]}...")
        
        response = agent(user_input)
        result = response.message["content"][0]["text"]
        
        logger.info("=== Agent Invocation Completed Successfully ===")
        return result
    
    except Exception as e:
        error_msg = f"Agent invocation failed: {str(e)}"
        logger.error(error_msg)
        logger.exception("Full traceback:")
        return f"I apologize, but I encountered an error processing your request. Please try again or contact support if the issue persists. Error: {str(e)}"

if __name__ == "__main__":
    app.run()
