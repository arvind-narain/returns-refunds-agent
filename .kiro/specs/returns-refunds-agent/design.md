---
title: Returns & Refunds Agent - Design Specification
version: 1.0.0
status: draft
created: 2026-03-22
updated: 2026-03-22
authors: [Arvind Narain]
---

# Returns & Refunds Agent - Design Specification

## 1. Design Overview

### 1.1 Architecture Pattern
The system follows a **serverless, event-driven architecture** with the following key patterns:

- **Agent Pattern**: Autonomous AI agent with tool-calling capabilities
- **Memory Pattern**: Persistent state management across sessions
- **Gateway Pattern**: External API integration via MCP protocol
- **Retrieval-Augmented Generation (RAG)**: Knowledge base integration for policy documents

### 1.2 Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| AI Model | Claude Sonnet 4.5 (Bedrock) | Natural language understanding and generation |
| Agent Framework | Strands Agents | Agent orchestration and tool management |
| Runtime Platform | AgentCore Runtime | Serverless deployment and scaling |
| Memory | AgentCore Memory | Persistent conversation state |
| Gateway | AgentCore Gateway | External API integration |
| Knowledge Base | Bedrock Knowledge Base | Document retrieval |
| Authentication | Cognito | OAuth 2.0 token management |
| Observability | CloudWatch + X-Ray | Logging, metrics, tracing |
| Language | Python 3.10+ | Implementation language |

## 2. System Architecture

### 2.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      Client Layer                                │
│  ┌──────────────────┐              ┌──────────────────┐         │
│  │  Streamlit UI    │              │   CLI Scripts    │         │
│  └────────┬─────────┘              └────────┬─────────┘         │
└───────────┼────────────────────────────────┼──────────────────┘
            │                                 │
            │         OAuth 2.0 Token         │
            └────────────────┬────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────┐
│                  AgentCore Runtime Container                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Agent Core (17_runtime_agent.py)            │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │  @app.entrypoint invoke(payload, context)          │  │   │
│  │  │  • Initialize model                                 │  │   │
│  │  │  • Configure memory                                 │  │   │
│  │  │  • Load tools                                       │  │   │
│  │  │  • Create agent                                     │  │   │
│  │  │  • Process request                                  │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  │                                                            │   │
│  │  ┌─────────────────────────────────────────────────────┐ │   │
│  │  │  Tool Layer                                         │ │   │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │ │   │
│  │  │  │ Custom Tools │  │ Built-in     │  │ Gateway  │ │ │   │
│  │  │  │              │  │ Tools        │  │ Tools    │ │ │   │
│  │  │  │ • Eligibility│  │ • retrieve   │  │ • Order  │ │ │   │
│  │  │  │ • Refund     │  │ • current_   │  │   Lookup │ │ │   │
│  │  │  │ • Format     │  │   time       │  │          │ │ │   │
│  │  │  └──────────────┘  └──────────────┘  └──────────┘ │ │   │
│  │  └─────────────────────────────────────────────────────┘ │   │
│  │                                                            │   │
│  │  ┌─────────────────────────────────────────────────────┐ │   │
│  │  │  Memory Session Manager                             │ │   │
│  │  │  • AgentCoreMemoryConfig                            │ │   │
│  │  │  • RetrievalConfig per namespace                    │ │   │
│  │  │  • Session state management                         │ │   │
│  │  └─────────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐    ┌──────────────┐    ┌──────────────────┐
│   AgentCore   │    │  AgentCore   │    │  Knowledge Base  │
│    Memory     │    │   Gateway    │    │   (Bedrock)      │
│               │    │              │    │                  │
│ DynamoDB      │    │ ┌──────────┐ │    │ S3 + Embeddings  │
│ • Preferences │    │ │  Lambda  │ │    │ • Policy Docs    │
│ • Semantic    │    │ │ Function │ │    │ • Return Rules   │
│ • Summary     │    │ └──────────┘ │    │ • FAQs           │
└───────────────┘    └──────────────┘    └──────────────────┘
```

### 2.2 Sequence Diagram: User Request Flow

```
User → Streamlit UI → Cognito → AgentCore Runtime → Agent → Memory
                                                      ↓
                                                    Model (Claude)
                                                      ↓
                                                    Tools
                                                      ↓
                                              ┌──────┴──────┐
                                              ↓             ↓
                                          Gateway      Knowledge Base
                                              ↓
                                          Lambda
```

## 3. Detailed Component Design

### 3.1 Agent Core Module

**File**: `src/agents/17_runtime_agent.py`

**Responsibilities**:
- Initialize Bedrock model with specified parameters
- Configure memory session manager with retrieval settings
- Load and register all tools (custom, built-in, gateway)
- Process user requests through agent loop
- Handle errors gracefully with user-friendly messages

**Key Functions**:

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

**Design Decisions**:
- Model initialization inside invoke() to avoid module-level state
- Fallback mechanism when gateway is unavailable
- Comprehensive logging at each step
- Error handling with user-friendly messages

### 3.2 Custom Tools Module

**Tools**:

1. **check_return_eligibility**
   - **Input**: purchase_date (str), item_category (str), order_id (str)
   - **Output**: dict with eligibility, reason, days_remaining
   - **Logic**: Date validation, category-based window lookup, eligibility calculation
   - **Error Handling**: Invalid date format, missing data

2. **calculate_refund_amount**
   - **Input**: original_price (float), item_condition (str), return_reason (str)
   - **Output**: dict with refund_amount, breakdown, fees
   - **Logic**: Condition-based percentage, restocking fee calculation
   - **Error Handling**: Invalid price, unknown condition

3. **format_policy_response**
   - **Input**: policy_text (str), category (str)
   - **Output**: str with formatted policy
   - **Logic**: Section parsing, bullet point formatting, header addition
   - **Error Handling**: Malformed text, encoding issues

**Design Principles**:
- Pure functions with no side effects
- Comprehensive input validation
- Detailed error messages
- Testable in isolation

### 3.3 Memory Integration

**Configuration**:

```python
AgentCoreMemoryConfig(
    memory_id=os.environ["MEMORY_ID"],
    session_id=context.session_id,
    actor_id=payload.get("actor_id", "default-actor"),
    retrieval_config={
        f"app/{actor_id}/semantic": RetrievalConfig(top_k=3),
        f"app/{actor_id}/preferences": RetrievalConfig(top_k=3),
        f"app/{actor_id}/{session_id}/summary": RetrievalConfig(top_k=2),
    }
)
```

**Memory Strategies**:

1. **Semantic Memory**
   - **Namespace**: `app/{actorId}/semantic`
   - **Purpose**: Store factual information (order details, product info)
   - **Retrieval**: Top 3 most relevant facts

2. **Preference Memory**
   - **Namespace**: `app/{actorId}/preferences`
   - **Purpose**: Store user preferences (communication method, language)
   - **Retrieval**: Top 3 most relevant preferences

3. **Summary Memory**
   - **Namespace**: `app/{actorId}/{sessionId}/summary`
   - **Purpose**: Store conversation summaries
   - **Retrieval**: Top 2 most recent summaries

**Design Decisions**:
- Actor-based isolation for multi-tenancy
- Session-based organization for conversation tracking
- Configurable top_k for retrieval tuning
- Graceful degradation if memory unavailable

### 3.4 Gateway Integration

**MCP Client Setup**:

```python
def create_mcp_client():
    """
    Create MCP client with OAuth authentication
    
    Returns:
        MCPClient or None if configuration incomplete
    """
    # Get OAuth token from Cognito
    # Create streamable HTTP client with bearer token
    # Return MCPClient instance
```

**Gateway Tools**:
- Dynamically loaded from MCP client
- Authenticated with OAuth 2.0 bearer token
- Scoped access (gateway-api/read, gateway-api/write)

**Design Decisions**:
- Lazy initialization (only when needed)
- Token refresh handled by Cognito
- Fallback to non-gateway mode if unavailable
- Connection kept alive during agent execution

### 3.5 Knowledge Base Integration

**Retrieve Tool Configuration**:

```python
retrieve(
    knowledgeBaseId=kb_id,
    region=REGION,
    text="search query"
)
```

**Design Decisions**:
- Knowledge base ID from environment variable
- Region-specific endpoint
- Semantic search for relevant documents
- Formatted results for readability

## 4. Data Models

### 4.1 Request Payload

```python
{
    "prompt": str,           # User input text
    "actor_id": str          # Optional user identifier
}
```

### 4.2 Eligibility Response

```python
{
    "eligible": bool,
    "reason": str,
    "order_id": str,
    "days_since_purchase": int,
    "days_remaining": int    # Only if eligible
}
```

### 4.3 Refund Calculation Response

```python
{
    "original_price": float,
    "refund_amount": float,
    "refund_percentage": int,
    "restocking_fee": float,
    "shipping_refunded": bool,
    "item_condition": str,
    "return_reason": str
}
```

### 4.4 Memory Event

```python
[
    ("user message text", "USER"),
    ("assistant response text", "ASSISTANT")
]
```

## 5. Configuration Management

### 5.1 Environment Variables

| Variable | Purpose | Required | Example |
|----------|---------|----------|---------|
| MEMORY_ID | AgentCore Memory resource ID | Yes | `my_memory-ABC123` |
| KNOWLEDGE_BASE_ID | Bedrock KB ID | Yes | `WJOU9NWICK` |
| GATEWAY_URL | AgentCore Gateway endpoint | No | `https://...` |
| COGNITO_CLIENT_ID | OAuth client ID | No | `abc123...` |
| COGNITO_CLIENT_SECRET | OAuth client secret | No | `secret...` |
| COGNITO_DISCOVERY_URL | OIDC discovery endpoint | No | `https://cognito-idp...` |
| OAUTH_SCOPES | OAuth scopes | No | `gateway-api/read gateway-api/write` |

### 5.2 Configuration Files

| File | Content | Sensitive |
|------|---------|-----------|
| `memory_config.json` | Memory ID | No |
| `cognito_config.json` | Client ID, secret, URLs | Yes |
| `gateway_config.json` | Gateway ID, URL | No |
| `runtime_config.json` | Agent ARN | No |
| `kb_config.json` | Knowledge base ID | No |

**Design Decision**: Configuration files excluded from Git via `.gitignore`

## 6. Error Handling Strategy

### 6.1 Error Categories

1. **User Input Errors**
   - Invalid date format
   - Missing required fields
   - Out-of-range values
   - **Response**: User-friendly error message with guidance

2. **Service Errors**
   - Memory unavailable
   - Gateway timeout
   - Knowledge base error
   - **Response**: Graceful degradation, continue with reduced functionality

3. **System Errors**
   - Model invocation failure
   - Configuration missing
   - Unexpected exceptions
   - **Response**: Generic error message, detailed logging

### 6.2 Error Handling Pattern

```python
try:
    # Primary operation
    result = perform_operation()
except SpecificError as e:
    logger.error(f"Specific error: {e}")
    # Fallback or user message
except Exception as e:
    logger.exception("Unexpected error")
    return "User-friendly generic message"
```

## 7. Security Design

### 7.1 Authentication Flow

```
User → Cognito (Client Credentials) → Access Token → Gateway Request
```

### 7.2 Authorization

- **IAM Roles**: Least-privilege permissions for each service
- **OAuth Scopes**: Fine-grained access control for gateway
- **Actor Isolation**: Memory namespaces prevent cross-user access

### 7.3 Data Protection

- **In Transit**: TLS 1.2+ for all network communication
- **At Rest**: DynamoDB encryption for memory data
- **Secrets**: Environment variables, never in code
- **PII**: No logging of sensitive customer information

## 8. Observability Design

### 8.1 Logging Strategy

**Log Levels**:
- **INFO**: Normal operations (invocation start/end, tool calls)
- **WARNING**: Degraded functionality (gateway unavailable)
- **ERROR**: Failures (tool errors, service errors)
- **EXCEPTION**: Unexpected errors with stack traces

**Log Format**:
```
[TIMESTAMP] [LEVEL] [COMPONENT] Message
```

### 8.2 Metrics

| Metric | Type | Purpose |
|--------|------|---------|
| Invocation Count | Counter | Track request volume |
| Invocation Latency | Histogram | Monitor performance |
| Tool Call Count | Counter | Track tool usage |
| Error Rate | Counter | Monitor failures |
| Memory Retrieval Time | Histogram | Monitor memory performance |

### 8.3 Tracing

- **X-Ray Integration**: Distributed tracing across services
- **Spans**: Agent invocation, tool calls, memory operations
- **Correlation IDs**: Track requests end-to-end

## 9. Deployment Design

### 9.1 Deployment Architecture

```
Local Development → Docker Build → ECR Push → AgentCore Runtime Deploy
```

### 9.2 Deployment Steps

1. **Configure**: Set entrypoint, role, environment variables
2. **Build**: Create Docker container with dependencies
3. **Push**: Upload to ECR
4. **Deploy**: Create AgentCore Runtime resource
5. **Verify**: Check status, test invocation

### 9.3 Rollback Strategy

- Keep previous container images in ECR
- Redeploy previous version if issues detected
- Monitor metrics during rollout

## 10. Testing Strategy

### 10.1 Unit Tests

- Test each custom tool in isolation
- Mock external dependencies
- Verify error handling
- Check edge cases

### 10.2 Integration Tests

- Test agent with real services
- Verify memory integration
- Test gateway connectivity
- Validate knowledge base retrieval

### 10.3 End-to-End Tests

- Test complete user flows
- Verify multi-turn conversations
- Test error scenarios
- Validate observability

## 11. Performance Optimization

### 11.1 Latency Optimization

- **Model Selection**: Claude Sonnet 4.5 for balance of speed and quality
- **Memory Retrieval**: Limit top_k to reduce latency
- **Tool Execution**: Parallel execution where possible
- **Caching**: Session state cached in memory

### 11.2 Cost Optimization

- **Serverless**: Pay only for actual usage
- **Memory**: Efficient retrieval with top_k limits
- **Model**: Use appropriate temperature (0.3) to reduce retries

## 12. Design Decisions Log

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Strands Agents Framework | Mature, well-documented, AgentCore integration | LangChain, CrewAI |
| Claude Sonnet 4.5 | Best balance of performance and cost | GPT-4, Claude Opus |
| Python 3.10+ | Required by Strands, good ecosystem | Node.js, Go |
| AgentCore Runtime | Serverless, auto-scaling, managed | ECS, Lambda |
| OAuth 2.0 | Industry standard, secure | API keys, IAM |
| CloudWatch | Native AWS integration | Datadog, New Relic |

## 13. Future Enhancements

### 13.1 Planned Features

1. **Multi-language Support**: Detect and respond in user's language
2. **Proactive Notifications**: Alert users about expiring return windows
3. **Image Analysis**: Process product photos for condition assessment
4. **Sentiment Analysis**: Detect frustrated customers, escalate to human
5. **A/B Testing**: Test different prompts and tool configurations

### 13.2 Scalability Improvements

1. **Caching Layer**: Redis for frequently accessed data
2. **Read Replicas**: Scale knowledge base queries
3. **Regional Deployment**: Multi-region for global users
4. **CDN**: Cache static content for UI

## 14. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-03-22 | Arvind Narain | Initial design specification |

---

**Document Status**: Draft  
**Next Review Date**: 2026-04-01  
**Approval Required**: Technical Lead, Security Team
