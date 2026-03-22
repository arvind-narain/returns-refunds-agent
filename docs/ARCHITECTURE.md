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
   - Logic: Date validation, category rules
   - Output: Eligibility status, days remaining

2. **calculate_refund_amount**
   - Input: original_price, item_condition, return_reason
   - Logic: Condition-based calculation, restocking fees
   - Output: Refund amount, breakdown

3. **format_policy_response**
   - Input: policy_text, category
   - Logic: Text formatting, bullet points
   - Output: Customer-friendly format

#### Built-in Tools
- **current_time**: Returns current timestamp
- **retrieve**: Knowledge Base document retrieval

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
6. **Tool Execution** → Custom tools, Gateway, KB
7. **Memory Storage** → Save conversation
8. **Response** → Return to user

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
