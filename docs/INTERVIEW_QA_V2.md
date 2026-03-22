# System Design Interview Questions: Returns & Refunds Platform (V2)

**Document Status**: Interview Preparation Guide  
**Version**: 2.0.0  
**Date**: 2026-03-22  
**Audience**: Senior/Staff Engineer Candidates  
**Based On**: V2 Specification and Future Enhancements

---

## Overview

This document contains system design interview questions based on the V2 returns and refunds platform (future enhancements). Each question includes:
- Problem statement with realistic context
- Key areas to explore during discussion
- Detailed answer outline from senior/staff engineer perspective
- Common pitfalls and anti-patterns to avoid
- Tradeoff analysis with quantitative reasoning

The questions cover:
- **Observability**: Safety monitoring via Gateway and Runtime logs
- **Evolution**: Single-tenant to multi-tenant architecture
- **Evolution**: Single-region to multi-region deployment

---

## Table of Contents

1. [Observability: Safety Monitoring via Gateway and Runtime Logs](#question-4-observability-safety-monitoring-via-gateway-and-runtime-logs)
2. [Evolution: Single-Tenant to Multi-Tenant Architecture](#question-5-evolution-single-tenant-to-multi-tenant-architecture)
3. [Evolution: Single-Region to Multi-Region Deployment](#question-6-evolution-single-region-to-multi-region-deployment)

---

## Question 4: Observability: Safety Monitoring via Gateway and Runtime Logs

### Problem Statement

"Our returns agent runs on AgentCore Runtime and uses Gateway for external API calls. We need to monitor safety: Are there security issues? Is PII being leaked? Are there performance bottlenecks? How would you use CloudWatch logs, X-Ray traces, and Runtime metrics to monitor safety and performance? What specific log patterns would you look for, and how would you debug production issues?"

### Context
- Current: Basic CloudWatch logs, no structured analysis
- Target: Comprehensive safety monitoring, performance debugging, security auditing
- Components: AgentCore Runtime (agent container), Gateway (MCP protocol), Lambda (order lookup)
- Scale: 10K-50K requests/day, need to detect security issues within minutes

### Strong Answer Outline

#### 1. CloudWatch Logs Architecture for AgentCore

**Log Groups and Streams**:
```
/aws/bedrock-agentcore/runtimes/{agent-arn}
├─ agent-invocations/          # Agent request/response logs
├─ tool-executions/            # Tool call logs
├─ gateway-calls/              # Gateway MCP calls
├─ errors/                     # Error logs
└─ security-events/            # Security-related events

/aws/lambda/{function-name}
└─ order-lookup-function/      # Lambda function logs

/aws/bedrock-agentcore/gateway/{gateway-id}
├─ target-invocations/         # Gateway target calls
├─ auth-events/                # OAuth token validation
└─ errors/                     # Gateway errors
```

**Structured Logging Format**:
```python
class StructuredLogger:
    """
    Structured logging for AgentCore Runtime.
    """
    def log_agent_invocation(self, request, response, duration_ms):
        """
        Log every agent invocation with structured data.
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'log_type': 'agent_invocation',
            'request_id': request.correlation_id,
            'actor_id': request.actor_id,
            'session_id': request.session_id,
            
            # Request details (sanitized)
            'prompt': self.sanitize_pii(request.prompt),
            'prompt_length': len(request.prompt),
            
            # Response details (sanitized)
            'response': self.sanitize_pii(response.text),
            'response_length': len(response.text),
            
            # Performance
            'duration_ms': duration_ms,
            'model_id': request.model_id,
            'temperature': request.temperature,
            
            # Tool usage
            'tools_called': [t['name'] for t in response.tool_calls],
            'tool_call_count': len(response.tool_calls),
            
            # Tokens (cost tracking)
            'input_tokens': response.usage.input_tokens,
            'output_tokens': response.usage.output_tokens,
            'total_tokens': response.usage.total_tokens,
            
            # Status
            'success': response.success,
            'error_type': response.error_type if not response.success else None
        }
        
        logger.info(json.dumps(log_entry))
```


#### 2. Safety Monitoring Patterns

**PII Detection and Leakage Prevention**:
```python
class PIIDetector:
    """
    Detect and sanitize PII in logs.
    """
    def __init__(self):
        # Regex patterns for common PII
        self.patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            'address': r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd)\b'
        }
    
    def detect_pii(self, text):
        """
        Detect PII in text and return findings.
        """
        findings = []
        
        for pii_type, pattern in self.patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                findings.append({
                    'type': pii_type,
                    'count': len(matches),
                    'samples': matches[:3]  # First 3 matches
                })
        
        return findings
    
    def sanitize_pii(self, text):
        """
        Replace PII with placeholders.
        """
        sanitized = text
        
        for pii_type, pattern in self.patterns.items():
            sanitized = re.sub(pattern, f'[{pii_type.upper()}_REDACTED]', sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    def log_pii_detection(self, request_id, findings):
        """
        Log PII detection events for security audit.
        """
        if findings:
            logger.warning('pii_detected', extra={
                'request_id': request_id,
                'pii_types': [f['type'] for f in findings],
                'pii_count': sum(f['count'] for f in findings),
                'severity': 'high'
            })
            
            # Emit CloudWatch metric
            cloudwatch.put_metric_data(
                Namespace='Security',
                MetricData=[{
                    'MetricName': 'PIIDetected',
                    'Value': 1,
                    'Unit': 'Count',
                    'Dimensions': [
                        {'Name': 'RequestId', 'Value': request_id}
                    ]
                }]
            )
```

**Security Event Monitoring**:
```python
class SecurityMonitor:
    """
    Monitor security events in AgentCore Runtime and Gateway.
    """
    def monitor_auth_failures(self):
        """
        Detect authentication failures and potential attacks.
        """
        # Query CloudWatch Logs for auth failures
        query = """
        fields @timestamp, actor_id, error_type, ip_address
        | filter log_type = "auth_failure"
        | stats count() as failure_count by actor_id, ip_address
        | filter failure_count > 5
        """
        
        results = logs_insights.start_query(
            logGroupName='/aws/bedrock-agentcore/gateway/*',
            startTime=int((datetime.now() - timedelta(minutes=15)).timestamp()),
            endTime=int(datetime.now().timestamp()),
            queryString=query
        )
        
        # Alert on suspicious patterns
        for result in results:
            if result['failure_count'] > 10:
                self.alert_security_team({
                    'event': 'brute_force_attempt',
                    'actor_id': result['actor_id'],
                    'ip_address': result['ip_address'],
                    'failure_count': result['failure_count'],
                    'severity': 'critical'
                })
    
    def monitor_unusual_access_patterns(self):
        """
        Detect unusual access patterns (e.g., access from new locations).
        """
        # Query for access from new IP addresses
        query = """
        fields @timestamp, actor_id, ip_address, geolocation
        | filter log_type = "agent_invocation"
        | stats count() as request_count by actor_id, ip_address, geolocation
        | filter request_count < 5
        """
        
        results = logs_insights.start_query(
            logGroupName='/aws/bedrock-agentcore/runtimes/*',
            startTime=int((datetime.now() - timedelta(hours=1)).timestamp()),
            endTime=int(datetime.now().timestamp()),
            queryString=query
        )
        
        # Check against known IP addresses for each actor
        for result in results:
            known_ips = get_known_ips(result['actor_id'])
            if result['ip_address'] not in known_ips:
                self.alert_security_team({
                    'event': 'access_from_new_location',
                    'actor_id': result['actor_id'],
                    'ip_address': result['ip_address'],
                    'geolocation': result['geolocation'],
                    'severity': 'medium'
                })
```


#### 3. X-Ray Distributed Tracing

**End-to-End Request Tracing**:
```python
class XRayTracer:
    """
    Instrument AgentCore Runtime with X-Ray for distributed tracing.
    """
    def trace_agent_invocation(self, request):
        """
        Create X-Ray trace for entire agent invocation.
        """
        # Start root segment
        with xray_recorder.in_segment('agent_invocation') as segment:
            segment.put_annotation('actor_id', request.actor_id)
            segment.put_annotation('session_id', request.session_id)
            segment.put_metadata('prompt_length', len(request.prompt))
            
            # Trace model inference
            with xray_recorder.in_subsegment('bedrock_inference') as subsegment:
                subsegment.put_annotation('model_id', request.model_id)
                response = invoke_bedrock_model(request)
                subsegment.put_metadata('input_tokens', response.usage.input_tokens)
                subsegment.put_metadata('output_tokens', response.usage.output_tokens)
            
            # Trace tool calls
            for tool_call in response.tool_calls:
                with xray_recorder.in_subsegment(f'tool_{tool_call.name}') as subsegment:
                    subsegment.put_annotation('tool_name', tool_call.name)
                    tool_result = execute_tool(tool_call)
                    subsegment.put_metadata('tool_result', tool_result)
            
            # Trace Gateway calls
            if 'lookup_order' in [t.name for t in response.tool_calls]:
                with xray_recorder.in_subsegment('gateway_call') as subsegment:
                    subsegment.put_annotation('gateway_id', gateway_id)
                    subsegment.put_annotation('target_name', 'lookup_order')
                    gateway_result = call_gateway(gateway_id, 'lookup_order', inputs)
                    subsegment.put_metadata('latency_ms', gateway_result.latency_ms)
            
            return response
```

**X-Ray Service Map Analysis**:
```
Agent Invocation (2.3s avg)
    │
    ├─> Bedrock Inference (1.8s avg, 95% success)
    │   └─> Claude Sonnet 4.5
    │
    ├─> Tool: check_eligibility (15ms avg, 99% success)
    │   └─> Policy Engine
    │
    ├─> Tool: lookup_order (320ms avg, 97% success)
    │   └─> AgentCore Gateway (280ms avg)
    │       └─> Lambda: OrderLookupFunction (250ms avg)
    │           └─> DynamoDB: orders-table (50ms avg)
    │
    └─> Tool: calculate_refund (12ms avg, 99% success)
        └─> Policy Engine
```

**Performance Bottleneck Detection**:
```python
def analyze_xray_traces(time_range_minutes=60):
    """
    Analyze X-Ray traces to identify performance bottlenecks.
    """
    # Query X-Ray for slow traces
    filter_expression = 'duration > 5'  # >5 seconds
    
    traces = xray.get_trace_summaries(
        StartTime=datetime.now() - timedelta(minutes=time_range_minutes),
        EndTime=datetime.now(),
        FilterExpression=filter_expression
    )
    
    # Analyze bottlenecks
    bottlenecks = {}
    for trace in traces['TraceSummaries']:
        trace_id = trace['Id']
        trace_details = xray.batch_get_traces(TraceIds=[trace_id])
        
        # Find slowest segment
        for segment in trace_details['Traces'][0]['Segments']:
            segment_data = json.loads(segment['Document'])
            duration = segment_data.get('end_time', 0) - segment_data.get('start_time', 0)
            
            segment_name = segment_data.get('name')
            if segment_name not in bottlenecks:
                bottlenecks[segment_name] = []
            
            bottlenecks[segment_name].append(duration)
    
    # Calculate statistics
    for segment_name, durations in bottlenecks.items():
        print(f"{segment_name}:")
        print(f"  Count: {len(durations)}")
        print(f"  Avg: {np.mean(durations):.2f}s")
        print(f"  p95: {np.percentile(durations, 95):.2f}s")
        print(f"  p99: {np.percentile(durations, 99):.2f}s")
```


#### 4. Runtime Metrics and Debugging

**CloudWatch Metrics for AgentCore Runtime**:
```python
# Key metrics to track
runtime_metrics = {
    'InvocationCount': 'Total agent invocations',
    'InvocationDuration': 'End-to-end latency (ms)',
    'InvocationErrors': 'Failed invocations',
    'ModelInferenceLatency': 'Bedrock model latency (ms)',
    'ToolCallCount': 'Number of tool calls per invocation',
    'ToolCallLatency': 'Tool execution latency (ms)',
    'ToolCallErrors': 'Failed tool calls',
    'TokenUsage': 'Total tokens consumed',
    'CostPerInvocation': 'Estimated cost ($)'
}

# CloudWatch Logs Insights queries for debugging
debugging_queries = {
    'slow_requests': """
        fields @timestamp, request_id, duration_ms, tools_called
        | filter duration_ms > 5000
        | sort duration_ms desc
        | limit 20
    """,
    
    'error_analysis': """
        fields @timestamp, request_id, error_type, error_message
        | filter success = false
        | stats count() by error_type
    """,
    
    'tool_performance': """
        fields @timestamp, tool_name, latency_ms
        | filter log_type = "tool_execution"
        | stats avg(latency_ms) as avg_latency, max(latency_ms) as max_latency by tool_name
    """,
    
    'token_usage_by_actor': """
        fields @timestamp, actor_id, total_tokens
        | stats sum(total_tokens) as total_tokens by actor_id
        | sort total_tokens desc
    """
}
```

**Production Debugging Workflow**:
```
1. Identify Issue (Alert or User Report)
   ├─ Check CloudWatch Dashboard for anomalies
   ├─ Review recent alarms
   └─ Check X-Ray service map for errors

2. Gather Context (CloudWatch Logs Insights)
   ├─ Query for error logs in time window
   ├─ Find affected request IDs
   └─ Identify error patterns

3. Trace Request Flow (X-Ray)
   ├─ Look up trace by request ID
   ├─ Analyze segment durations
   ├─ Identify bottleneck or failure point
   └─ Check subsegment errors

4. Analyze Root Cause
   ├─ Gateway logs: Check OAuth, target invocation
   ├─ Lambda logs: Check function execution
   ├─ Runtime logs: Check agent behavior
   └─ DynamoDB metrics: Check throttling

5. Implement Fix
   ├─ Code change (if bug)
   ├─ Configuration change (if misconfiguration)
   ├─ Scaling adjustment (if capacity issue)
   └─ Deploy and verify

6. Post-Mortem
   ├─ Document root cause
   ├─ Add monitoring to prevent recurrence
   ├─ Update runbooks
   └─ Share learnings with team
```

#### 5. Common Pitfalls and Key Takeaways

**Pitfalls**:
- ❌ Logging PII without sanitization (compliance violation)
- ❌ No structured logging (hard to query)
- ❌ Ignoring X-Ray traces (missing performance insights)
- ❌ No alerting on security events (delayed incident response)

**Key Takeaways**:
- Structured logging with PII sanitization for all components
- X-Ray distributed tracing for end-to-end visibility
- CloudWatch Logs Insights for ad-hoc debugging
- Security monitoring: Auth failures, PII detection, unusual access
- Performance monitoring: Latency percentiles, bottleneck detection
- Cost tracking: Token usage, invocation costs per actor

---

## Question 5: Evolution: Single-Tenant to Multi-Tenant Architecture

### Problem Statement

"Our returns platform currently serves a single merchant (internal tool). We want to evolve it into a multi-tenant SaaS platform serving 100-500 merchants. Each merchant needs isolated data, custom policies, and separate billing. How would you design the multi-tenant architecture? What are the key isolation strategies, and how would you handle tenant-specific customization without code changes?"

### Context
- Current: Single tenant, hardcoded policies, shared infrastructure
- Target: 100-500 tenants, isolated data, configurable policies, tenant-specific billing
- Constraints: Maintain <1s latency, 99.9% availability, GDPR compliance
- Scale: 10K-50K requests/day across all tenants

### Strong Answer Outline

#### 1. Tenant Isolation Strategies

**Three Isolation Models**:
```
┌─────────────────────────────────────────────────────────────┐
│  Model 1: Silo (Dedicated Infrastructure per Tenant)        │
│  ├─ Pros: Maximum isolation, custom scaling, compliance     │
│  ├─ Cons: High cost, operational complexity                 │
│  └─ Use Case: Enterprise customers, regulated industries    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Model 2: Pool (Shared Infrastructure, Logical Isolation)   │
│  ├─ Pros: Cost-effective, easy to scale, simple ops         │
│  ├─ Cons: Noisy neighbor, limited customization             │
│  └─ Use Case: SMB customers, standard features              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Model 3: Bridge (Hybrid - Critical Silo, Rest Pool)        │
│  ├─ Pros: Balance cost and isolation                        │
│  ├─ Cons: Complexity in routing and management              │
│  └─ Use Case: Mixed customer base (RECOMMENDED)             │
└─────────────────────────────────────────────────────────────┘
```

**Recommended: Bridge Model Architecture**:
```
┌─────────────────────────────────────────────────────────────┐
│  Tenant Routing Layer (API Gateway)                         │
│  ├─ Extract tenant_id from JWT token                        │
│  ├─ Route to silo or pool based on tenant tier              │
│  └─ Apply tenant-specific rate limits                       │
└─────────────────────────────────────────────────────────────┘
                          │
            ┌─────────────┴─────────────┐
            │                           │
┌───────────▼──────────┐    ┌───────────▼──────────┐
│  Silo Tenants        │    │  Pool Tenants        │
│  (Enterprise)        │    │  (SMB)               │
│                      │    │                      │
│  Dedicated:          │    │  Shared:             │
│  ├─ Agent Runtime    │    │  ├─ Agent Runtime    │
│  ├─ DynamoDB Table   │    │  ├─ DynamoDB Table   │
│  ├─ S3 Bucket        │    │  │   (tenant_id PK)  │
│  └─ VPC              │    │  └─ Shared VPC       │
└──────────────────────┘    └──────────────────────┘
```

#### 2. Data Isolation Design

**DynamoDB Multi-Tenant Schema (Pool Model)**:
```python
# Tenant-aware partition key design
class MultiTenantSchema:
    """
    DynamoDB schema with tenant isolation.
    """
    # Decision Log Table
    decision_log = {
        'table_name': 'decision_log',
        'partition_key': 'tenant_id#decision_id',  # Composite key
        'sort_key': 'timestamp',
        'gsi': [
            {
                'name': 'tenant-customer-index',
                'partition_key': 'tenant_id#customer_id',
                'sort_key': 'timestamp'
            },
            {
                'name': 'tenant-type-index',
                'partition_key': 'tenant_id#decision_type',
                'sort_key': 'timestamp'
            }
        ]
    }
    
    # Policy Configuration Table
    policy_config = {
        'table_name': 'policy_config',
        'partition_key': 'tenant_id',
        'sort_key': 'policy_version',
        'attributes': {
            'tenant_id': 'string',
            'policy_version': 'string',
            'policy_data': 'map',  # YAML policy as JSON
            'effective_date': 'string',
            'created_at': 'string',
            'created_by': 'string'
        }
    }
    
    # Tenant Metadata Table
    tenant_metadata = {
        'table_name': 'tenant_metadata',
        'partition_key': 'tenant_id',
        'attributes': {
            'tenant_id': 'string',
            'tenant_name': 'string',
            'tier': 'string',  # 'enterprise', 'professional', 'starter'
            'status': 'string',  # 'active', 'suspended', 'trial'
            'created_at': 'string',
            'billing_plan': 'string',
            'rate_limit': 'number',  # Requests per minute
            'features': 'list',  # Enabled features
            'isolation_model': 'string'  # 'silo' or 'pool'
        }
    }

# Query with tenant isolation
def get_customer_decisions(tenant_id, customer_id, limit=10):
    """
    Query decisions with automatic tenant isolation.
    """
    response = dynamodb.query(
        TableName='decision_log',
        IndexName='tenant-customer-index',
        KeyConditionExpression='tenant_id#customer_id = :pk',
        ExpressionAttributeValues={
            ':pk': f'{tenant_id}#{customer_id}'
        },
        Limit=limit,
        ScanIndexForward=False  # Newest first
    )
    
    return response['Items']
```

**S3 Multi-Tenant Structure**:
```
s3://returns-platform-data/
├─ tenants/
│  ├─ tenant-001/
│  │  ├─ policies/
│  │  │  ├─ default_policy_v1.yaml
│  │  │  └─ custom_policy_v2.yaml
│  │  ├─ audit-logs/
│  │  │  └─ 2026/03/22/decisions.json
│  │  └─ documents/
│  │     └─ return_policy.pdf
│  ├─ tenant-002/
│  │  └─ ...
│  └─ tenant-003/
│     └─ ...
└─ shared/
   └─ templates/
      └─ default_policy_template.yaml
```


#### 3. Tenant-Specific Customization

**Policy Engine with Tenant Overrides**:
```python
class MultiTenantPolicyEngine:
    """
    Policy engine with tenant-specific customization.
    """
    def __init__(self):
        self.cache = {}  # In-memory cache
        self.redis = RedisClient()  # Shared cache
    
    def get_policy(self, tenant_id, policy_version='latest'):
        """
        Load tenant-specific policy with caching.
        """
        cache_key = f"policy:{tenant_id}:{policy_version}"
        
        # Check cache
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        cached_policy = self.redis.get(cache_key)
        if cached_policy:
            policy = json.loads(cached_policy)
            self.cache[cache_key] = policy
            return policy
        
        # Load from DynamoDB
        response = dynamodb.get_item(
            TableName='policy_config',
            Key={
                'tenant_id': tenant_id,
                'policy_version': policy_version if policy_version != 'latest' else self.get_latest_version(tenant_id)
            }
        )
        
        if 'Item' not in response:
            # Fall back to default policy
            return self.get_default_policy()
        
        policy = response['Item']['policy_data']
        
        # Cache for 5 minutes
        self.redis.setex(cache_key, 300, json.dumps(policy))
        self.cache[cache_key] = policy
        
        return policy
    
    def evaluate_with_tenant_context(self, tenant_id, return_request):
        """
        Evaluate return request with tenant-specific policy.
        """
        # Load tenant policy
        policy = self.get_policy(tenant_id)
        
        # Load tenant metadata (for feature flags, rate limits)
        tenant = self.get_tenant_metadata(tenant_id)
        
        # Check if tenant has access to feature
        if 'advanced_fraud_detection' in tenant['features']:
            risk_score = self.calculate_risk_score_ml(return_request)
        else:
            risk_score = self.calculate_risk_score_rules(return_request)
        
        # Evaluate eligibility
        eligibility = self.check_eligibility(policy, return_request)
        
        # Calculate refund
        refund = self.calculate_refund(policy, return_request)
        
        return {
            'eligible': eligibility['eligible'],
            'refund_amount': refund['amount'],
            'risk_score': risk_score,
            'policy_version': policy['version'],
            'tenant_id': tenant_id
        }
```

**Feature Flags and Tiering**:
```python
class TenantFeatureManager:
    """
    Manage feature access by tenant tier.
    """
    FEATURE_MATRIX = {
        'starter': [
            'basic_returns',
            'policy_configuration',
            'email_notifications'
        ],
        'professional': [
            'basic_returns',
            'policy_configuration',
            'email_notifications',
            'advanced_analytics',
            'custom_branding',
            'api_access'
        ],
        'enterprise': [
            'basic_returns',
            'policy_configuration',
            'email_notifications',
            'advanced_analytics',
            'custom_branding',
            'api_access',
            'advanced_fraud_detection',
            'dedicated_support',
            'sla_guarantees',
            'custom_integrations'
        ]
    }
    
    def has_feature(self, tenant_id, feature_name):
        """
        Check if tenant has access to feature.
        """
        tenant = self.get_tenant_metadata(tenant_id)
        tier = tenant['tier']
        
        return feature_name in self.FEATURE_MATRIX.get(tier, [])
    
    def enforce_rate_limit(self, tenant_id):
        """
        Enforce tenant-specific rate limits.
        """
        tenant = self.get_tenant_metadata(tenant_id)
        rate_limit = tenant['rate_limit']  # Requests per minute
        
        # Check current usage
        current_usage = self.redis.incr(f"rate_limit:{tenant_id}:{int(time.time() / 60)}")
        self.redis.expire(f"rate_limit:{tenant_id}:{int(time.time() / 60)}", 60)
        
        if current_usage > rate_limit:
            raise RateLimitExceeded(f"Tenant {tenant_id} exceeded rate limit: {rate_limit} req/min")
```

#### 4. Authentication and Authorization

**Multi-Tenant JWT Structure**:
```python
# JWT token payload
{
    "sub": "user_12345",  # User ID
    "tenant_id": "tenant_001",  # Tenant ID (critical)
    "role": "agent",  # User role within tenant
    "permissions": ["read_returns", "approve_returns"],
    "tier": "professional",
    "iss": "https://auth.returns-platform.com",
    "exp": 1711123456,
    "iat": 1711119856
}

# Lambda authorizer for API Gateway
def lambda_authorizer(event, context):
    """
    Validate JWT and extract tenant context.
    """
    token = event['authorizationToken'].replace('Bearer ', '')
    
    try:
        # Verify JWT signature
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=['RS256'])
        
        # Extract tenant_id
        tenant_id = payload.get('tenant_id')
        if not tenant_id:
            raise Exception('Missing tenant_id in token')
        
        # Check tenant status
        tenant = get_tenant_metadata(tenant_id)
        if tenant['status'] != 'active':
            raise Exception(f'Tenant {tenant_id} is not active')
        
        # Build policy document
        return {
            'principalId': payload['sub'],
            'policyDocument': {
                'Version': '2012-10-17',
                'Statement': [{
                    'Action': 'execute-api:Invoke',
                    'Effect': 'Allow',
                    'Resource': event['methodArn']
                }]
            },
            'context': {
                'tenant_id': tenant_id,
                'user_id': payload['sub'],
                'role': payload['role'],
                'tier': payload['tier']
            }
        }
    
    except Exception as e:
        raise Exception('Unauthorized')
```

#### 5. Billing and Cost Attribution

**Usage Tracking per Tenant**:
```python
class TenantUsageTracker:
    """
    Track usage metrics for billing.
    """
    def track_invocation(self, tenant_id, request, response):
        """
        Track agent invocation for billing.
        """
        usage_entry = {
            'tenant_id': tenant_id,
            'timestamp': datetime.now().isoformat(),
            'request_id': request.correlation_id,
            
            # Billable metrics
            'invocation_count': 1,
            'input_tokens': response.usage.input_tokens,
            'output_tokens': response.usage.output_tokens,
            'total_tokens': response.usage.total_tokens,
            'tool_calls': len(response.tool_calls),
            'duration_ms': response.duration_ms,
            
            # Cost calculation
            'model_cost': self.calculate_model_cost(response.usage),
            'tool_cost': self.calculate_tool_cost(response.tool_calls),
            'total_cost': self.calculate_total_cost(response)
        }
        
        # Write to DynamoDB for billing
        dynamodb.put_item(
            TableName='tenant_usage',
            Item=usage_entry
        )
        
        # Emit CloudWatch metric
        cloudwatch.put_metric_data(
            Namespace='Billing',
            MetricData=[
                {
                    'MetricName': 'InvocationCost',
                    'Value': usage_entry['total_cost'],
                    'Unit': 'None',
                    'Dimensions': [
                        {'Name': 'TenantId', 'Value': tenant_id},
                        {'Name': 'Tier', 'Value': self.get_tenant_tier(tenant_id)}
                    ]
                }
            ]
        )
    
    def generate_monthly_invoice(self, tenant_id, month):
        """
        Generate monthly invoice for tenant.
        """
        # Query usage for month
        usage = dynamodb.query(
            TableName='tenant_usage',
            KeyConditionExpression='tenant_id = :tid AND begins_with(timestamp, :month)',
            ExpressionAttributeValues={
                ':tid': tenant_id,
                ':month': month  # '2026-03'
            }
        )
        
        # Aggregate costs
        total_invocations = len(usage['Items'])
        total_tokens = sum(item['total_tokens'] for item in usage['Items'])
        total_cost = sum(item['total_cost'] for item in usage['Items'])
        
        # Apply tier-based pricing
        tenant = self.get_tenant_metadata(tenant_id)
        tier_discount = self.get_tier_discount(tenant['tier'])
        final_cost = total_cost * (1 - tier_discount)
        
        return {
            'tenant_id': tenant_id,
            'month': month,
            'invocations': total_invocations,
            'tokens': total_tokens,
            'base_cost': total_cost,
            'discount': tier_discount,
            'final_cost': final_cost
        }
```


#### 6. Migration Strategy from Single to Multi-Tenant

**Phase 1: Add Tenant Context (2-3 weeks)**
```
1. Add tenant_id to all data models
   ├─ Update DynamoDB schemas (add tenant_id to partition keys)
   ├─ Update S3 folder structure (tenant-specific folders)
   └─ Update API contracts (require tenant_id in requests)

2. Implement tenant-aware authentication
   ├─ Add tenant_id to JWT tokens
   ├─ Update Lambda authorizer
   └─ Add tenant validation middleware

3. Update application code
   ├─ Pass tenant_id through all function calls
   ├─ Add tenant_id to all database queries
   └─ Add tenant_id to all logs

4. Migrate existing data
   ├─ Assign tenant_id='default' to existing records
   ├─ Backfill tenant_id in DynamoDB
   └─ Reorganize S3 objects
```

**Phase 2: Implement Isolation (3-4 weeks)**
```
1. Deploy pool infrastructure
   ├─ Shared AgentCore Runtime with tenant routing
   ├─ Shared DynamoDB tables with tenant isolation
   └─ Shared S3 bucket with tenant prefixes

2. Implement tenant management
   ├─ Tenant onboarding API
   ├─ Tenant configuration UI
   └─ Tenant status management

3. Add feature flags and tiering
   ├─ Feature matrix by tier
   ├─ Rate limiting per tenant
   └─ Usage tracking for billing

4. Testing and validation
   ├─ Test tenant isolation (no data leakage)
   ├─ Test performance under multi-tenant load
   └─ Test tenant-specific customization
```

**Phase 3: Onboard First Tenants (2-3 weeks)**
```
1. Onboard pilot tenants (3-5 tenants)
   ├─ Create tenant accounts
   ├─ Configure tenant-specific policies
   └─ Train tenant users

2. Monitor and optimize
   ├─ Monitor tenant usage patterns
   ├─ Optimize resource allocation
   └─ Tune rate limits and quotas

3. Iterate based on feedback
   ├─ Add requested features
   ├─ Fix tenant-specific issues
   └─ Improve onboarding experience
```

#### 7. Common Pitfalls and Key Takeaways

**Pitfalls**:
- ❌ Forgetting tenant_id in queries (data leakage)
- ❌ No tenant validation (unauthorized access)
- ❌ Shared rate limits (noisy neighbor problem)
- ❌ No cost attribution (billing issues)

**Key Takeaways**:
- Bridge model: Silo for enterprise, pool for SMB
- Tenant-aware partition keys in DynamoDB
- JWT-based authentication with tenant_id
- Feature flags and tiering for customization
- Usage tracking for accurate billing
- Phased migration: Add context → Implement isolation → Onboard tenants

---

## Question 6: Evolution: Single-Region to Multi-Region Deployment

### Problem Statement

"Our returns platform currently runs in a single AWS region (us-west-2). We want to expand globally to serve customers in Europe and Asia with low latency and high availability. How would you design a multi-region architecture? What are the tradeoffs between active-active and active-passive? How would you handle data replication, consistency, and disaster recovery?"

### Context
- Current: Single region (us-west-2), 99.5% availability
- Target: Multi-region (us-west-2, eu-west-1, ap-southeast-1), 99.9% availability
- Requirements: <500ms latency globally, GDPR compliance (EU data in EU)
- Scale: 10K-50K requests/day globally

### Strong Answer Outline

#### 1. Multi-Region Deployment Models

**Active-Passive vs. Active-Active Comparison**:
```
┌─────────────────────────────────────────────────────────────┐
│  Active-Passive (Disaster Recovery)                         │
│  ├─ Primary: us-west-2 (100% traffic)                       │
│  ├─ Secondary: eu-west-1 (standby, 0% traffic)              │
│  ├─ Failover: Manual or automatic (5-15 minutes)            │
│  ├─ Data: Async replication (RPO: minutes, RTO: 15 min)     │
│  ├─ Cost: Lower (standby resources minimal)                 │
│  └─ Use Case: DR only, not for latency optimization         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Active-Active (Global Load Balancing)                      │
│  ├─ Primary: us-west-2 (US traffic)                         │
│  ├─ Secondary: eu-west-1 (EU traffic)                       │
│  ├─ Tertiary: ap-southeast-1 (Asia traffic)                 │
│  ├─ Routing: Latency-based or geolocation-based             │
│  ├─ Data: Bi-directional replication (RPO: seconds)         │
│  ├─ Cost: Higher (all regions fully provisioned)            │
│  └─ Use Case: Global scale, low latency (RECOMMENDED)       │
└─────────────────────────────────────────────────────────────┘
```

**Recommended: Active-Active with Regional Affinity**:
```
┌─────────────────────────────────────────────────────────────┐
│  Global Edge Layer                                          │
│  ├─ AWS Global Accelerator (Anycast IP)                     │
│  ├─ CloudFront (Static assets, API caching)                 │
│  └─ Route 53 (Latency-based routing)                        │
└─────────────────────────────────────────────────────────────┘
                          │
            ┌─────────────┼─────────────┐
            │             │             │
┌───────────▼──────┐ ┌────▼────────┐ ┌─▼──────────────┐
│  us-west-2       │ │  eu-west-1  │ │  ap-southeast-1│
│  (Americas)      │ │  (Europe)   │ │  (Asia)        │
│                  │ │             │ │                │
│  Full Stack:     │ │  Full Stack:│ │  Full Stack:   │
│  ├─ API Gateway  │ │  ├─ API GW  │ │  ├─ API GW     │
│  ├─ Runtime      │ │  ├─ Runtime │ │  ├─ Runtime    │
│  ├─ DynamoDB     │ │  ├─ DynamoDB│ │  ├─ DynamoDB   │
│  │   Global Tbl │ │  │   Global  │ │  │   Global    │
│  └─ S3 (CRR)    │ │  └─ S3 (CRR)│ │  └─ S3 (CRR)   │
└──────────────────┘ └─────────────┘ └────────────────┘
         │                  │                │
         └──────────────────┴────────────────┘
                     │
              Bi-directional
              Replication
```

#### 2. Data Replication Strategy

**DynamoDB Global Tables**:
```python
class GlobalTableManager:
    """
    Manage DynamoDB Global Tables for multi-region replication.
    """
    def create_global_table(self, table_name, regions):
        """
        Create DynamoDB Global Table across regions.
        """
        # Create table in primary region
        primary_region = regions[0]
        dynamodb_primary = boto3.client('dynamodb', region_name=primary_region)
        
        dynamodb_primary.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'tenant_id#decision_id', 'KeyType': 'HASH'},
                {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'tenant_id#decision_id', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp', 'AttributeType': 'N'}
            ],
            BillingMode='PAY_PER_REQUEST',
            StreamSpecification={
                'StreamEnabled': True,
                'StreamViewType': 'NEW_AND_OLD_IMAGES'
            }
        )
        
        # Wait for table to be active
        waiter = dynamodb_primary.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        
        # Create global table
        dynamodb_primary.create_global_table(
            GlobalTableName=table_name,
            ReplicationGroup=[
                {'RegionName': region} for region in regions
            ]
        )
        
        return {
            'table_name': table_name,
            'regions': regions,
            'replication_latency': 'typically < 1 second'
        }
    
    def monitor_replication_lag(self, table_name, regions):
        """
        Monitor replication lag between regions.
        """
        lags = {}
        
        for region in regions:
            dynamodb = boto3.client('dynamodb', region_name=region)
            
            # Get table description
            response = dynamodb.describe_table(TableName=table_name)
            
            # Check replication status
            for replica in response['Table'].get('Replicas', []):
                replica_region = replica['RegionName']
                replica_status = replica['ReplicaStatus']
                
                if replica_status != 'ACTIVE':
                    lags[replica_region] = 'UNHEALTHY'
                else:
                    # Estimate lag by comparing stream positions
                    lag_seconds = self.estimate_replication_lag(table_name, region, replica_region)
                    lags[replica_region] = lag_seconds
        
        return lags
```

**S3 Cross-Region Replication**:
```python
def setup_s3_replication(source_bucket, source_region, dest_buckets):
    """
    Configure S3 Cross-Region Replication.
    """
    s3_source = boto3.client('s3', region_name=source_region)
    
    # Enable versioning (required for CRR)
    s3_source.put_bucket_versioning(
        Bucket=source_bucket,
        VersioningConfiguration={'Status': 'Enabled'}
    )
    
    # Create replication configuration
    replication_rules = []
    for i, dest_bucket in enumerate(dest_buckets):
        replication_rules.append({
            'ID': f'replication-rule-{i}',
            'Priority': i,
            'Filter': {'Prefix': ''},
            'Status': 'Enabled',
            'Destination': {
                'Bucket': f'arn:aws:s3:::{dest_bucket}',
                'ReplicationTime': {
                    'Status': 'Enabled',
                    'Time': {'Minutes': 15}  # S3 RTC: 99.99% within 15 min
                },
                'Metrics': {
                    'Status': 'Enabled',
                    'EventThreshold': {'Minutes': 15}
                }
            },
            'DeleteMarkerReplication': {'Status': 'Enabled'}
        })
    
    s3_source.put_bucket_replication(
        Bucket=source_bucket,
        ReplicationConfiguration={
            'Role': 'arn:aws:iam::123456789012:role/s3-replication-role',
            'Rules': replication_rules
        }
    )
```


#### 3. Consistency and Conflict Resolution

**Eventual Consistency Model**:
```python
class ConflictResolver:
    """
    Handle conflicts in multi-region writes.
    """
    def resolve_conflict(self, item_v1, item_v2):
        """
        Resolve conflicts using Last-Write-Wins (LWW) strategy.
        """
        # Compare timestamps
        timestamp_v1 = item_v1['timestamp']
        timestamp_v2 = item_v2['timestamp']
        
        if timestamp_v1 > timestamp_v2:
            return item_v1
        elif timestamp_v2 > timestamp_v1:
            return item_v2
        else:
            # Same timestamp - use decision_id as tiebreaker
            if item_v1['decision_id'] > item_v2['decision_id']:
                return item_v1
            else:
                return item_v2
    
    def handle_write_conflict(self, tenant_id, decision_id):
        """
        Handle scenario where same decision is written in multiple regions.
        """
        # Query all regions for the decision
        decisions = []
        for region in ['us-west-2', 'eu-west-1', 'ap-southeast-1']:
            dynamodb = boto3.client('dynamodb', region_name=region)
            response = dynamodb.get_item(
                TableName='decision_log',
                Key={
                    'tenant_id#decision_id': f'{tenant_id}#{decision_id}',
                    'timestamp': {'N': str(int(time.time()))}
                }
            )
            if 'Item' in response:
                decisions.append(response['Item'])
        
        # Resolve conflict
        if len(decisions) > 1:
            winner = self.resolve_conflict(decisions[0], decisions[1])
            
            # Write winner to all regions
            for region in ['us-west-2', 'eu-west-1', 'ap-southeast-1']:
                dynamodb = boto3.client('dynamodb', region_name=region)
                dynamodb.put_item(
                    TableName='decision_log',
                    Item=winner
                )
```

**Regional Affinity for Writes**:
```python
def route_write_to_home_region(tenant_id):
    """
    Route writes to tenant's home region to minimize conflicts.
    """
    # Get tenant metadata
    tenant = get_tenant_metadata(tenant_id)
    home_region = tenant.get('home_region', 'us-west-2')
    
    # Route write to home region
    dynamodb = boto3.client('dynamodb', region_name=home_region)
    
    return dynamodb

# Usage
dynamodb = route_write_to_home_region('tenant_001')
dynamodb.put_item(
    TableName='decision_log',
    Item={
        'tenant_id#decision_id': 'tenant_001#decision_123',
        'timestamp': int(time.time()),
        'decision': 'approved',
        'home_region': 'us-west-2'  # Track origin
    }
)
```

#### 4. GDPR Compliance and Data Residency

**Regional Data Isolation**:
```python
class DataResidencyManager:
    """
    Ensure GDPR compliance with regional data isolation.
    """
    REGION_MAPPING = {
        'EU': ['eu-west-1', 'eu-central-1'],
        'US': ['us-west-2', 'us-east-1'],
        'ASIA': ['ap-southeast-1', 'ap-northeast-1']
    }
    
    def get_allowed_regions(self, tenant_id):
        """
        Get allowed regions for tenant based on data residency requirements.
        """
        tenant = get_tenant_metadata(tenant_id)
        data_residency = tenant.get('data_residency', 'US')
        
        return self.REGION_MAPPING.get(data_residency, ['us-west-2'])
    
    def enforce_data_residency(self, tenant_id, target_region):
        """
        Enforce data residency rules before writing.
        """
        allowed_regions = self.get_allowed_regions(tenant_id)
        
        if target_region not in allowed_regions:
            raise DataResidencyViolation(
                f"Tenant {tenant_id} data cannot be stored in {target_region}. "
                f"Allowed regions: {allowed_regions}"
            )
    
    def setup_regional_replication(self, tenant_id):
        """
        Configure replication only within allowed regions.
        """
        allowed_regions = self.get_allowed_regions(tenant_id)
        
        # Create DynamoDB table with regional replication
        if len(allowed_regions) > 1:
            create_global_table(
                table_name=f'decision_log_{tenant_id}',
                regions=allowed_regions
            )
        else:
            # Single region only (strict GDPR)
            create_table(
                table_name=f'decision_log_{tenant_id}',
                region=allowed_regions[0]
            )
```

#### 5. Disaster Recovery and Failover

**Automated Failover Strategy**:
```python
class FailoverManager:
    """
    Manage automated failover between regions.
    """
    def __init__(self):
        self.health_check_interval = 60  # seconds
        self.failover_threshold = 3  # consecutive failures
    
    def monitor_regional_health(self):
        """
        Monitor health of each region.
        """
        health_status = {}
        
        for region in ['us-west-2', 'eu-west-1', 'ap-southeast-1']:
            # Check API Gateway health
            api_health = self.check_api_health(region)
            
            # Check DynamoDB health
            dynamodb_health = self.check_dynamodb_health(region)
            
            # Check AgentCore Runtime health
            runtime_health = self.check_runtime_health(region)
            
            # Overall health
            health_status[region] = {
                'api': api_health,
                'dynamodb': dynamodb_health,
                'runtime': runtime_health,
                'overall': all([api_health, dynamodb_health, runtime_health])
            }
        
        return health_status
    
    def trigger_failover(self, failed_region, target_region):
        """
        Trigger failover from failed region to target region.
        """
        logger.critical(f"Initiating failover from {failed_region} to {target_region}")
        
        # Update Route 53 health checks
        route53 = boto3.client('route53')
        route53.change_resource_record_sets(
            HostedZoneId='Z1234567890ABC',
            ChangeBatch={
                'Changes': [{
                    'Action': 'UPSERT',
                    'ResourceRecordSet': {
                        'Name': 'api.returns-platform.com',
                        'Type': 'A',
                        'SetIdentifier': failed_region,
                        'Failover': 'PRIMARY',
                        'HealthCheckId': 'health-check-id',
                        'AliasTarget': {
                            'HostedZoneId': 'Z1234567890ABC',
                            'DNSName': f'api-{target_region}.returns-platform.com',
                            'EvaluateTargetHealth': True
                        }
                    }
                }]
            }
        )
        
        # Notify operations team
        sns = boto3.client('sns')
        sns.publish(
            TopicArn='arn:aws:sns:us-west-2:123456789012:critical-alerts',
            Subject=f'CRITICAL: Failover from {failed_region} to {target_region}',
            Message=f'Automated failover initiated at {datetime.now().isoformat()}'
        )
        
        # Log failover event
        logger.info(f"Failover completed: {failed_region} -> {target_region}")
```

**Recovery Time Objective (RTO) and Recovery Point Objective (RPO)**:
```
┌─────────────────────────────────────────────────────────────┐
│  Disaster Recovery Metrics                                  │
├─────────────────────────────────────────────────────────────┤
│  RTO (Recovery Time Objective)                              │
│  ├─ Automated failover: 2-5 minutes                         │
│  ├─ Manual failover: 15-30 minutes                          │
│  └─ Full region rebuild: 2-4 hours                          │
│                                                              │
│  RPO (Recovery Point Objective)                             │
│  ├─ DynamoDB Global Tables: < 1 second                      │
│  ├─ S3 Cross-Region Replication: < 15 minutes               │
│  └─ CloudWatch Logs: < 5 minutes (via Kinesis)              │
└─────────────────────────────────────────────────────────────┘
```


#### 6. Cost Analysis and Optimization

**Multi-Region Cost Breakdown**:
```
┌─────────────────────────────────────────────────────────────┐
│  Monthly Cost Estimate (Active-Active, 3 Regions)          │
├─────────────────────────────────────────────────────────────┤
│  Compute (AgentCore Runtime)                                │
│  ├─ 3 regions × $5,000/region = $15,000                     │
│  └─ Auto-scaling: +20% buffer = $18,000                     │
│                                                              │
│  Data Storage (DynamoDB Global Tables)                      │
│  ├─ Storage: 100GB × 3 regions × $0.25/GB = $75             │
│  ├─ Writes: 10M writes × 3 regions × $1.25/M = $37.50       │
│  ├─ Reads: 30M reads × 3 regions × $0.25/M = $22.50         │
│  ├─ Replication: 10M writes × 2 replicas × $1.875/M = $37.50│
│  └─ Total DynamoDB: $172.50                                 │
│                                                              │
│  Data Transfer                                               │
│  ├─ Cross-region replication: 50GB × $0.02/GB = $1,000      │
│  ├─ CloudFront: 500GB × $0.085/GB = $42.50                  │
│  └─ Total Transfer: $1,042.50                               │
│                                                              │
│  Networking (Global Accelerator)                            │
│  ├─ Fixed fee: $0.025/hour × 730 hours = $18.25             │
│  ├─ Data transfer: 500GB × $0.015/GB = $7.50                │
│  └─ Total Networking: $25.75                                │
│                                                              │
│  Monitoring & Logging                                        │
│  ├─ CloudWatch Logs: 100GB × 3 regions × $0.50/GB = $150    │
│  ├─ X-Ray: 10M traces × $5/M = $50                          │
│  └─ Total Monitoring: $200                                  │
│                                                              │
│  TOTAL MONTHLY COST: ~$19,440                               │
│  (vs. Single Region: ~$6,500)                               │
│  Cost Increase: 3x for 3 regions                            │
└─────────────────────────────────────────────────────────────┘
```

**Cost Optimization Strategies**:
```python
def optimize_multi_region_costs():
    """
    Strategies to reduce multi-region costs.
    """
    optimizations = {
        '1. Regional Routing': {
            'description': 'Route traffic to nearest region to minimize cross-region data transfer',
            'savings': '30-40% on data transfer costs',
            'implementation': 'Use Route 53 latency-based routing + CloudFront'
        },
        
        '2. Selective Replication': {
            'description': 'Replicate only critical data (decisions, policies), not all data',
            'savings': '20-30% on storage and replication costs',
            'implementation': 'Use S3 replication filters, DynamoDB streams with Lambda'
        },
        
        '3. Reserved Capacity': {
            'description': 'Purchase reserved capacity for predictable workloads',
            'savings': '30-50% on compute costs',
            'implementation': 'Savings Plans for Lambda, Reserved Concurrency for AgentCore'
        },
        
        '4. Tiered Storage': {
            'description': 'Move old data to cheaper storage tiers',
            'savings': '50-70% on long-term storage',
            'implementation': 'S3 Intelligent-Tiering, DynamoDB TTL for old records'
        },
        
        '5. Compression': {
            'description': 'Compress data before replication',
            'savings': '40-60% on data transfer',
            'implementation': 'Gzip compression for S3 objects, DynamoDB attribute compression'
        }
    }
    
    return optimizations
```

#### 7. Migration Strategy from Single to Multi-Region

**Phase 1: Setup Secondary Regions (2-3 weeks)**
```
1. Deploy infrastructure in secondary regions
   ├─ Create DynamoDB Global Tables
   ├─ Setup S3 Cross-Region Replication
   ├─ Deploy AgentCore Runtime in eu-west-1, ap-southeast-1
   └─ Configure API Gateway in all regions

2. Enable data replication
   ├─ Enable DynamoDB Streams
   ├─ Configure Global Table replication
   ├─ Setup S3 CRR
   └─ Verify replication lag < 1 second

3. Testing
   ├─ Test read/write in all regions
   ├─ Test replication consistency
   └─ Test failover scenarios
```

**Phase 2: Enable Global Routing (1-2 weeks)**
```
1. Configure Global Accelerator
   ├─ Create accelerator with static IPs
   ├─ Add endpoints for all regions
   └─ Configure health checks

2. Update DNS
   ├─ Point domain to Global Accelerator
   ├─ Configure Route 53 latency-based routing
   └─ Test routing from different locations

3. Gradual rollout
   ├─ Route 10% traffic to secondary regions
   ├─ Monitor latency and error rates
   ├─ Increase to 50%, then 100%
   └─ Rollback plan if issues detected
```

**Phase 3: Optimize and Monitor (Ongoing)**
```
1. Monitor regional performance
   ├─ Latency by region
   ├─ Error rates by region
   └─ Replication lag

2. Optimize costs
   ├─ Analyze data transfer patterns
   ├─ Implement selective replication
   └─ Purchase reserved capacity

3. Disaster recovery drills
   ├─ Monthly failover tests
   ├─ Quarterly full region failure simulation
   └─ Update runbooks based on learnings
```

#### 8. Common Pitfalls and Key Takeaways

**Pitfalls**:
- ❌ Ignoring data residency requirements (GDPR violations)
- ❌ No conflict resolution strategy (data inconsistency)
- ❌ Underestimating cross-region data transfer costs (3x cost increase)
- ❌ No automated failover (long RTO during outages)

**Key Takeaways**:
- Active-active with regional affinity for global scale and low latency
- DynamoDB Global Tables for < 1 second replication
- Regional data isolation for GDPR compliance
- Last-Write-Wins conflict resolution with regional affinity
- Automated failover with Route 53 health checks
- Cost optimization: Regional routing, selective replication, reserved capacity
- Phased migration: Setup regions → Enable routing → Optimize

---

## Summary

This document provides interview preparation for senior/staff engineer candidates working on the V2 returns and refunds platform (future enhancements). The questions cover:

1. **Safety Monitoring**: Using CloudWatch logs, X-Ray traces, and Runtime metrics for security and performance
2. **Multi-Tenant Evolution**: Designing tenant isolation, authentication, and billing for 100-500 merchants
3. **Multi-Region Deployment**: Active-active architecture with data replication and disaster recovery

Each question includes:
- Realistic problem statement with context
- Detailed answer outline from senior/staff engineer perspective
- Code examples and architectural diagrams
- Quantitative tradeoff analysis
- Common pitfalls to avoid
- Key takeaways

**Document Version**: 2.0.0  
**Last Updated**: 2026-03-22  
**Status**: Complete (3/3 questions - V2 Future Enhancements)


