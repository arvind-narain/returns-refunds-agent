#!/usr/bin/env python3
"""
Streamlit Chat Interface for AgentCore Runtime Agent

A user-friendly web interface to interact with the deployed returns agent.
"""

import streamlit as st
import json
import requests
import yaml
from bedrock_agentcore_starter_toolkit import Runtime
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Returns Assistant",
    page_icon="🔄",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #FF9900;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .user-message {
        background-color: #E8F4F8;
        border-left: 4px solid #0073BB;
    }
    .assistant-message {
        background-color: #F5F5F5;
        border-left: 4px solid #FF9900;
    }
    .info-box {
        background-color: #FFF3CD;
        border: 1px solid #FFE69C;
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'runtime' not in st.session_state:
    st.session_state.runtime = None
if 'bearer_token' not in st.session_state:
    st.session_state.bearer_token = None
if 'config_loaded' not in st.session_state:
    st.session_state.config_loaded = False

def load_configurations():
    """Load all configuration files"""
    try:
        with open('runtime_config.json') as f:
            runtime_config = json.load(f)
        
        with open('cognito_config.json') as f:
            cognito_config = json.load(f)
        
        with open('runtime_execution_role_config.json') as f:
            role_config = json.load(f)
        
        with open('.bedrock_agentcore.yaml') as f:
            yaml_config = yaml.safe_load(f)
        
        return runtime_config, cognito_config, role_config, yaml_config
    except FileNotFoundError as e:
        st.error(f"Configuration file not found: {e}")
        st.info("Please run the deployment script (19_deploy_agent.py) first.")
        return None, None, None, None

def get_oauth_token(cognito_config):
    """Get OAuth bearer token from Cognito"""
    try:
        token_endpoint = cognito_config["token_endpoint"]
        oauth_scopes = " ".join(cognito_config.get("scopes", ["gateway-api/read", "gateway-api/write"]))
        
        response = requests.post(
            token_endpoint,
            data={
                "grant_type": "client_credentials",
                "client_id": cognito_config["client_id"],
                "client_secret": cognito_config["client_secret"],
                "scope": oauth_scopes
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            st.error(f"Failed to get OAuth token: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error getting OAuth token: {e}")
        return None

def initialize_runtime(cognito_config, role_config, yaml_config):
    """Initialize the Runtime SDK"""
    try:
        runtime = Runtime()
        
        default_agent = yaml_config.get('default_agent')
        agent_config = yaml_config.get('agents', {}).get(default_agent, {})
        agent_name = agent_config.get('name')
        entrypoint = agent_config.get('entrypoint')
        
        auth_config = {
            "customJWTAuthorizer": {
                "allowedClients": [cognito_config["client_id"]],
                "discoveryUrl": cognito_config["discovery_url"]
            }
        }
        
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
        
        return runtime
    except Exception as e:
        st.error(f"Error initializing runtime: {e}")
        return None

def invoke_agent(runtime, bearer_token, user_message, actor_id):
    """Invoke the deployed agent"""
    try:
        payload = {
            "prompt": user_message,
            "actor_id": actor_id
        }
        
        response = runtime.invoke(payload, bearer_token=bearer_token)
        
        # Extract response text
        if isinstance(response, dict) and 'response' in response:
            return json.loads(response['response'])
        return str(response)
    except Exception as e:
        return f"Error invoking agent: {str(e)}"

# Main UI
st.markdown('<div class="main-header">🔄 Returns & Refunds Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Powered by Amazon Bedrock AgentCore Runtime</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Load configurations on first run
    if not st.session_state.config_loaded:
        with st.spinner("Loading configurations..."):
            runtime_config, cognito_config, role_config, yaml_config = load_configurations()
            
            if all([runtime_config, cognito_config, role_config, yaml_config]):
                # Get OAuth token
                bearer_token = get_oauth_token(cognito_config)
                if bearer_token:
                    st.session_state.bearer_token = bearer_token
                    
                    # Initialize runtime
                    runtime = initialize_runtime(cognito_config, role_config, yaml_config)
                    if runtime:
                        st.session_state.runtime = runtime
                        st.session_state.runtime_config = runtime_config
                        st.session_state.config_loaded = True
                        st.success("✅ Connected to agent!")
    
    if st.session_state.config_loaded:
        st.success("🟢 Agent Status: READY")
        
        with st.expander("📊 Agent Details"):
            st.write(f"**Agent ARN:**")
            st.code(st.session_state.runtime_config['agent_arn'], language="text")
            st.write(f"**Region:** {st.session_state.runtime_config['region']}")
            st.write(f"**Memory ID:** {st.session_state.runtime_config['memory_id']}")
            st.write(f"**Knowledge Base:** {st.session_state.runtime_config['knowledge_base_id']}")
        
        st.divider()
        
        # Actor ID input
        actor_id = st.text_input(
            "👤 Actor ID (User ID)",
            value="user_001",
            help="Unique identifier for the user - used for memory and personalization"
        )
        st.session_state.actor_id = actor_id
        
        st.divider()
        
        # Quick actions
        st.subheader("🚀 Quick Actions")
        if st.button("🔍 Check Order ORD-001"):
            st.session_state.quick_message = "Can you look up my order ORD-001?"
        if st.button("📋 Return Policy"):
            st.session_state.quick_message = "What is your return policy for electronics?"
        if st.button("💰 Calculate Refund"):
            st.session_state.quick_message = "I want to return a $500 laptop that's unopened. How much will I get back?"
        
        st.divider()
        
        if st.button("🗑️ Clear Chat History"):
            st.session_state.messages = []
            st.rerun()
    else:
        st.error("❌ Not connected")
        st.info("Please ensure all configuration files exist and the agent is deployed.")

# Main chat area
if st.session_state.config_loaded:
    # Display chat messages
    for message in st.session_state.messages:
        role = message["role"]
        content = message["content"]
        timestamp = message.get("timestamp", "")
        
        if role == "user":
            st.markdown(f'<div class="chat-message user-message"><strong>👤 You</strong> <small>({timestamp})</small><br>{content}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-message assistant-message"><strong>🤖 Assistant</strong> <small>({timestamp})</small><br>{content}</div>', unsafe_allow_html=True)
    
    # Handle quick message
    if 'quick_message' in st.session_state:
        user_message = st.session_state.quick_message
        del st.session_state.quick_message
        
        # Add user message
        timestamp = datetime.now().strftime("%H:%M:%S")
        st.session_state.messages.append({
            "role": "user",
            "content": user_message,
            "timestamp": timestamp
        })
        
        # Get agent response
        with st.spinner("🤔 Agent is thinking..."):
            response = invoke_agent(
                st.session_state.runtime,
                st.session_state.bearer_token,
                user_message,
                st.session_state.actor_id
            )
        
        # Add assistant response
        st.session_state.messages.append({
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })
        
        st.rerun()
    
    # Chat input
    user_input = st.chat_input("Type your message here...")
    
    if user_input:
        # Add user message
        timestamp = datetime.now().strftime("%H:%M:%S")
        st.session_state.messages.append({
            "role": "user",
            "content": user_input,
            "timestamp": timestamp
        })
        
        # Get agent response
        with st.spinner("🤔 Agent is thinking..."):
            response = invoke_agent(
                st.session_state.runtime,
                st.session_state.bearer_token,
                user_input,
                st.session_state.actor_id
            )
        
        # Add assistant response
        st.session_state.messages.append({
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })
        
        st.rerun()
    
    # Welcome message if no messages
    if len(st.session_state.messages) == 0:
        st.markdown("""
        <div class="info-box">
            <h3>👋 Welcome to the Returns & Refunds Assistant!</h3>
            <p>I can help you with:</p>
            <ul>
                <li>🔍 Looking up your orders</li>
                <li>✅ Checking return eligibility</li>
                <li>💰 Calculating refund amounts</li>
                <li>📋 Explaining return policies</li>
                <li>📧 Remembering your preferences</li>
            </ul>
            <p><strong>Try asking:</strong></p>
            <ul>
                <li>"Can you look up my order ORD-001?"</li>
                <li>"What's your return policy for electronics?"</li>
                <li>"I want to return a laptop, can you help?"</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
else:
    st.warning("⚠️ Please configure the agent in the sidebar first.")
    st.info("""
    **Setup Instructions:**
    1. Ensure you've deployed the agent using `19_deploy_agent.py`
    2. Verify all configuration files exist
    3. Check that the agent status is READY using `20_check_status.py`
    4. Refresh this page
    """)

# Footer
st.divider()
st.caption("Built with Amazon Bedrock AgentCore Runtime | Powered by Claude Sonnet 4.5")
