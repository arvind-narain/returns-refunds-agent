# Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User Interface Layer                         │
│  ┌──────────────────┐              ┌──────────────────┐            │
│  │  Streamlit UI    │              │   CLI Scripts    │            │
│  │  (Web Chat)      │              │  (Direct Invoke) │            │
│  └────────┬─────────┘              └────────┬─────────┘            │
└───────────┼────────────────────────────────┼──────────────────────┘
            │                                 │
            │         OAuth 2.0 (Cognito)     │
            └────────────────┬────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────────┐
│                  AgentCore Runtime (Serverless)                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              Returns & Refunds Agent                         │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────┐    │   │
│  │  │  Custom    │  │  Built-in  │  │  Memory Manager    │    │   │
│  │  │  Tools     │  │  Tools     │  │  (Session State)   │    │   │
│  │  └────────────┘  └────────────┘  └────────────────────┘    │   │
│  │  • Eligibility  • current_time   • Preferences             │   │
│  │  • Refund Calc  • retrieve       • History                 │   │
│  │  • Formatting                     • Summaries               │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                             │                                        │
│  ┌──────────────────────────┼────────────────────────────────────┐ │
│  │         Claude Sonnet 4.5 (Bedrock)                           │ │
│  └───────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐    ┌──────────────┐    ┌──────────────────┐
│   AgentCore   │    │  AgentCore   │    │  Knowledge Base  │
│    Memory     │    │   Gateway    │    │   (Bedrock)      │
│               │    │              │    │                  │
│ • Preferences │    │ ┌──────────┐ │    │ • Policy Docs    │
│ • Semantic    │    │ │  Lambda  │ │    │ • Return Rules   │
│ • Summary     │    │ │ Function │ │    │ • FAQs           │
│               │    │ └──────────┘ │    │                  │
└───────────────┘    └──────────────┘    └──────────────────┘
                             │
                             ▼
                     ┌──────────────┐
                     │  Order Data  │
                     │  (Mock DB)   │
                     └──────────────┘
```

## Component Details

### 1. User Interface Layer

#### Streamlit Web UI
- **Purpose**: Interactive chat interface
- **Features**: 
  - Real-time conversation
  - Quick action buttons
  - Actor ID selection
  - Chat history
- **Location**: `src/ui/streamlit_app.py`

#### CLI Scripts
- **Purpose**: Direct agent invocation
- **Features**:
  - Programmatic access
  - Batch processing
  - Testing automation
- **Location**: `scripts/21_invoke_agent.py`

### 2. Authentication Layer

#### Cognito User Pool
- **Purpose**: OAuth 2.0 authentication
- **Flow**: Client Credentials Grant
- **Scopes**: `gateway-api/read`, `gateway-api/write`
- **Token Type**: JWT Bearer Token

### 3. AgentCore Runtime

#### Agent Container
- **Runtime**: Python 3.10+ on ARM64
- **Deployment**: Serverless, auto-scaling
- **Entry Point**: `@app.entrypoint` decorator
- **Session Management**: 15-minute timeout

#### Custom Tools
1. **check_return_eligibility**
   - Input: purchase_date, item_category, order_id
   - Logic: Uses Policy Engine for configurable rules
   - Output: Eligibility status, days remaining, policy version

2. **calculate_refund_amount**
   - Input: original_price, item_condition, return_reason
   - Logic: Uses Policy Engine for configurable calculations
   - Output: Refund amount, breakdown, policy version

3. **format_policy_response**
   - Input: policy_text, category
   - Logic: Text formatting, bullet points
   - Output: Customer-friendly format

4. **get_policy_info**
   - Input: None
   - Logic: Query current policy metadata
   - Output: Policy name, version, effective date

#### Built-in Tools
- **current_time**: Returns current timestamp
- **retrieve**: Knowledge Base document retrieval

### 3.5 Policy Engine

#### Purpose
Replaces hardcoded business rules with configurable policies loaded from YAML/JSON files.

#### Location
- **Module**: `src/agents/policy_engine.py`
- **Policies**: `policies/` directory
- **Default Policy**: `policies/default_policy.yaml`
- **Schema**: `policies/schema.json`

#### Configuration
```yaml
# policies/default_policy.yaml
policy_id: "default-policy-v1"
policy_name: "Standard Return Policy"
version: "1.0.0"

return_windows:
  electronics: 90
  clothing: 30
  default: 30

refund_rules:
  defective:
    refund_percentage: 100
    restocking_fee_percentage: 0
    shipping_refunded: true
  changed_mind:
    unopened:
      refund_percentage: 100
      restocking_fee_percentage: 0
    used:
      refund_percentage: 80
      restocking_fee_percentage: 20
```

#### Key Features
- **Configurable Rules**: Return windows and refund calculations
- **Version Tracking**: Every decision includes policy version
- **Hot Reload**: Change policy without code deployment (requires restart)
- **Validation**: JSON Schema validation on load
- **Environment Variable**: `POLICY_FILE=policies/custom_policy.yaml`

#### Usage
```python
from src.agents.policy_engine import get_policy_engine

policy = get_policy_engine()
result = policy.check_eligibility("2026-03-01", "electronics")
# Returns: {'eligible': True, 'policy_version': '1.0.0', ...}
```

### 3.6 Decision Logging

#### Purpose
Comprehensive audit trail for all return/refund decisions with structured data.

#### Location
- **Module**: `src/agents/decision_logger.py`
- **Infrastructure**: `infrastructure/decision_log_table.json`
- **Setup Script**: `infrastructure/create_decision_log_table.py`

#### Storage Backends

**1. CloudWatch Logs** (Always Enabled)
- **Format**: Structured JSON
- **Log Group**: `/aws/bedrock-agentcore/runtimes/*`
- **Retention**: 30 days (configurable)
- **Use Case**: Real-time monitoring, debugging

**2. DynamoDB** (Preferred)
- **Table**: `returns-decision-log`
- **Primary Key**: `decision_id` (UUID)
- **GSI**: `timestamp-index` for time-based queries
- **GSI**: `actor-index` for user-based queries
- **Billing**: Pay-per-request
- **Use Case**: Fast queries, dashboards, analytics

**3. S3** (Fallback)
- **Bucket**: `returns-decision-logs`
- **Structure**: `decisions/YYYY/MM/DD/{decision_id}.json`
- **Use Case**: Long-term archive, compliance

#### Log Entry Structure
```json
{
  "decision_id": "uuid-v4",
  "timestamp": "2026-03-22T10:30:00Z",
  "decision_type": "eligibility|refund|escalation",
  "decision": "approved|denied|calculated",
  "inputs": {
    "order_id": "ORD-001",
    "purchase_date": "2026-03-01",
    "category": "electronics"
  },
  "outputs": {
    "eligible": true,
    "reason": "Within 90-day window"
  },
  "actor_id": "user_001",
  "session_id": "session_123",
  "policy_version": "1.0.0",
  "reason": "Item is within 90-day return window",
  "correlation_id": "uuid-v4"
}
```

#### Query Capabilities
- **By Decision ID**: Direct lookup (DynamoDB primary key)
- **By Time Range**: Query timestamp-index
- **By Actor**: Query actor-index for user-specific decisions
- **By Session**: Filter by session_id for conversation flow
- **By Policy Version**: Analyze impact of policy changes

#### Environment Variables
```bash
ENABLE_DECISION_LOGGING=true          # Enable/disable logging
DECISION_LOG_TABLE=returns-decision-log  # DynamoDB table name
DECISION_LOG_BUCKET=returns-decision-logs  # S3 bucket name
AWS_REGION=us-west-2                  # AWS region
```

#### Usage
```python
from src.agents.decision_logger import get_decision_logger

logger = get_decision_logger()
decision_id = logger.log_eligibility_decision(
    order_id="ORD-001",
    purchase_date="2026-03-01",
    category="electronics",
    eligible=True,
    reason="Within 90-day window",
    policy_version="1.0.0",
    actor_id="user_001",
    session_id="session_123"
)
```

#### Automatic Fallback
- If DynamoDB unavailable → Falls back to S3
- If S3 unavailable → CloudWatch Logs only
- Never fails silently, always logs somewhere

### 4. Data Layer

#### AgentCore Memory
- **Storage**: DynamoDB-backed
- **Strategies**:
  - **Summary**: Conversation summaries per session
  - **Preferences**: User preferences (cross-session)
  - **Semantic**: Factual information with embeddings
- **Namespaces**:
  - `app/{actorId}/preferences`
  - `app/{actorId}/semantic`
  - `app/{actorId}/{sessionId}/summary`

#### AgentCore Gateway
- **Purpose**: External API integration
- **Protocol**: MCP (Model Context Protocol)
- **Authentication**: OAuth 2.0 via Cognito
- **Targets**: Lambda functions

#### Knowledge Base
- **Backend**: Amazon Bedrock Knowledge Base
- **Storage**: S3 + Vector embeddings
- **Content**: Return policies, FAQs
- **Retrieval**: Semantic search

### 5. Observability Layer

#### CloudWatch Logs
- **Log Groups**: `/aws/bedrock-agentcore/runtimes/*`
- **Streams**: Runtime logs, OpenTelemetry
- **Retention**: Configurable

#### X-Ray Tracing
- **Traces**: Request flow, tool calls
- **Spans**: Individual operations
- **Analysis**: Performance bottlenecks

#### GenAI Dashboard
- **Metrics**: Latency, throughput, errors
- **Visualizations**: Request volume, success rates
- **Alerts**: Configurable thresholds

## Data Flow

### Request Flow

1. **User Input** → Streamlit UI or CLI
2. **Authentication** → Cognito OAuth token
3. **Agent Invocation** → AgentCore Runtime
4. **Memory Retrieval** → Load user context
5. **LLM Processing** → Claude Sonnet 4.5
6. **Tool Execution** → Custom tools (via Policy Engine), Gateway, KB
7. **Decision Logging** → Log eligibility/refund decisions
8. **Memory Storage** → Save conversation
9. **Response** → Return to user

### Policy Engine Flow

1. **Initialization** → Load policy from YAML/JSON file
2. **Validation** → Validate against JSON schema
3. **Caching** → Store policy in memory
4. **Tool Call** → Agent calls check_eligibility or calculate_refund
5. **Policy Lookup** → Get return window or refund rules
6. **Calculation** → Apply policy rules to inputs
7. **Version Tracking** → Include policy version in result
8. **Return** → Send result back to agent

### Decision Logging Flow

1. **Decision Made** → Tool returns eligibility or refund result
2. **Log Entry Creation** → Build structured log entry with:
   - Unique decision_id (UUID)
   - Timestamp (ISO 8601 UTC)
   - Decision type and outcome
   - All inputs and outputs
   - Actor ID, session ID
   - Policy version used
   - Human-readable reason
3. **CloudWatch Logging** → Always log to CloudWatch (structured JSON)
4. **DynamoDB Logging** → If available, write to DynamoDB table
5. **S3 Fallback** → If DynamoDB unavailable, write to S3
6. **Async Processing** → Non-blocking, doesn't delay response
7. **Query Support** → Enable real-time queries and analytics

### Memory Flow

1. **Event Creation** → Store conversation turn
2. **Async Processing** → Extract preferences, facts
3. **Embedding** → Semantic search indexing
4. **Retrieval** → Query by namespace and text
5. **Context Injection** → Add to agent prompt

### Gateway Flow

1. **Tool Call** → Agent decides to use gateway tool
2. **Token Generation** → Get OAuth token
3. **MCP Request** → Call Lambda via gateway
4. **Lambda Execution** → Process request
5. **Response** → Return data to agent
6. **Integration** → Agent uses data in response

## Scalability

### Auto-scaling
- **Trigger**: Request volume
- **Scale**: Automatic container provisioning
- **Limits**: Account quotas

### Performance
- **Cold Start**: ~2-3 seconds
- **Warm Request**: ~500ms-1s
- **Concurrent**: Multiple instances

### Cost Optimization
- **Pay-per-use**: No idle costs
- **Memory**: Efficient retrieval
- **Caching**: Session state

## Security

### Network
- **Encryption**: TLS 1.2+ in transit
- **VPC**: Optional private networking
- **Endpoints**: Private API endpoints

### Authentication
- **OAuth 2.0**: Industry standard
- **JWT**: Signed tokens
- **Scopes**: Fine-grained permissions

### Authorization
- **IAM Roles**: Least privilege
- **Resource Policies**: Service-to-service
- **Secrets**: Environment variables

## Deployment

### Infrastructure as Code
- **Scripts**: Python-based setup
- **Configuration**: JSON files
- **Idempotent**: Safe to re-run

### CI/CD Ready
- **Git**: Version control
- **Testing**: Automated tests
- **Deployment**: Single command

### Monitoring
- **Health Checks**: `/ping` endpoint
- **Logs**: Structured logging
- **Traces**: Distributed tracing
