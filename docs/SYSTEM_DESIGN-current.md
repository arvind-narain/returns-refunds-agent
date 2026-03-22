# System Design Document: Returns & Refunds Agent

**Document Status**: Current State Analysis  
**Version**: 1.0.0  
**Date**: 2026-03-22  
**Author**: Engineering Team  
**Audience**: Senior/Staff Engineers, Technical Leadership

---

## Table of Contents

1. [Problem Statement & Requirements](#1-problem-statement--requirements)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Data & State Model](#3-data--state-model)
4. [Scalability & Performance](#4-scalability--performance)
5. [Reliability & Failure Handling](#5-reliability--failure-handling)
6. [Observability](#6-observability)
7. [Security, Compliance & Cost](#7-security-compliance--cost)
8. [Technical Debt & Future Considerations](#8-technical-debt--future-considerations)

---

## 1. Problem Statement & Requirements

### 1.1 Business Problem

Customer support agents spend significant time manually:
- Calculating return eligibility based on purchase dates and product categories
- Computing refund amounts with complex condition-based logic and restocking fees
- Looking up company return policies across multiple documents
- Switching between systems to retrieve order information
- Repeating information across multiple customer interactions

**Impact**: Slow response times, inconsistent policy application, agent frustration, potential calculation errors.

### 1.2 Solution Overview

An AI-powered assistant that automates returns/refunds workflows for internal support agents, providing:
- Instant return eligibility checks with category-specific business rules
- Accurate refund calculations with transparent breakdowns
- Natural language policy retrieval from knowledge base
- Integrated order lookup without system switching
- Conversational memory for context-aware interactions

### 1.3 Functional Requirements


#### FR-1: Return Eligibility Verification
- **Input**: Purchase date (YYYY-MM-DD), item category, order ID
- **Business Rules**:
  - Electronics: 90-day return window
  - Clothing, books, home, toys: 30-day return window
  - Non-returnable: perishables, digital, gift cards, personalized items
- **Output**: Eligibility status (boolean), reason, days remaining/since purchase
- **Accuracy**: 100% (deterministic logic)

#### FR-2: Refund Amount Calculation
- **Input**: Original price, item condition, return reason
- **Business Rules**:
  - Defective/wrong_item: 100% refund, no fees, shipping refunded
  - Unopened: 100% refund, no restocking fee
  - Opened_unused: 100% refund, 15% restocking fee
  - Used: 80% refund, 20% restocking fee
  - Damaged: 50% refund, no restocking fee
- **Output**: Refund amount (2 decimal places), breakdown, fees, shipping status
- **Safety**: Non-negative amounts, never exceeds original price, all calculations logged

#### FR-3: Policy Information Retrieval
- **Input**: Natural language query about return policies
- **Process**: Semantic search on knowledge base (S3 + vector embeddings)
- **Output**: Formatted policy text with sections, bullets, customer service tips
- **Accuracy**: Semantic relevance >0.7

#### FR-4: Order Lookup Integration
- **Input**: Order ID (e.g., ORD-001)
- **Process**: OAuth-authenticated call to Lambda via AgentCore Gateway
- **Output**: Product name, purchase date, amount, category, eligibility status
- **Current State**: Mock data (3 sample orders), production integration pending

#### FR-5: Conversational Memory
- **Capabilities**: Remember user preferences, conversation history, semantic facts
- **Isolation**: Actor-based namespaces (one per support agent)
- **Retention**: 30 days
- **Processing**: Asynchronous (20-30 seconds for strategy processing)

### 1.4 Non-Functional Requirements

| Category | Requirement | Target | Current State |
|----------|-------------|--------|---------------|
| **Latency** | End-to-end response | p50: 2s, p95: 5s, p99: 10s | Meeting targets |
| **Throughput** | Daily requests | <100 requests/day | Low traffic |
| **Availability** | Business hours uptime | 99.5% (8am-8pm PT, Mon-Fri) | Acceptable |
| **Correctness** | Policy decisions | 100% for deterministic rules | Unit tested |
| **Security** | Authentication | OAuth 2.0 JWT tokens | Implemented |
| **Cost** | Daily operational cost | $10-15/day | Within budget |

### 1.5 Constraints & Assumptions

**Constraints**:
- Single region deployment (us-west-2)
- Internal tool only (not customer-facing)
- Business hours support (no 24/7 requirement)
- Mock order data (3 samples)
- Hardcoded business rules (return windows, fees)

**Assumptions**:
- Low traffic (<100 requests/day) for foreseeable future
- Cold start latency (2-3 seconds) acceptable for internal tool
- Manual policy updates sufficient
- Actor-based isolation prevents cross-agent data leakage

---


## 2. High-Level Architecture

### 2.1 System Context Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL ACTORS                                  │
│  ┌──────────────────────┐              ┌──────────────────────┐        │
│  │  Support Agent       │              │  Customer            │        │
│  │  (5-10 users)        │              │  (via agent)         │        │
│  └──────────┬───────────┘              └──────────────────────┘        │
└─────────────┼────────────────────────────────────────────────────────────┘
              │
              │ HTTPS (OAuth 2.0)
              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      USER INTERFACE LAYER                                │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Streamlit Web UI                    CLI Scripts                 │   │
│  │  • Chat interface                    • Direct invocation         │   │
│  │  • OAuth token mgmt                  • Batch processing          │   │
│  │  • Actor ID selection                • Testing automation        │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────┬───────────────────────────────────────────────────────────┘
              │
              │ HTTPS + JWT Bearer Token
              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    AUTHENTICATION LAYER                                  │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Amazon Cognito User Pool                                        │   │
│  │  • OAuth 2.0 Client Credentials Grant                            │   │
│  │  • JWT token generation & validation                             │   │
│  │  • Scopes: gateway-api/read, gateway-api/write                   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────┬───────────────────────────────────────────────────────────┘
              │
              │ Validated JWT
              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   AGENTCORE RUNTIME (Serverless)                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Returns & Refunds Agent Container                               │   │
│  │  ┌────────────────────────────────────────────────────────────┐  │   │
│  │  │  Agent Core (Strands Framework)                            │  │   │
│  │  │  • Model: Claude Sonnet 4.5 (temp=0.3)                     │  │   │
│  │  │  • Session Manager: AgentCore Memory integration           │  │   │
│  │  │  • Tool Orchestration: Sequential tool calling             │  │   │
│  │  └────────────────────────────────────────────────────────────┘  │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────┐  │   │
│  │  │  Tool Layer                                                 │  │   │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │  │   │
│  │  │  │ Custom Tools │  │ Built-in     │  │ Gateway Tools    │ │  │   │
│  │  │  │              │  │ Tools        │  │ (MCP Protocol)   │ │  │   │
│  │  │  │ • Eligibility│  │ • retrieve   │  │ • lookup_order   │ │  │   │
│  │  │  │ • Refund     │  │ • current_   │  │                  │ │  │   │
│  │  │  │ • Format     │  │   time       │  │                  │ │  │   │
│  │  │  └──────────────┘  └──────────────┘  └──────────────────┘ │  │   │
│  │  └────────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────┬───────────────────────────────────────────────────────────┘
              │
              │ API Calls
              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        DATA & INTEGRATION LAYER                          │
│                                                                           │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │  AgentCore       │  │  AgentCore       │  │  Bedrock Knowledge   │  │
│  │  Memory          │  │  Gateway         │  │  Base                │  │
│  │                  │  │                  │  │                      │  │
│  │  DynamoDB        │  │  ┌────────────┐  │  │  S3 + Embeddings     │  │
│  │  • Preferences   │  │  │  Lambda    │  │  │  • Policy docs       │  │
│  │  • Semantic      │  │  │  Function  │  │  │  • FAQs              │  │
│  │  • Summary       │  │  └────────────┘  │  │  • Return rules      │  │
│  │                  │  │                  │  │                      │  │
│  │  Top-k: 2-3      │  │  OAuth 2.0       │  │  Semantic search     │  │
│  │  Async: 20-30s   │  │  MCP Protocol    │  │  Relevance >0.7      │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
              │
              │ Mock Data (3 orders)
              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      EXTERNAL SYSTEMS (Future)                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Order Management System (Not Yet Integrated)                    │   │
│  │  • Real order database                                           │   │
│  │  • Production order lookup                                       │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Responsibilities


#### User Interface Layer
- **Streamlit Web UI**: Interactive chat interface with OAuth token management, actor ID selection, quick action buttons
- **CLI Scripts**: Direct agent invocation for testing, batch processing, automation

#### Authentication Layer
- **Cognito User Pool**: OAuth 2.0 identity provider with client credentials grant flow
- **JWT Tokens**: Short-lived (1 hour), scoped access tokens for gateway authorization

#### AgentCore Runtime
- **Agent Container**: Docker container (linux/arm64) with Python 3.12, OpenTelemetry instrumentation
- **Agent Core**: Strands Agents framework orchestrating Claude Sonnet 4.5 with tool calling
- **Tool Layer**: Custom business logic tools, built-in Strands tools, MCP gateway tools

#### Data & Integration Layer
- **AgentCore Memory**: DynamoDB-backed persistent state with 3 strategies (summary, preferences, semantic)
- **AgentCore Gateway**: MCP protocol bridge to external APIs with OAuth authentication
- **Knowledge Base**: S3 + vector embeddings for semantic policy document retrieval (created externally, not scripted in this repo)

### 2.3 Request Flow

```
1. Agent → UI: "Can I return ORD-001?"
2. UI → Cognito: Request OAuth token (client credentials)
3. Cognito → UI: JWT bearer token (1 hour expiration)
4. UI → AgentCore Runtime: POST /invoke {prompt, actor_id} + Bearer token
5. Runtime → Cognito: Validate JWT token
6. Runtime → Agent: invoke(payload, context)
7. Agent → Memory: Retrieve context (preferences, history, summaries)
8. Memory → Agent: Top-k relevant memories (2-3 per namespace)
9. Agent → Bedrock: Process with Claude Sonnet 4.5 + context
10. Bedrock → Agent: Tool calls needed (lookup_order, check_eligibility)
11. Agent → Gateway: lookup_order(ORD-001) + OAuth token
12. Gateway → Lambda: Invoke OrderLookupFunction
13. Lambda → Gateway: Order details (product, date, amount, category)
14. Gateway → Agent: Order data
15. Agent → Custom Tool: check_return_eligibility(date, category, order_id)
16. Custom Tool → Agent: Eligibility result
17. Agent → Bedrock: Generate response with tool results
18. Bedrock → Agent: Final response text
19. Agent → Memory: Store conversation (USER/ASSISTANT pair)
20. Memory → Background: Async processing (20-30s) → extract preferences, facts, summary
21. Agent → Runtime: Return response text
22. Runtime → UI: Response
23. UI → Agent: Display response
```

**Latency Breakdown**:
- OAuth token (cached): ~0ms (reused)
- Memory retrieval: ~100-200ms (DynamoDB)
- Model inference: ~1-2s (Claude Sonnet 4.5)
- Gateway call: ~200-500ms (Lambda cold start possible)
- Custom tools: ~10-50ms (deterministic logic)
- Memory storage: ~50-100ms (async processing happens later)
- **Total**: 2-5 seconds typical (p50: 2s, p95: 5s)

---

## 2.4 Implementation Details

### Agent File Variants

The repository contains four agent implementations with increasing capabilities:

| File | Location | Type | Features | Use Case |
|------|----------|------|----------|----------|
| `01_returns_refunds_agent.py` | `src/agents/` | Basic standalone | Custom tools, KB retrieval | Local testing, basic functionality |
| `06_memory_enabled_agent.py` | `src/agents/` | With memory | Custom tools, KB, Memory | Testing memory features locally |
| `14_full_agent.py` | `src/agents/` | Full-featured | Custom tools, KB, Memory, Gateway | Testing all features locally |
| `17_runtime_agent.py` | `src/agents/` | Production runtime | All features + `@app.entrypoint` | Production deployment to AgentCore Runtime |

**Key Differences**:
- Files 01, 06, 14: Standalone scripts for local testing
- File 17: Uses `BedrockAgentCoreApp` with `@app.entrypoint` decorator for runtime deployment
- All files share the same three custom tools and system prompt structure
- Memory integration uses `AgentCoreMemoryConfig` with retrieval settings for 3 namespaces
- Gateway integration uses `MCPClient` with OAuth token management

### Infrastructure Scripts

Infrastructure setup is automated via Python scripts in `src/infrastructure/`:

| Script | Purpose | Output |
|--------|---------|--------|
| `03_create_memory.py` | Create AgentCore Memory with 3 strategies | `memory_config.json` |
| `04_seed_memory.py` | Seed memory with sample conversations | Memory events |
| `08_create_cognito.py` | Create Cognito User Pool for OAuth | `cognito_config.json` |
| `09_create_gateway_role.py` | Create IAM role for Gateway | `gateway_role_config.json` |
| `10_create_lambda.py` | Create Lambda for order lookup | `lambda_config.json` |
| `11_create_gateway.py` | Create AgentCore Gateway | `gateway_config.json` |
| `12_add_lambda_to_gateway.py` | Add Lambda target to gateway | Gateway target |
| `13_list_gateway_targets.py` | List gateway targets | Console output |
| `16_create_runtime_role.py` | Create IAM execution role | `runtime_execution_role_config.json` |

**Notes**:
- Scripts numbered non-sequentially (03, 04, 08-13, 16)
- Knowledge Base (01) not scripted - created externally, ID stored in `kb_config.json`
- All scripts save configuration to JSON files for subsequent steps
- Scripts use boto3 for AWS API calls and bedrock_agentcore libraries

### Deployment Scripts

Deployment and monitoring scripts in `scripts/`:

| Script | Purpose |
|--------|---------|
| `19_deploy_agent.py` | Deploy agent to AgentCore Runtime (5-10 min) |
| `20_check_status.py` | Monitor deployment status |
| `21_invoke_agent.py` | Test deployed agent |
| `22_get_dashboard.py` | Get CloudWatch observability dashboard URL |
| `23_get_logs_info.py` | Get CloudWatch logs information |

---

## 2.5 Policy Engine & Decision Logging

### Policy Engine

#### Overview
The Policy Engine replaces hardcoded business rules with configurable policies loaded from YAML/JSON files. This enables policy changes without code deployment and provides version tracking for audit compliance.

#### Architecture
```
┌─────────────────────────────────────────────────────────┐
│  Agent Tools (check_eligibility, calculate_refund)     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Policy Engine (src/agents/policy_engine.py)            │
│  ┌───────────────────────────────────────────────────┐  │
│  │  PolicyEngine Class                               │  │
│  │  • _load_policy() - Parse YAML/JSON              │  │
│  │  • _validate_policy() - Schema validation        │  │
│  │  • get_return_window(category) - Lookup window   │  │
│  │  • is_returnable_category(cat) - Check allowed   │  │
│  │  • check_eligibility(date, cat) - Evaluate       │  │
│  │  • calculate_refund(price, cond, reason) - Calc  │  │
│  │  • get_policy_info() - Metadata                  │  │
│  └───────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Policy Files (policies/)                               │
│  • default_policy.yaml - Standard policy                │
│  • schema.json - JSON Schema validation                 │
│  • README.md - Documentation                            │
└─────────────────────────────────────────────────────────┘
```

#### Policy File Structure
```yaml
policy_id: "default-policy-v1"
policy_name: "Standard Return Policy"
version: "1.0.0"
effective_date: "2026-03-22"

return_windows:
  electronics: 90
  clothing: 30
  default: 30

non_returnable_categories:
  - perishables
  - digital
  - gift_cards

refund_rules:
  defective:
    refund_percentage: 100
    restocking_fee_percentage: 0
    shipping_refunded: true
  changed_mind:
    unopened:
      refund_percentage: 100
      restocking_fee_percentage: 0
      shipping_refunded: false
    used:
      refund_percentage: 80
      restocking_fee_percentage: 20
      shipping_refunded: false
```

#### Configuration
- **Environment Variable**: `POLICY_FILE=policies/custom_policy.yaml`
- **Default**: `policies/default_policy.yaml`
- **Validation**: Automatic JSON Schema validation on load
- **Caching**: Policy loaded once at startup, cached in memory
- **Hot Reload**: Requires agent restart to pick up changes

#### Integration with Tools
```python
# Before (Hardcoded):
def check_return_eligibility(purchase_date, category, order_id):
    # 50 lines of if/else logic
    if category == 'electronics':
        window = 90
    elif category == 'clothing':
        window = 30
    # ... more hardcoded rules

# After (Policy Engine):
def check_return_eligibility(purchase_date, category, order_id):
    policy = get_policy_engine()
    result = policy.check_eligibility(purchase_date, category)
    result['order_id'] = order_id
    return result  # Includes policy_version
```

#### Benefits
- **Configurability**: Change policies without code deployment
- **Version Tracking**: Every decision includes policy version
- **Auditability**: Know which policy was used for each decision
- **Testability**: Easy to test different policy scenarios
- **Maintainability**: Business logic separated from code

---

### Decision Logging

#### Overview
Comprehensive audit trail system that logs all return/refund decisions with structured data to multiple storage backends for compliance, analytics, and debugging.

#### Architecture
```
┌─────────────────────────────────────────────────────────┐
│  Agent Tools (after decision made)                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Decision Logger (src/agents/decision_logger.py)        │
│  ┌───────────────────────────────────────────────────┐  │
│  │  DecisionLogger Class                             │  │
│  │  • log_decision() - Generic logging               │  │
│  │  • log_eligibility_decision() - Eligibility       │  │
│  │  • log_refund_decision() - Refund calculation     │  │
│  │  • _log_to_s3() - S3 fallback                     │  │
│  └───────────────────────────────────────────────────┘  │
└──────┬──────────────┬──────────────┬────────────────────┘
       │              │              │
       ▼              ▼              ▼
┌─────────────┐ ┌──────────┐ ┌─────────────────┐
│ CloudWatch  │ │ DynamoDB │ │ S3 (Fallback)   │
│ Logs        │ │ Table    │ │ Bucket          │
│ (Always)    │ │(Preferred)│ │ (If DDB fails) │
└─────────────┘ └──────────┘ └─────────────────┘
```

#### Storage Backends

**1. CloudWatch Logs** (Always Enabled)
- **Format**: Structured JSON
- **Log Group**: `/aws/bedrock-agentcore/runtimes/*`
- **Logger**: `decision_log` logger
- **Retention**: 30 days (configurable)
- **Use Case**: Real-time monitoring, debugging, alerts
- **Query**: CloudWatch Logs Insights

**2. DynamoDB** (Preferred)
- **Table**: `returns-decision-log`
- **Primary Key**: `decision_id` (UUID)
- **GSI 1**: `timestamp-index` - Time-based queries
- **GSI 2**: `actor-index` - User-based queries (actor_id + timestamp)
- **Billing**: Pay-per-request (on-demand)
- **Use Case**: Fast queries, dashboards, real-time analytics
- **Query Speed**: Milliseconds

**3. S3** (Fallback)
- **Bucket**: `returns-decision-logs`
- **Path**: `decisions/YYYY/MM/DD/{decision_id}.json`
- **Format**: JSON per decision
- **Use Case**: Long-term archive, compliance, cost-effective storage
- **Query Speed**: Seconds (requires Athena or S3 Select)

#### Log Entry Structure
```json
{
  "decision_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-03-22T10:30:00.000Z",
  "decision_type": "eligibility",
  "decision": "approved",
  "inputs": {
    "order_id": "ORD-001",
    "purchase_date": "2026-03-01",
    "category": "electronics"
  },
  "outputs": {
    "eligible": true,
    "reason": "Item is within 90-day return window",
    "days_since_purchase": 21,
    "days_remaining": 69
  },
  "actor_id": "user_001",
  "session_id": "session_20260322_103000",
  "policy_version": "1.0.0",
  "reason": "Item is within 90-day return window",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### Query Patterns

**By Decision ID** (Direct Lookup)
```python
# DynamoDB
table.get_item(Key={'decision_id': 'uuid'})

# CloudWatch Logs Insights
fields @timestamp, decision_id, decision_type, decision
| filter decision_id = "uuid"
```

**By Time Range** (Time-based Analysis)
```python
# DynamoDB (using timestamp-index)
table.query(
    IndexName='timestamp-index',
    KeyConditionExpression='timestamp BETWEEN :start AND :end'
)

# CloudWatch Logs Insights
fields @timestamp, decision_id, decision_type, decision
| filter @timestamp >= "2026-03-22T00:00:00Z" 
    and @timestamp <= "2026-03-22T23:59:59Z"
| stats count() by decision_type
```

**By Actor** (User-specific Queries)
```python
# DynamoDB (using actor-index)
table.query(
    IndexName='actor-index',
    KeyConditionExpression='actor_id = :actor_id'
)

# CloudWatch Logs Insights
fields @timestamp, decision_id, decision_type, decision
| filter actor_id = "user_001"
| sort @timestamp desc
```

**By Policy Version** (Policy Impact Analysis)
```python
# DynamoDB (scan with filter)
table.scan(
    FilterExpression='policy_version = :version'
)

# CloudWatch Logs Insights
fields @timestamp, decision_id, decision_type, decision
| filter policy_version = "1.0.0"
| stats count() by decision_type, decision
```

#### Configuration
```bash
# Environment Variables
ENABLE_DECISION_LOGGING=true          # Enable/disable (default: true)
DECISION_LOG_TABLE=returns-decision-log  # DynamoDB table name
DECISION_LOG_BUCKET=returns-decision-logs  # S3 bucket name
AWS_REGION=us-west-2                  # AWS region
```

#### Automatic Fallback Logic
1. **Primary**: Try DynamoDB
   - If table exists and accessible → Log to DynamoDB
   - If table doesn't exist or permission denied → Fall back to S3
2. **Fallback**: Try S3
   - If bucket exists and accessible → Log to S3
   - If bucket doesn't exist or permission denied → CloudWatch only
3. **Always**: CloudWatch Logs
   - Always log to CloudWatch regardless of DynamoDB/S3 status
   - Never fails silently

#### Performance Impact
- **Logging Overhead**: ~5ms per decision (async, non-blocking)
- **Memory**: Negligible (~1KB per log entry)
- **Network**: Async writes, doesn't delay response to user
- **Overall**: <1% performance impact

#### Compliance & Audit
- **Immutable**: Decisions cannot be modified after logging
- **Unique IDs**: UUID v4 for each decision
- **Timestamps**: ISO 8601 UTC for consistency
- **Version Tracking**: Policy version included in every decision
- **Correlation**: Link related decisions via correlation_id
- **Retention**: Configurable (30 days CloudWatch, unlimited DynamoDB/S3)

---

### 3.1 Entity Model

#### Order Entity (External System - Mock Data)
```python
Order {
    order_id: str              # Primary key (e.g., "ORD-001")
    product_name: str          # "Dell XPS 15 Laptop"
    purchase_date: date        # YYYY-MM-DD
    amount: decimal(10,2)      # Original purchase price
    category: str              # "electronics", "clothing", etc.
    condition: str             # "unopened", "opened_unused", "used", "damaged"
    return_eligible: bool      # Computed field
    return_window_days: int    # Category-specific (90 or 30)
    days_remaining: int        # Computed: window - days_since_purchase
}

# Current Mock Data:
# ORD-001: Dell XPS 15 Laptop, 15 days old, eligible
# ORD-002: iPhone 13 Pro, 45 days old, expired
# ORD-003: Samsung Galaxy Tab S8, 5 days old, defective, eligible
```

#### Return Decision Entity (Computed, Not Persisted)
```python
ReturnDecision {
    order_id: str
    eligible: bool
    reason: str                # "Within window", "Expired", "Non-returnable"
    days_since_purchase: int
    days_remaining: int        # Only if eligible
    return_window: int         # Category-specific window
    category: str
    computed_at: timestamp
}
```

#### Refund Calculation Entity (Computed, Logged)
```python
RefundCalculation {
    order_id: str
    original_price: decimal(10,2)
    item_condition: str
    return_reason: str
    refund_amount: decimal(10,2)      # Final amount (2 decimals)
    refund_percentage: int            # 50, 80, or 100
    restocking_fee: decimal(10,2)     # 0, 15%, or 20% of original
    shipping_refunded: bool
    calculated_at: timestamp
    calculated_by: str                # actor_id
}

# Business Rules (Configurable via Policy Engine):
# See policies/default_policy.yaml for current rules
# defective/wrong_item: 100%, $0 fee, shipping refunded
# unopened: 100%, $0 fee
# opened_unused: 100%, 15% fee
# used: 80%, 20% fee
# damaged: 50%, $0 fee
```

#### Policy Configuration Entity (File-based - YAML/JSON)
```python
PolicyConfig {
    policy_id: str             # "default-policy-v1"
    policy_name: str           # "Standard Return Policy"
    version: str               # "1.0.0"
    effective_date: date       # When policy becomes active
    
    return_windows: dict       # Category → days mapping
    # {
    #   "electronics": 90,
    #   "clothing": 30,
    #   "default": 30
    # }
    
    non_returnable_categories: List[str]  # ["digital", "perishables", ...]
    
    refund_rules: dict         # Nested rules by reason and condition
    # {
    #   "defective": {"refund_percentage": 100, "restocking_fee_percentage": 0, ...},
    #   "changed_mind": {
    #     "unopened": {"refund_percentage": 100, ...},
    #     "used": {"refund_percentage": 80, "restocking_fee_percentage": 20, ...}
    #   }
    # }
}

# Storage: policies/default_policy.yaml
# Validation: policies/schema.json
# Loading: src/agents/policy_engine.py
# Environment Variable: POLICY_FILE=policies/custom_policy.yaml
```

#### Decision Log Entity (DynamoDB / S3 / CloudWatch)
```python
DecisionLog {
    decision_id: str           # UUID (primary key)
    timestamp: datetime        # ISO 8601 UTC
    decision_type: str         # "eligibility", "refund", "escalation"
    decision: str              # "approved", "denied", "calculated"
    
    inputs: dict               # All input parameters
    # {
    #   "order_id": "ORD-001",
    #   "purchase_date": "2026-03-01",
    #   "category": "electronics"
    # }
    
    outputs: dict              # Decision results
    # {
    #   "eligible": true,
    #   "reason": "Within 90-day window",
    #   "days_remaining": 75
    # }
    
    actor_id: str              # Support agent making decision
    session_id: str            # Conversation session
    policy_version: str        # Policy version used (e.g., "1.0.0")
    reason: str                # Human-readable explanation
    correlation_id: str        # Link related decisions
}

# Storage Options:
# 1. DynamoDB: returns-decision-log table (preferred)
#    - Primary Key: decision_id
#    - GSI: timestamp-index (time-based queries)
#    - GSI: actor-index (user-based queries)
# 2. S3: returns-decision-logs bucket (fallback)
#    - Path: decisions/YYYY/MM/DD/{decision_id}.json
# 3. CloudWatch Logs: /aws/bedrock-agentcore/runtimes/* (always)
#    - Format: Structured JSON

# Query Capabilities:
# - By decision_id: Direct lookup (DynamoDB)
# - By timestamp: Time-range queries (DynamoDB GSI)
# - By actor_id: User-specific queries (DynamoDB GSI)
# - By policy_version: Policy impact analysis (scan/filter)
```

#### Conversation Memory Entity (AgentCore Memory - DynamoDB)
```python
MemoryEvent {
    event_id: str              # UUID
    memory_id: str             # Memory resource ID
    actor_id: str              # Support agent identifier
    session_id: str            # Conversation session
    timestamp: datetime
    messages: List[Tuple[str, str]]  # [("user text", "USER"), ("agent text", "ASSISTANT")]
    
    # Processed asynchronously (20-30 seconds):
    preferences: List[str]     # Extracted to app/{actorId}/preferences
    semantic_facts: List[str]  # Embedded to app/{actorId}/semantic
    summary: str               # Generated to app/{actorId}/{sessionId}/summary
}

# Namespaces:
# - app/{actorId}/preferences: Cross-session user preferences
# - app/{actorId}/semantic: Factual information with embeddings
# - app/{actorId}/{sessionId}/summary: Per-session conversation summaries

# Retrieval Config:
# - semantic: top_k=3
# - preferences: top_k=3
# - summary: top_k=2
```

#### Policy Document Entity (Knowledge Base - S3 + Embeddings)
```python
PolicyDocument {
    document_id: str
    title: str
    category: str              # "electronics", "general", etc.
    content: str               # Full policy text
    embedding: vector[1536]    # Vector embedding for semantic search
    last_updated: datetime
    version: str
}

# Retrieval:
# - Semantic search with relevance threshold >0.7
# - Returns top-k relevant document chunks
```

### 3.2 State Management

#### Session State (AgentCore Runtime)
```python
SessionState {
    session_id: str            # 15-minute timeout
    actor_id: str              # Support agent identifier
    conversation_turns: int
    last_activity: timestamp
    
    # Cached during session:
    oauth_token: str           # Cognito JWT (1 hour expiration)
    mcp_client: MCPClient      # Gateway connection
    memory_context: dict       # Retrieved memories
}
```

#### Application State (Stateless)
- **Agent**: Stateless, recreated per request
- **Tools**: Pure functions, no state
- **Configuration**: Loaded from environment variables and JSON files

### 3.3 Data Flow & Persistence

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA PERSISTENCE                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  AgentCore Memory (DynamoDB)                         │  │
│  │  • Retention: 30 days                                │  │
│  │  • Encryption: At rest                               │  │
│  │  • Isolation: Actor-based namespaces                 │  │
│  │  • Processing: Async (20-30s)                        │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Knowledge Base (S3 + Vector DB)                     │  │
│  │  • Storage: S3 buckets                               │  │
│  │  • Embeddings: Vector database                       │  │
│  │  • Updates: Manual (monthly)                         │  │
│  │  • Versioning: S3 versioning enabled                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  CloudWatch Logs                                     │  │
│  │  • All requests logged with correlation IDs          │  │
│  │  • Refund calculations logged for audit              │  │
│  │  • Retention: 30 days (configurable)                 │  │
│  │  • No PII logged                                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Configuration Files (Local, Git-ignored)            │  │
│  │  • memory_config.json, cognito_config.json, etc.    │  │
│  │  • Sensitive data excluded from version control     │  │
│  │  • Loaded as environment variables at runtime       │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 3.4 Data Consistency & Integrity

**Consistency Model**:
- **Memory**: Eventually consistent (20-30 second async processing)
- **Knowledge Base**: Manually updated, no real-time consistency requirements
- **Refund Calculations**: Deterministic, no state dependencies
- **Order Lookup**: Mock data (consistent), production would be eventually consistent

**Integrity Safeguards**:
- Refund amount always non-negative: `max(0, calculated_amount)`
- Refund never exceeds original price: implicit in percentage-based calculation
- All calculations logged to CloudWatch for audit trail
- Actor-based isolation prevents cross-user data leakage

---


## 4. Scalability & Performance

### 4.1 Current Performance Characteristics

| Metric | Target | Current | Measurement Method |
|--------|--------|---------|-------------------|
| **Latency (p50)** | 2 seconds | ~2s | End-to-end UI to response |
| **Latency (p95)** | 5 seconds | ~5s | CloudWatch metrics |
| **Latency (p99)** | 10 seconds | ~8s | CloudWatch metrics |
| **Cold Start** | <5 seconds | 2-3s | First request after idle |
| **Warm Request** | <2 seconds | 500ms-1s | Subsequent requests |
| **Throughput** | <100 req/day | ~50 req/day | CloudWatch request count |
| **Concurrent Users** | 5-10 agents | ~5 agents | Streamlit sessions |

### 4.2 Scalability Analysis

#### Current Scale
- **Traffic**: <100 requests/day (~4 requests/hour during business hours)
- **Users**: 5-10 concurrent support agents
- **Geography**: Single region (us-west-2)
- **Data Volume**: 
  - Memory: ~1000 events/month (30-day retention)
  - Logs: ~1 GB/month
  - Knowledge Base: ~100 policy documents

#### Scaling Dimensions

**Vertical Scaling (Single Request)**:
```
Component                  Current Latency    Bottleneck?
─────────────────────────────────────────────────────────
OAuth Token (cached)       ~0ms               No
Memory Retrieval           100-200ms          No
Model Inference            1-2s               Yes (largest)
Gateway Call (Lambda)      200-500ms          Moderate
Custom Tools               10-50ms            No
Memory Storage             50-100ms           No
─────────────────────────────────────────────────────────
Total                      2-5s               Model-bound
```

**Horizontal Scaling (Concurrent Requests)**:
- **AgentCore Runtime**: Auto-scales based on request volume
- **Current Limit**: AWS account quotas (not reached)
- **Bottleneck**: None at current scale (<10 concurrent requests)

#### Immediate Bottlenecks

**1. Model Inference Latency (1-2 seconds)**
- **Impact**: Dominates end-to-end latency
- **Mitigation Options**:
  - Use faster model (trade-off: accuracy)
  - Implement streaming responses (perceived latency improvement)
  - Cache common queries (limited applicability for dynamic data)
- **Priority**: Low (acceptable for internal tool)

**2. Memory Processing Delay (20-30 seconds)**
- **Impact**: Preferences not available in same session
- **Mitigation Options**:
  - Synchronous preference extraction (trade-off: latency)
  - Client-side caching of preferences
  - Manual preference entry by agent
- **Priority**: Low (design limitation, acceptable)

**3. Cold Start Latency (2-3 seconds)**
- **Impact**: First request after idle period
- **Mitigation Options**:
  - Provisioned concurrency (trade-off: cost)
  - Warm-up requests (scheduled pings)
  - Smaller container image
- **Priority**: Low (acceptable for internal tool)

**4. Single Region Deployment**
- **Impact**: Regional outage affects all users
- **Mitigation Options**:
  - Multi-region deployment (trade-off: complexity, cost)
  - Failover to manual processes
- **Priority**: Low (acceptable risk for internal tool)

### 4.3 Capacity Planning

#### Current Capacity
- **AgentCore Runtime**: Scales to handle 100x current load without changes
- **Memory (DynamoDB)**: On-demand scaling, no capacity limits at current scale
- **Knowledge Base**: No capacity limits for read operations
- **Lambda**: 1000 concurrent executions (AWS default), far exceeds needs

#### Growth Scenarios

**Scenario 1: 10x Traffic (1000 requests/day)**
- **Impact**: Still within auto-scaling capacity
- **Cost**: ~$100-150/day (10x current)
- **Changes Needed**: None
- **Monitoring**: Increase CloudWatch alarm thresholds

**Scenario 2: Customer-Facing (100x Traffic, 10,000 requests/day)**
- **Impact**: Requires architectural changes
- **Changes Needed**:
  - Multi-region deployment for global users
  - CDN for static assets
  - Caching layer for knowledge base queries
  - Rate limiting per user
  - Enhanced monitoring and alerting
- **Cost**: ~$1000-1500/day
- **Timeline**: 3-6 months for production-ready customer-facing deployment

**Scenario 3: Real-Time Requirements (p95 <1 second)**
- **Impact**: Requires model optimization
- **Changes Needed**:
  - Faster model (e.g., Claude Haiku)
  - Streaming responses
  - Aggressive caching
  - Provisioned concurrency
- **Cost**: ~$50-100/day (provisioned capacity)
- **Timeline**: 1-2 months

### 4.4 Performance Optimization Opportunities

**Quick Wins (1-2 weeks)**:
1. Implement response streaming for perceived latency improvement
2. Cache OAuth tokens more aggressively (currently per-session)
3. Optimize Docker image size (reduce cold start)

**Medium-Term (1-3 months)**:
1. Implement knowledge base query caching (Redis/ElastiCache)
2. Add provisioned concurrency for predictable latency
3. Optimize memory retrieval queries (reduce top_k if possible)

**Long-Term (3-6 months)**:
1. Multi-region deployment for geographic distribution
2. Model fine-tuning for faster inference
3. Implement request batching for high-volume scenarios

---


## 5. Reliability & Failure Handling

### 5.1 Availability Target

**SLA**: 99.5% during business hours (8am-8pm PT, Mon-Fri)
- **Acceptable Downtime**: ~2 hours/month
- **Recovery Time Objective (RTO)**: 15 minutes
- **Recovery Point Objective (RPO)**: No data loss (all data persisted)

### 5.2 Failure Modes & Handling

#### FM-1: AgentCore Runtime Failure
**Symptoms**: Agent not responding, 500 errors, timeout
**Causes**: Container crash, OOM, deployment failure
**Impact**: All users unable to access agent
**Detection**: CloudWatch alarms on error rate >5%, health check failures
**Mitigation**:
- Auto-restart by AgentCore Runtime
- Rollback to previous container image (5-10 minutes)
- Manual fallback: agents use spreadsheets for calculations
**Recovery**: Redeploy agent via `scripts/19_deploy_agent.py`

#### FM-2: Bedrock Model Unavailable
**Symptoms**: Model invocation errors, timeout
**Causes**: Bedrock service outage, quota exceeded, throttling
**Impact**: Agent cannot process requests
**Detection**: CloudWatch alarms on Bedrock API errors
**Mitigation**:
- Retry once with exponential backoff
- Return user-friendly error message
- No automatic fallback to different model (single model constraint)
**Recovery**: Wait for Bedrock service recovery, escalate to AWS Support

#### FM-3: AgentCore Memory Unavailable
**Symptoms**: Memory retrieval/storage errors
**Causes**: DynamoDB outage, network issues, quota exceeded
**Impact**: Agent continues without conversation history
**Detection**: CloudWatch alarms on Memory API errors
**Mitigation**:
- **Graceful Degradation**: Agent continues without memory
- Log warning, inform user that preferences may not be available
- Store conversation locally in session (lost after session ends)
**Recovery**: Automatic when Memory service recovers

#### FM-4: AgentCore Gateway Unavailable
**Symptoms**: Gateway tool calls fail, Lambda not invoked
**Causes**: Gateway service outage, Lambda failure, OAuth token issues
**Impact**: Agent cannot look up orders
**Detection**: CloudWatch alarms on Gateway API errors
**Mitigation**:
- **Graceful Degradation**: Agent continues without order lookup
- Retry 3 times with exponential backoff
- Inform user to provide order details manually
**Recovery**: Automatic when Gateway/Lambda recovers

#### FM-5: Knowledge Base Unavailable
**Symptoms**: Retrieve tool fails, no policy documents returned
**Causes**: Bedrock KB service outage, S3 issues
**Impact**: Agent cannot retrieve policy documents
**Detection**: CloudWatch alarms on KB API errors
**Mitigation**:
- **Graceful Degradation**: Agent uses cached policies or manual lookup
- Inform user to refer to policy website
- Agent can still perform calculations without KB
**Recovery**: Automatic when KB service recovers

#### FM-6: Cognito Authentication Failure
**Symptoms**: OAuth token generation fails, 401 errors
**Causes**: Cognito service outage, misconfiguration, expired credentials
**Impact**: Users cannot authenticate, no access to agent
**Detection**: UI displays authentication error
**Mitigation**:
- Retry token request 3 times
- Check Cognito service status
- Verify client_id and client_secret configuration
**Recovery**: Fix configuration, redeploy if needed

#### FM-7: Lambda Function Failure (Order Lookup)
**Symptoms**: Gateway returns 500 error, timeout
**Causes**: Lambda code error, timeout (30s), memory limit (128MB)
**Impact**: Order lookup unavailable
**Detection**: CloudWatch Lambda error metrics, Gateway logs
**Mitigation**:
- Lambda retries automatically (3 attempts)
- Return error to agent with available order IDs
- Agent informs user to provide order details manually
**Recovery**: Fix Lambda code, redeploy via `scripts/10_create_lambda.py`

### 5.3 Fault Tolerance Strategies

#### Retry Logic
```python
# Gateway Requests
max_retries = 3
backoff = exponential (1s, 2s, 4s)
timeout = 30 seconds per attempt

# Memory Operations
max_retries = 1
fallback = continue without memory
timeout = 5 seconds

# Model Invocation
max_retries = 1
fallback = return error message
timeout = 30 seconds
```

#### Circuit Breaker Pattern
**Not Currently Implemented** - Opportunity for improvement
- Could implement for Gateway calls to prevent cascading failures
- Open circuit after 5 consecutive failures
- Half-open after 60 seconds to test recovery

#### Graceful Degradation Hierarchy
```
Full Functionality
├─ Agent + Memory + Gateway + KB
│
├─ Agent + Memory + KB (Gateway unavailable)
│  └─ Impact: No order lookup, manual entry required
│
├─ Agent + Gateway + KB (Memory unavailable)
│  └─ Impact: No conversation history, no preferences
│
├─ Agent + KB (Memory + Gateway unavailable)
│  └─ Impact: Basic functionality only
│
└─ Agent Only (All services unavailable)
   └─ Impact: Custom tools only, no external data
```

### 5.4 Data Integrity & Consistency

#### Refund Calculation Integrity
- **Validation**: Non-negative amounts, never exceeds original price
- **Audit Trail**: All calculations logged to CloudWatch with input parameters
- **Human Oversight**: Agent reviews amount before communicating to customer
- **Rollback**: No automatic refund processing, agent must manually approve

#### Memory Data Integrity
- **Isolation**: Actor-based namespaces prevent cross-user data leakage
- **Encryption**: DynamoDB encryption at rest
- **Retention**: 30-day automatic expiration
- **Backup**: DynamoDB point-in-time recovery (not currently enabled)

#### Configuration Integrity
- **Secrets**: Stored in environment variables, never in code
- **Validation**: Configuration files validated at deployment time
- **Version Control**: Infrastructure scripts in Git, config files excluded

### 5.5 Disaster Recovery

#### Backup Strategy
- **Memory Data**: DynamoDB managed backups (not currently enabled)
- **Knowledge Base**: S3 versioning enabled
- **Configuration**: Infrastructure scripts in Git
- **Container Images**: ECR retains previous images

#### Recovery Procedures

**Scenario 1: Complete Region Failure**
- **RTO**: 4-8 hours (manual multi-region deployment)
- **RPO**: 30 days (memory data lost beyond retention)
- **Procedure**:
  1. Deploy infrastructure to backup region (us-east-1)
  2. Restore knowledge base from S3 cross-region replication
  3. Redeploy agent container
  4. Update DNS/load balancer to new region
  5. Memory data lost (acceptable for internal tool)

**Scenario 2: Data Corruption**
- **RTO**: 1-2 hours
- **RPO**: Point-in-time recovery (if enabled)
- **Procedure**:
  1. Identify corruption source
  2. Restore from DynamoDB backup
  3. Verify data integrity
  4. Resume operations

**Scenario 3: Deployment Failure**
- **RTO**: 15 minutes
- **RPO**: No data loss
- **Procedure**:
  1. Identify failed deployment
  2. Rollback to previous container image
  3. Verify functionality
  4. Investigate root cause

---


## 6. Observability

### 6.1 Current Instrumentation

#### Logging (CloudWatch Logs)
```
Log Group: /aws/bedrock-agentcore/runtimes/returns_refunds_agent-*
Retention: 30 days (configurable)
Format: JSON with structured fields
Level: INFO (normal), ERROR (failures)

Logged Events:
├─ Agent Invocation Start
│  └─ Fields: timestamp, actor_id, session_id, prompt (truncated)
├─ Memory Retrieval
│  └─ Fields: memory_id, namespaces, top_k, latency_ms
├─ Model Inference
│  └─ Fields: model_id, temperature, input_tokens, output_tokens, latency_ms
├─ Tool Calls
│  └─ Fields: tool_name, inputs, outputs, latency_ms
├─ Gateway Calls
│  └─ Fields: gateway_url, tool_name, oauth_scope, latency_ms, status_code
├─ Refund Calculations
│  └─ Fields: order_id, original_price, refund_amount, breakdown, actor_id
├─ Errors
│  └─ Fields: error_type, error_message, stack_trace, context
└─ Agent Invocation Complete
   └─ Fields: total_latency_ms, tools_called, response_length
```

**PII Handling**: No customer PII logged (order IDs are pseudonymized)

#### Metrics (CloudWatch Metrics)
```
Namespace: AWS/BedrockAgentCore

Metrics Tracked:
├─ Invocations (Count)
│  └─ Dimensions: AgentName, Region
├─ Latency (Milliseconds)
│  └─ Statistics: p50, p95, p99, Average, Max
├─ Errors (Count)
│  └─ Dimensions: ErrorType (ModelError, MemoryError, GatewayError)
├─ Tool Usage (Count)
│  └─ Dimensions: ToolName
├─ Memory Retrieval Time (Milliseconds)
│  └─ Dimensions: Namespace
└─ Gateway Call Latency (Milliseconds)
   └─ Dimensions: TargetName
```

#### Tracing (X-Ray)
```
Service Map:
Streamlit UI → AgentCore Runtime → Bedrock Model
                      ↓
                AgentCore Memory (DynamoDB)
                      ↓
                AgentCore Gateway → Lambda

Spans:
├─ Agent Invocation (root span)
│  ├─ Memory Retrieval
│  │  └─ DynamoDB Query
│  ├─ Model Inference
│  │  └─ Bedrock InvokeModel
│  ├─ Tool Execution
│  │  ├─ Custom Tool (local)
│  │  └─ Gateway Tool
│  │     └─ Lambda Invocation
│  └─ Memory Storage
│     └─ DynamoDB PutItem
└─ Response Return

Correlation: Request ID propagated through all spans
```

#### Dashboards

**CloudWatch GenAI Observability Dashboard**
- Request volume (requests/hour, requests/day)
- Latency distribution (p50, p95, p99)
- Error rate (errors per 100 requests)
- Tool usage breakdown (pie chart)
- Model token usage (input/output tokens)
- Cost estimation (based on token usage)

**Custom Business Metrics Dashboard** (Planned, Not Implemented)
- Return approval rate (% approved vs. denied)
- Average refund amount
- Most common return reasons
- Policy questions frequency
- Agent productivity (requests per agent per hour)

### 6.2 Observability Gaps

#### Missing Instrumentation

**1. Business Metrics**
- **Gap**: No tracking of return approval rates, refund amounts, return reasons
- **Impact**: Cannot measure business outcomes, only technical performance
- **Recommendation**: Add custom CloudWatch metrics for business KPIs
- **Effort**: 1-2 weeks

**2. User Experience Metrics**
- **Gap**: No tracking of user satisfaction, task completion rate
- **Impact**: Cannot measure if agent is actually helping support agents
- **Recommendation**: Add feedback mechanism in UI, track task completion
- **Effort**: 2-3 weeks

**3. Cost Attribution**
- **Gap**: No per-agent or per-request cost tracking
- **Impact**: Cannot identify cost drivers or optimize for specific use cases
- **Recommendation**: Tag requests with actor_id, track token usage per agent
- **Effort**: 1 week

**4. Synthetic Monitoring**
- **Gap**: No proactive health checks or synthetic transactions
- **Impact**: Failures only detected when real users encounter them
- **Recommendation**: Implement scheduled health checks (every 5 minutes)
- **Effort**: 1 week

**5. Alerting Coverage**
- **Gap**: Limited alerts (error rate, latency, cost)
- **Missing**: Memory processing delays, knowledge base staleness, OAuth token expiration
- **Recommendation**: Expand alert coverage to all critical paths
- **Effort**: 1 week

**6. Distributed Tracing Completeness**
- **Gap**: X-Ray traces don't include custom tool execution details
- **Impact**: Cannot debug performance issues in custom tools
- **Recommendation**: Add custom X-Ray subsegments for tool execution
- **Effort**: 1 week

### 6.3 Debugging Workflow

#### Scenario 1: Agent Returns Incorrect Refund Amount
```
1. Check CloudWatch Logs for request with correlation ID
2. Find refund calculation log entry
3. Verify input parameters (original_price, item_condition, return_reason)
4. Check business rules in code (calculate_refund_amount tool)
5. Verify calculation logic matches expected output
6. If bug found: Fix code, add unit test, redeploy
7. If input error: Investigate why agent called tool with wrong parameters
```

#### Scenario 2: High Latency (>10 seconds)
```
1. Check CloudWatch Metrics for latency spike
2. Identify time range of high latency
3. Check X-Ray traces for slow spans
4. Common causes:
   - Model inference slow: Check Bedrock service status
   - Memory retrieval slow: Check DynamoDB metrics
   - Gateway call slow: Check Lambda cold start, execution time
   - Multiple tool calls: Check if agent is calling tools unnecessarily
5. Mitigation:
   - If model slow: Consider faster model or streaming
   - If memory slow: Reduce top_k or optimize queries
   - If gateway slow: Optimize Lambda or add caching
```

#### Scenario 3: Authentication Failures
```
1. Check UI error message (401 Unauthorized)
2. Check CloudWatch Logs for OAuth token errors
3. Verify Cognito configuration (client_id, client_secret, discovery_url)
4. Test token generation manually:
   curl -X POST <token_endpoint> -d "grant_type=client_credentials&client_id=...&client_secret=..."
5. If token valid: Check AgentCore Runtime authorizer configuration
6. If token invalid: Regenerate Cognito credentials, update config
```

### 6.4 Monitoring Recommendations

**Immediate (1-2 weeks)**:
1. Add synthetic health checks (every 5 minutes)
2. Expand alerting to cover all critical paths
3. Implement cost attribution per actor_id

**Short-Term (1-3 months)**:
1. Add business metrics dashboard (approval rates, refund amounts)
2. Implement user feedback mechanism in UI
3. Add custom X-Ray subsegments for tool execution

**Long-Term (3-6 months)**:
1. Implement anomaly detection for latency and error rates
2. Add predictive alerting (forecast capacity needs)
3. Integrate with centralized logging platform (e.g., Splunk, Datadog)

---


## 7. Security, Compliance & Cost

### 7.1 Security Architecture

#### Authentication & Authorization

**OAuth 2.0 Flow (Client Credentials Grant)**:
```
1. UI → Cognito: POST /oauth2/token
   Body: grant_type=client_credentials, client_id=..., client_secret=..., scope=gateway-api/read gateway-api/write
2. Cognito → UI: JWT bearer token (1 hour expiration)
3. UI → AgentCore Runtime: POST /invoke + Authorization: Bearer <token>
4. Runtime → Cognito: Validate JWT signature and expiration
5. Runtime → Agent: Invoke if token valid
```

**Token Security**:
- **Storage**: Environment variables, never in code or logs
- **Expiration**: 1 hour (Cognito default)
- **Scopes**: Fine-grained (gateway-api/read, gateway-api/write)
- **Rotation**: Manual (no automatic rotation implemented)

**IAM Roles (Least Privilege)**:
```
Gateway Execution Role:
├─ Trust Policy: bedrock-agentcore.amazonaws.com
└─ Permissions: lambda:InvokeFunction (specific Lambda ARN)

Runtime Execution Role:
├─ Trust Policy: bedrock-agentcore.amazonaws.com
└─ Permissions:
   ├─ bedrock:InvokeModel (specific model ARN)
   ├─ bedrock-agentcore:GetMemory, CreateEvent, RetrieveMemory
   ├─ bedrock-agentcore:InvokeGateway, GetGateway
   ├─ bedrock-agent:Retrieve (specific KB ARN)
   ├─ logs:CreateLogGroup, CreateLogStream, PutLogEvents
   ├─ xray:PutTraceSegments, PutTelemetryRecords
   └─ ecr:GetAuthorizationToken, BatchGetImage
```

#### Data Protection

**In Transit**:
- All communication over TLS 1.2+
- HTTPS for UI → Runtime
- TLS for Runtime → AWS services

**At Rest**:
- DynamoDB encryption enabled (AWS managed keys)
- S3 encryption for knowledge base documents
- ECR encryption for container images

**PII Handling**:
- No customer PII logged to CloudWatch
- Order IDs are pseudonymized (ORD-001, not real customer IDs)
- Actor IDs are internal support agent identifiers, not customer data
- Conversation content stored in memory (encrypted at rest)

#### Network Security

**Current State**:
- Public network mode (no VPC)
- AgentCore Runtime in AWS managed VPC
- No direct network access to agent container

**Future Considerations**:
- VPC deployment for private database access (when integrating real order system)
- Security groups for Lambda functions
- VPC endpoints for AWS services

### 7.2 Compliance

#### Data Retention
- **Memory Events**: 30 days (configurable)
- **CloudWatch Logs**: 30 days (configurable)
- **X-Ray Traces**: 30 days (AWS default)
- **Knowledge Base**: Indefinite (manually managed)

#### Audit Trail
- All agent invocations logged with actor_id and timestamp
- All refund calculations logged with input parameters and results
- All gateway calls logged with OAuth scope and target
- Correlation IDs enable end-to-end request tracking

#### Privacy & Compliance
- **Internal Tool**: Not customer-facing, internal use only
- **Data Isolation**: Actor-based namespaces prevent cross-agent data leakage
- **No PII in Logs**: Customer data not logged to CloudWatch
- **GDPR/CCPA**: Not applicable (internal tool, no customer data)

#### Security Audit Recommendations
1. Regular review of IAM role permissions (quarterly)
2. OAuth token rotation policy (currently manual)
3. Penetration testing (annually)
4. Dependency vulnerability scanning (automated)
5. Secrets management audit (quarterly)

### 7.3 Cost Analysis

#### Current Cost Breakdown (Daily)

```
Service                     Cost/Day    % of Total    Notes
─────────────────────────────────────────────────────────────
Bedrock Model (Claude)      $1-2        15%          ~200K tokens/day
AgentCore Runtime           $3-5        40%          Serverless compute
AgentCore Memory            $0.50-1     8%           DynamoDB ops
AgentCore Gateway           $0.20-0.50  4%           MCP protocol
Lambda (Order Lookup)       $0          0%           Free tier
Cognito                     $0          0%           Free tier
CloudWatch Logs             $0.50       4%           ~1 GB/month
X-Ray                       $0          0%           Free tier
ECR                         $0.10       1%           Image storage
Knowledge Base              $2-3        23%          S3 + embeddings
Other (Data Transfer, etc.) $0.50       5%           Misc
─────────────────────────────────────────────────────────────
TOTAL                       $10-15/day  100%         Low traffic
```

#### Cost Drivers

**1. Model Inference (15%)**
- **Driver**: Token usage (input + output)
- **Current**: ~200K tokens/day (~100 requests × 2K tokens/request)
- **Optimization**:
  - Lower temperature (0.3) reduces retries
  - Concise system prompt reduces input tokens
  - Streaming responses don't reduce cost but improve UX

**2. AgentCore Runtime (40%)**
- **Driver**: Compute time (per-request + per-second)
- **Current**: ~100 requests/day × 2-5 seconds/request
- **Optimization**:
  - Reduce cold starts (provisioned concurrency, but increases cost)
  - Optimize container image size
  - Reduce session timeout (15 min → 5 min)

**3. Knowledge Base (23%)**
- **Driver**: S3 storage + embedding generation + retrieval queries
- **Current**: ~100 documents, ~50 queries/day
- **Optimization**:
  - Implement caching for frequently accessed policies
  - Reduce embedding dimensions (trade-off: accuracy)
  - Batch document updates

**4. AgentCore Memory (8%)**
- **Driver**: DynamoDB read/write operations + storage
- **Current**: ~100 events/day, 30-day retention
- **Optimization**:
  - Reduce top_k (3 → 2) for retrieval
  - Shorter retention (30 days → 14 days)
  - On-demand vs. provisioned capacity (already on-demand)

#### Cost Scaling Projections

```
Traffic Level          Daily Cost    Monthly Cost    Annual Cost
───────────────────────────────────────────────────────────────
Current (100 req/day)  $10-15        $300-450        $3,600-5,400
10x (1K req/day)       $100-150      $3K-4.5K        $36K-54K
100x (10K req/day)     $1K-1.5K      $30K-45K        $360K-540K
```

**Note**: 100x scaling would require architectural changes (caching, multi-region, etc.), which would alter cost structure.

#### Cost Optimization Opportunities

**Quick Wins (No Architecture Changes)**:
1. Reduce memory retention (30 days → 14 days): Save ~$0.25/day
2. Optimize system prompt length: Save ~$0.50/day
3. Implement knowledge base query caching: Save ~$1-2/day
4. Reduce session timeout (15 min → 5 min): Save ~$0.50/day
**Total Savings**: ~$2-3/day (~20% reduction)

**Medium-Term (Architecture Changes)**:
1. Implement Redis caching for KB queries: Save ~$2-3/day, Add ~$1/day (Redis)
2. Use cheaper model for simple queries: Save ~$0.50-1/day
3. Batch memory operations: Save ~$0.25/day
**Total Savings**: ~$2-4/day (~25% reduction)

**Long-Term (Significant Changes)**:
1. Fine-tune smaller model: Save ~$1-2/day, One-time cost ~$500-1000
2. Implement aggressive caching: Save ~$3-5/day, Add ~$2/day (infrastructure)
3. Optimize container runtime: Save ~$1-2/day
**Total Savings**: ~$3-7/day (~40% reduction)

#### Cost Monitoring & Alerts

**Current Alerts**:
- Daily cost >$20 (CloudWatch alarm)
- Monthly cost >$500 (AWS Cost Explorer)

**Recommended Alerts**:
- Hourly cost >$1 (detect runaway costs)
- Token usage >500K/day (detect abuse or bugs)
- Memory storage >10K events (detect retention issues)
- Knowledge Base queries >200/day (detect excessive retrieval)

#### Cost Attribution

**Current State**: No per-agent or per-request cost tracking

**Recommendation**: Tag all requests with actor_id, track:
- Token usage per agent
- Memory operations per agent
- Gateway calls per agent
- Total cost per agent per day

**Benefit**: Identify high-cost users, optimize for specific use cases

---


## 8. Technical Debt & Future Considerations

### 8.1 Current Technical Debt

#### High Priority (Address in 1-3 months)

**TD-1: Mock Order Data**
- **Issue**: Only 3 sample orders (ORD-001, ORD-002, ORD-003), no real order system integration
- **Impact**: Cannot test with real customer orders, limits production readiness
- **Effort**: 2-4 weeks (Lambda VPC config, database connection, error handling)
- **Risk**: High (blocks production use with real customers)

**TD-2: Hardcoded Business Rules**
- **Issue**: Return windows (90/30 days) and restocking fees (15%/20%) hardcoded in Python
- **Impact**: Policy changes require code changes and redeployment
- **Effort**: 1-2 weeks (externalize to configuration file or database)
- **Risk**: Medium (policy changes are infrequent but require engineering time)

**TD-3: Manual Policy Updates**
- **Issue**: Knowledge base documents manually updated, no automation
- **Impact**: Policies may become outdated, leading to incorrect information
- **Effort**: 2-3 weeks (implement automated ingestion pipeline)
- **Risk**: Medium (incorrect policy information affects customer trust)
- **Note**: KB created externally (not scripted in this repo), ID stored in `kb_config.json`

**TD-4: No Property-Based Tests**
- **Issue**: Refund calculations tested with unit tests, but no property-based tests
- **Impact**: Edge cases may not be covered, potential for calculation errors
- **Effort**: 1 week (implement hypothesis tests for mathematical properties)
- **Risk**: Medium (financial impact if calculations are incorrect)

#### Medium Priority (Address in 3-6 months)

**TD-5: Single Region Deployment**
- **Issue**: All resources in us-west-2, no geographic redundancy
- **Impact**: Regional outage affects all users
- **Effort**: 4-6 weeks (multi-region deployment, data replication, DNS failover)
- **Risk**: Low (acceptable for internal tool, but blocks customer-facing use)

**TD-6: No Circuit Breaker Pattern**
- **Issue**: No circuit breaker for gateway calls, potential for cascading failures
- **Impact**: Repeated failures to unavailable services waste resources
- **Effort**: 1-2 weeks (implement circuit breaker library)
- **Risk**: Low (graceful degradation already implemented)

**TD-7: Limited Business Metrics**
- **Issue**: Only technical metrics tracked, no business KPIs
- **Impact**: Cannot measure business outcomes (approval rates, refund amounts, etc.)
- **Effort**: 2-3 weeks (add custom CloudWatch metrics, build dashboard)
- **Risk**: Low (nice-to-have for internal tool)

**TD-8: No Synthetic Monitoring**
- **Issue**: No proactive health checks, failures only detected by real users
- **Impact**: Downtime not detected until users report issues
- **Effort**: 1 week (implement scheduled health checks)
- **Risk**: Low (low traffic, manual fallback available)

#### Low Priority (Address in 6-12 months)

**TD-9: No Rate Limiting**
- **Issue**: No per-user or global rate limiting
- **Impact**: Potential for abuse or runaway costs
- **Effort**: 1-2 weeks (implement rate limiting middleware)
- **Risk**: Very Low (internal tool, controlled access)

**TD-10: No Model Fallback**
- **Issue**: Single model (Claude Sonnet 4.5), no fallback if unavailable
- **Impact**: Agent completely unavailable if model fails
- **Effort**: 2-3 weeks (implement multi-model support)
- **Risk**: Very Low (Bedrock is highly available)

**TD-11: No A/B Testing Framework**
- **Issue**: Cannot test different prompts, models, or configurations
- **Impact**: Difficult to optimize agent performance
- **Effort**: 3-4 weeks (implement feature flags, A/B testing framework)
- **Risk**: Very Low (optimization, not critical functionality)

### 8.2 Architectural Evolution

#### Phase 1: Production Readiness (3-6 months)
**Goal**: Make agent production-ready for real customer orders

**Changes**:
1. Integrate with real order management system (replace mock data)
2. Externalize business rules to configuration (return windows, fees)
3. Implement automated policy ingestion pipeline
4. Add property-based tests for refund calculations
5. Implement synthetic monitoring and expanded alerting
6. Add business metrics dashboard

**Effort**: 3-4 engineer-months
**Risk**: Medium (requires coordination with order system team)

#### Phase 2: Customer-Facing (6-12 months)
**Goal**: Expose agent to customers for self-service returns

**Changes**:
1. Multi-region deployment for global users
2. Enhanced security (rate limiting, DDoS protection)
3. Stricter latency requirements (p95 <1 second)
4. 24/7 availability and on-call support
5. Customer feedback mechanism
6. Multi-language support
7. Compliance enhancements (GDPR, CCPA)

**Effort**: 6-8 engineer-months
**Risk**: High (significant architectural changes, compliance requirements)

#### Phase 3: Advanced Capabilities (12-18 months)
**Goal**: Expand agent capabilities beyond returns/refunds

**Changes**:
1. Initiate return shipping labels automatically
2. Process refunds with approval workflow
3. Handle exchanges (not just returns)
4. Integrate with CRM for customer history
5. Proactive notifications (return window expiring)
6. Predictive analytics (forecast return rates)

**Effort**: 8-12 engineer-months
**Risk**: High (requires integration with multiple systems)

### 8.3 Alternative Architectures Considered

#### Alternative 1: Synchronous Memory Processing
**Pros**: Preferences available immediately in same session
**Cons**: Increased latency (20-30 seconds per request), worse user experience
**Decision**: Rejected (async processing is acceptable trade-off)

#### Alternative 2: Multiple LLM Models
**Pros**: Fallback if primary model unavailable, cost optimization for simple queries
**Cons**: Increased complexity, testing burden, inconsistent responses
**Decision**: Deferred (single model sufficient for current needs)

#### Alternative 3: Database-Driven Business Rules
**Pros**: Policy changes without code deployment, admin UI for policy management
**Cons**: Increased complexity, database dependency, potential for misconfiguration
**Decision**: Deferred (hardcoded rules acceptable for MVP, revisit in Phase 1)

#### Alternative 4: Event-Driven Architecture (SQS/EventBridge)
**Pros**: Decoupled components, better scalability, async processing
**Cons**: Increased complexity, eventual consistency, debugging difficulty
**Decision**: Rejected (synchronous request/response sufficient for current scale)

### 8.4 Open Questions & Decisions Needed

#### OQ-1: Customer-Facing Roadmap
**Question**: Should the agent be exposed to customers for self-service?
**Impact**: 100x-1000x traffic increase, stricter requirements, multi-region deployment
**Decision Needed By**: Q2 2026 (product roadmap planning)
**Stakeholders**: Product, Engineering, Customer Support

#### OQ-2: Real Order System Integration
**Question**: When should we integrate with real order management system?
**Impact**: Blocks production use, requires VPC configuration, database access
**Decision Needed By**: Q1 2026 (engineering prioritization)
**Stakeholders**: Engineering, Operations, Order System Team

#### OQ-3: Policy Management Strategy
**Question**: How should we handle policy changes (hardcoded, config file, database, admin UI)?
**Impact**: Affects deployment frequency, policy update latency, complexity
**Decision Needed By**: Q2 2026 (Phase 1 planning)
**Stakeholders**: Product, Engineering, Operations

#### OQ-4: Cost vs. Performance Trade-offs
**Question**: Should we optimize for cost or performance (caching, faster model, provisioned capacity)?
**Impact**: Affects user experience, operational costs, architectural complexity
**Decision Needed By**: Q2 2026 (budget planning)
**Stakeholders**: Engineering, Finance, Product

#### OQ-5: Observability Investment
**Question**: What level of observability is needed (business metrics, synthetic monitoring, anomaly detection)?
**Impact**: Affects debugging capability, proactive issue detection, engineering time
**Decision Needed By**: Q1 2026 (engineering prioritization)
**Stakeholders**: Engineering, Operations, Product

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| **Actor ID** | Unique identifier for support agent, used for memory isolation |
| **AgentCore** | AWS service for deploying and managing AI agents |
| **Cold Start** | Initial request latency when container is not warm |
| **Graceful Degradation** | System continues with reduced functionality when components fail |
| **MCP** | Model Context Protocol, standard for tool integration |
| **OAuth 2.0** | Industry-standard authorization framework |
| **Restocking Fee** | Fee charged for returning opened/used items |
| **Session ID** | Unique identifier for conversation session (15-minute timeout) |
| **Top-k** | Number of most relevant items retrieved from memory |

## Appendix B: References

- [AgentCore Documentation](https://aws.github.io/bedrock-agentcore-starter-toolkit/)
- [Strands Agents Documentation](https://strandsagents.com/)
- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Repository](https://github.com/arvind-narain/returns-refunds-agent)
- [Current State Spec](../specs/returns-agent-current.yaml)

## Appendix C: Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-03-22 | Engineering Team | Initial system design document |

---

**Document Status**: Current State Analysis  
**Next Review**: Q2 2026 (before Phase 1 planning)  
**Approval Required**: Staff Engineer, Engineering Manager, Technical Lead
