---
title: Repository Overview - Returns & Refunds Agent
created: 2026-03-22
repository: https://github.com/arvind-narain/returns-refunds-agent
---

# Repository Overview: Returns & Refunds Agent

## What the Agent Does (User Perspective)

From a customer's perspective, this AI agent provides:

- **Return Eligibility Checks**: Determines if purchased items can be returned based on purchase date and product category (90-day window for electronics, 30-day for other items)
- **Refund Calculations**: Calculates exact refund amounts considering item condition (unopened, opened, used, damaged), return reason (defective, wrong item, changed mind), and applicable restocking fees (15-20%)
- **Policy Information**: Retrieves and formats return policy documents from a knowledge base in customer-friendly language with clear sections and bullet points
- **Order Lookup**: Fetches order details (product name, purchase date, amount, eligibility status) by order ID through external API integration
- **Conversational Memory**: Remembers customer preferences (e.g., "prefers email updates") and conversation history across sessions for personalized service
- **Multi-turn Conversations**: Maintains context throughout the conversation, allowing customers to ask follow-up questions without repeating information

## Key Components

### Agent Definitions

**Production Agent** (`src/agents/17_runtime_agent.py`)
- Runtime-ready agent with `@app.entrypoint` decorator for AgentCore Runtime deployment
- Integrates all features: memory, gateway, knowledge base, custom tools
- Comprehensive error handling and logging
- Graceful degradation when optional services unavailable
- Model: Claude Sonnet 4.5 (us.anthropic.claude-sonnet-4-5-20250929-v1:0)
- Temperature: 0.3 for consistent, accurate responses

**Development Agents**
- `src/agents/01_returns_refunds_agent.py` - Basic agent with custom tools only
- `src/agents/06_memory_enabled_agent.py` - Agent with memory integration
- `src/agents/14_full_agent.py` - Full-featured agent with all integrations (pre-runtime)

### Custom Tools

**1. check_return_eligibility** (`@tool` decorator)
- **Input**: purchase_date (YYYY-MM-DD), item_category, order_id
- **Logic**: 
  - Electronics: 90-day return window
  - Clothing, books, home, toys: 30-day window
  - Non-returnable: perishables, digital, gift_cards, personalized
- **Output**: Eligibility status, reason, days remaining/since purchase
- **Error Handling**: Date format validation, graceful error messages

**2. calculate_refund_amount** (`@tool` decorator)
- **Input**: original_price, item_condition, return_reason
- **Logic**:
  - Defective/wrong_item: 100% refund, no fees, shipping refunded
  - Unopened: 100% refund, no fees
  - Opened_unused: 100% refund, 15% restocking fee
  - Used: 80% refund, 20% restocking fee
  - Damaged: 50% refund, no fees
- **Output**: Refund amount, breakdown, fees, shipping refund status
- **Validation**: Non-negative amounts, 2 decimal place rounding

**3. format_policy_response** (`@tool` decorator)
- **Input**: policy_text, category (optional)
- **Logic**: Parses text into sections, adds headers, converts to bullet points
- **Output**: Customer-friendly formatted text with emoji icons
- **Enhancement**: Adds helpful tips and contact information

### AWS Resources & Integrations

**AgentCore Memory** (DynamoDB-backed)
- **Resource ID**: Stored in `memory_config.json`
- **Strategies**:
  - Summary: `app/{actorId}/{sessionId}/summary` - Conversation summaries per session
  - Preferences: `app/{actorId}/preferences` - User preferences (cross-session)
  - Semantic: `app/{actorId}/semantic` - Factual information with embeddings
- **Retrieval**: Top-k configuration (semantic=3, preferences=3, summary=2)
- **Processing**: Asynchronous (20-30 seconds for strategy processing)
- **Isolation**: Actor-based namespaces prevent cross-user data leakage

**AgentCore Gateway** (MCP Protocol)
- **Resource ID**: Stored in `gateway_config.json`
- **Protocol**: Model Context Protocol (MCP)
- **Authentication**: OAuth 2.0 via Cognito (JWT bearer tokens)
- **Authorizer**: CUSTOM_JWT with Cognito discovery URL
- **Targets**: Lambda functions exposed as tools
- **Scopes**: `gateway-api/read`, `gateway-api/write`

**Lambda Function** (OrderLookupFunction)
- **ARN**: Stored in `lambda_config.json`
- **Runtime**: Python 3.12
- **Purpose**: Mock order database for testing
- **Sample Orders**:
  - ORD-001: Dell XPS 15 Laptop (15 days old, eligible)
  - ORD-002: iPhone 13 Pro (45 days old, expired)
  - ORD-003: Samsung Galaxy Tab S8 (5 days old, defective, eligible)
- **Tool Name**: `lookup_order`
- **Gateway Integration**: Exposed through AgentCore Gateway as MCP tool

**Cognito User Pool** (OAuth 2.0)
- **Configuration**: Stored in `cognito_config.json`
- **Flow**: Client Credentials Grant
- **Components**:
  - User Pool: Identity provider
  - App Client: OAuth client with client_id and client_secret
  - Resource Server: Custom scopes for gateway access
  - Domain: Token endpoint for OAuth flow
- **Discovery URL**: IDP format (`https://cognito-idp.{region}.amazonaws.com/{pool_id}/.well-known/openid-configuration`)

**Knowledge Base** (Bedrock)
- **ID**: Stored in `kb_config.json`
- **Backend**: S3 + Vector embeddings
- **Content**: Return policies, FAQs, policy documents
- **Retrieval**: Semantic search via `retrieve` tool
- **Integration**: Built-in Strands tool with knowledgeBaseId parameter

**IAM Roles**
- **Gateway Execution Role**: `gateway_role_config.json`
  - Trust policy: bedrock-agentcore.amazonaws.com
  - Permissions: Lambda invocation
- **Runtime Execution Role**: `runtime_execution_role_config.json`
  - Trust policy: bedrock-agentcore.amazonaws.com
  - Permissions: Bedrock, Memory, Gateway, KB, CloudWatch, X-Ray, ECR

**AgentCore Runtime**
- **Agent ARN**: Stored in `runtime_config.json`
- **Deployment**: Serverless, auto-scaling
- **Platform**: linux/arm64
- **Container**: Docker with Python 3.12
- **Observability**: CloudWatch Logs, X-Ray traces
- **Session Timeout**: 15 minutes idle timeout
- **Entry Point**: `17_runtime_agent.py` with `@app.entrypoint`

### Infrastructure Templates

**Deployment Configuration** (`.bedrock_agentcore.yaml`)
- Agent name, entrypoint, execution role
- AWS account, region, ECR settings
- Network configuration (PUBLIC mode)
- Authorizer configuration (Cognito JWT)
- Memory mode (NO_MEMORY - managed in code)
- Observability settings (enabled)

**Docker Configuration** (`Dockerfile`)
- Base image: `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`
- Package manager: uv (fast Python package installer)
- Dependencies: Installed from `requirements.txt`
- Instrumentation: OpenTelemetry for observability
- Non-root user: bedrock_agentcore (UID 1000)
- Exposed ports: 9000, 8000, 8080
- Entry command: `opentelemetry-instrument python -m 17_runtime_agent`

**Dependencies** (`requirements.txt`)
```
strands-agents>=0.1.0
strands-agents-tools>=0.1.0
bedrock-agentcore>=0.1.0
bedrock-agentcore-starter-toolkit>=0.1.0
boto3>=1.34.0
requests>=2.31.0
```

**UI Dependencies** (`requirements_streamlit.txt`)
```
streamlit>=1.28.0
requests>=2.31.0
```

## Main Entry Points

### Infrastructure Setup Scripts

**Memory Setup**
- `src/infrastructure/03_create_memory.py` - Creates AgentCore Memory with 3 strategies
- `src/infrastructure/04_seed_memory.py` - Seeds memory with sample conversations

**Authentication Setup**
- `src/infrastructure/08_create_cognito.py` - Creates Cognito user pool with OAuth 2.0

**IAM Setup**
- `src/infrastructure/09_create_gateway_role.py` - Creates gateway execution role
- `src/infrastructure/16_create_runtime_role.py` - Creates runtime execution role

**Gateway Setup**
- `src/infrastructure/10_create_lambda.py` - Creates Lambda function for order lookup
- `src/infrastructure/11_create_gateway.py` - Creates AgentCore Gateway
- `src/infrastructure/12_add_lambda_to_gateway.py` - Registers Lambda as gateway target
- `src/infrastructure/13_list_gateway_targets.py` - Lists all gateway targets

### Deployment Scripts

**Agent Deployment**
- `scripts/19_deploy_agent.py` - Deploys agent to AgentCore Runtime
  - Loads all configuration files
  - Configures runtime settings
  - Sets environment variables
  - Initiates deployment (5-10 minutes)
  - Saves agent ARN to `runtime_config.json`

**Operations**
- `scripts/20_check_status.py` - Monitors deployment status (polls until READY/FAILED)
- `scripts/21_invoke_agent.py` - Invokes deployed agent with OAuth authentication
- `scripts/22_get_dashboard.py` - Gets CloudWatch GenAI Observability dashboard URL
- `scripts/23_get_logs_info.py` - Gets log group info and AWS CLI commands

### Test Scripts

**Local Testing**
- `src/tests/02_test_agent.py` - Tests basic agent with custom tools
- `src/tests/05_test_memory.py` - Tests memory retrieval
- `src/tests/07_test_memory_agent.py` - Tests agent with memory integration
- `src/tests/15_test_full_agent.py` - Tests full agent with all features

### User Interface

**Streamlit Web App** (`src/ui/streamlit_app.py`)
- Interactive chat interface
- OAuth token management
- Actor ID selection
- Quick action buttons
- Chat history display
- Agent status monitoring
- Launch script: `src/ui/run_streamlit.sh`

### Handler Functions

**AgentCore Runtime Entry Point**
```python
@app.entrypoint
def invoke(payload, context=None):
    """
    Main entry point for AgentCore Runtime
    
    Args:
        payload: Dict with 'prompt' and optional 'actor_id'
        context: Runtime context with session_id
    
    Returns:
        str: Agent response text
    """
```

**Key Functions in 17_runtime_agent.py**
- `get_cognito_token_with_scope()` - Obtains OAuth token from Cognito
- `create_mcp_client()` - Creates MCP client for gateway access
- `check_return_eligibility()` - Custom tool for eligibility checks
- `calculate_refund_amount()` - Custom tool for refund calculations
- `format_policy_response()` - Custom tool for policy formatting

### Configuration Files

**Generated by Infrastructure Scripts** (excluded from Git)
- `memory_config.json` - Memory resource ID and configuration
- `cognito_config.json` - Cognito client ID, secret, discovery URL
- `gateway_config.json` - Gateway ID, URL, ARN
- `gateway_role_config.json` - Gateway IAM role ARN
- `lambda_config.json` - Lambda function ARN and tool schema
- `runtime_execution_role_config.json` - Runtime IAM role ARN
- `runtime_config.json` - Deployed agent ARN and configuration
- `kb_config.json` - Knowledge base ID

**Version Controlled**
- `.bedrock_agentcore.yaml` - Runtime deployment configuration
- `Dockerfile` - Container build instructions
- `requirements.txt` - Python dependencies
- `requirements_streamlit.txt` - UI dependencies
- `.dockerignore` - Files excluded from Docker build
- `.gitignore` - Files excluded from Git (includes all config JSONs)

## Existing Documentation

### Primary Documentation

**README.md** (Root)
- Project overview with badges (License, Python, AWS)
- Architecture diagram
- Quick start guide (5 steps: clone, install, deploy infra, deploy agent, launch UI)
- Project structure tree
- Custom tools description
- Monitoring & observability commands
- Testing instructions
- Security features
- Feature checklist
- Links to external documentation (AgentCore, Strands, Bedrock)
- Contributing guidelines
- License information (MIT)

**docs/ARCHITECTURE.md**
- Detailed system architecture with ASCII diagrams
- Component details for each layer:
  - User Interface Layer (Streamlit UI, CLI scripts)
  - Authentication Layer (Cognito OAuth 2.0)
  - AgentCore Runtime (agent container, tools, memory)
  - Data Layer (Memory, Gateway, Knowledge Base)
  - Observability Layer (CloudWatch, X-Ray, GenAI Dashboard)
- Data flow diagrams:
  - Request flow (user → UI → auth → runtime → agent → tools)
  - Memory flow (event creation → processing → retrieval)
  - Gateway flow (tool call → OAuth → MCP → Lambda)
- Scalability considerations (auto-scaling, performance, cost)
- Security architecture (network, authentication, authorization)
- Deployment architecture (IaC, CI/CD, monitoring)

**docs/SETUP.md**
- Prerequisites (AWS account, CLI, Bedrock access, Python)
- Required AWS permissions list
- Installation steps (clone, install, configure)
- Deployment sequence in 7 phases:
  - Phase 1: Memory Setup (create, seed, test)
  - Phase 2: Authentication (Cognito)
  - Phase 3: IAM Roles (gateway, runtime)
  - Phase 4: Gateway Setup (Lambda, gateway, targets)
  - Phase 5: Agent Deployment (deploy, monitor)
  - Phase 6: Testing (invoke agent)
  - Phase 7: UI Launch (Streamlit)
- Configuration files reference
- Troubleshooting guide (deployment, agent, auth, memory issues)
- Next steps links

### Spec Documentation (spec-driven-v1 branch)

**requirements.md** (`.kiro/specs/returns-refunds-agent/`)
- EARS-formatted requirements (WHEN, WHERE, IF-THEN, WHILE)
- 50+ functional requirements with unique IDs
- Non-functional requirements (performance, security, reliability)
- 8 user stories with acceptance criteria
- Requirements traceability matrix
- Constraints, assumptions, dependencies
- INCOSE quality rules compliance

**design.md** (`.kiro/specs/returns-refunds-agent/`)
- Design overview and technology stack
- Component diagrams and sequence diagrams
- Detailed component design (agent core, tools, memory, gateway)
- Data models and configuration management
- Error handling strategy
- Security and observability design
- Testing strategy
- Design decisions log

**tasks.md** (`.kiro/specs/returns-refunds-agent/`)
- 29 implementation tasks across 8 epics
- Task details: priority, effort, dependencies, acceptance criteria
- Critical path analysis
- Dependencies graph
- Total estimated effort: 71.5 hours

### Workflow Documentation

**agentcore-mcp-workflow.md** (`.kiro/steering/`)
- Core workflow rules for AgentCore development
- MCP tool usage patterns (Type 1 vs Type 2 tasks)
- Critical data structures (memory strategies, messages, Cognito URLs)
- API validation commands for all services
- Task mapping table (task → MCP tool)
- Reference tables (service clients, config files, defaults)
- Common mistakes and corrections
- Example workflows

### MCP Server Documentation

**agentcore-mcp-server/** (Local MCP server implementation)
- `server.py` - FastMCP server with all AgentCore tools
- `handlers/` - Organized by service:
  - `memory_handlers.py` - Memory operations
  - `gateway_handlers.py` - Gateway operations
  - `runtime_handlers.py` - Runtime deployment
  - `observability_handlers.py` - Monitoring tools
  - `strands_handlers.py` - Agent generation
  - `identity_handlers.py` - IAM role creation

## Data Flow Summary

### User Request Flow
1. User sends message via Streamlit UI or CLI
2. UI obtains OAuth token from Cognito
3. Request sent to AgentCore Runtime with bearer token
4. Runtime validates token and invokes agent
5. Agent retrieves memory context (preferences, history, summaries)
6. Agent processes request with Claude Sonnet 4.5
7. Agent calls tools as needed (custom, gateway, KB)
8. Agent stores conversation in memory
9. Response returned to user

### Memory Flow
1. Conversation turn stored as event (USER/ASSISTANT messages)
2. AgentCore Memory processes asynchronously (20-30 seconds)
3. Preferences extracted → preferences namespace
4. Facts embedded → semantic namespace
5. Summary generated → summary namespace
6. Next request retrieves relevant memories by namespace

### Gateway Flow
1. Agent decides to call gateway tool (e.g., lookup_order)
2. MCP client obtains OAuth token from Cognito
3. MCP request sent to Gateway with bearer token
4. Gateway validates token and invokes Lambda
5. Lambda processes request (order lookup)
6. Response returned through gateway to agent
7. Agent incorporates data into response

## Technology Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| AI Model | Claude Sonnet 4.5 | Natural language understanding |
| Agent Framework | Strands Agents | Agent orchestration |
| Runtime | AgentCore Runtime | Serverless deployment |
| Memory | AgentCore Memory | Persistent state |
| Gateway | AgentCore Gateway | External API integration |
| Knowledge Base | Bedrock KB | Document retrieval |
| Authentication | Cognito | OAuth 2.0 |
| Compute | Lambda | Order lookup function |
| Observability | CloudWatch + X-Ray | Logging and tracing |
| Container | Docker | Agent packaging |
| Language | Python 3.12 | Implementation |
| UI | Streamlit | Web interface |
| IaC | Python scripts | Infrastructure setup |

## Repository Statistics

- **Total Scripts**: 23 (9 infrastructure, 5 deployment/ops, 4 tests, 4 agents, 1 UI)
- **Configuration Files**: 8 JSON files (excluded from Git)
- **Documentation Files**: 6 (README, ARCHITECTURE, SETUP, 3 spec files)
- **Custom Tools**: 3 (@tool decorated functions)
- **AWS Services**: 10 (Bedrock, AgentCore Runtime/Memory/Gateway, Cognito, Lambda, IAM, CloudWatch, X-Ray, ECR)
- **Lines of Code**: ~10,000+ (estimated from commit history)
- **Deployment Time**: 5-10 minutes (automated)
- **Development Approach**: Vibe coding → Spec-driven (transition in progress)

---

**Last Updated**: 2026-03-22  
**Repository**: https://github.com/arvind-narain/returns-refunds-agent  
**Branch**: main (production), spec-driven-v1 (spec development)  
**Status**: Production-ready, deployed to AgentCore Runtime
