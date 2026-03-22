# Implementation Plan: Policy Layer, Decision Logging & Observability

**Branch**: `spec-driven-v1`  
**Time Budget**: 4-5 hours  
**Date**: 2026-03-22

## Overview

This plan adds three key capabilities to the current returns/refunds agent:
1. **Configurable Policy Layer**: JSON/YAML policies for return eligibility and refund calculation
2. **Decision Logging**: Structured logging with queryable IDs (who/what/why)
3. **Basic Observability**: Metrics dashboard for approved/denied/escalated decisions

## Prerequisites

- Current AWS services available: DynamoDB, S3, CloudWatch, Lambda, AgentCore Runtime
- Python environment with existing dependencies
- Access to current agent code in `src/agents/`

## Task List (Dependency Order)

### Phase 1: Policy Layer Foundation (90 minutes)

#### Task 1.1: Create Policy Schema & Sample Policies (30 min)
**Dependencies**: None  
**Deliverables**:
- `policies/schema.json` - JSON schema for policy validation
- `policies/default_policy.yaml` - Default return policy
- `policies/README.md` - Policy documentation

**Actions**:
- Define policy structure (return windows, refund rules, non-returnable categories)
- Create default policy matching current hardcoded rules
- Add validation schema for policy files

**Code Changes**: See `patches/001-policy-schema.patch`

---

#### Task 1.2: Implement Policy Loader Module (30 min)
**Dependencies**: Task 1.1  
**Deliverables**:
- `src/agents/policy_engine.py` - Policy loading and evaluation logic
- Unit tests in `src/tests/test_policy_engine.py`

**Actions**:
- Create `PolicyEngine` class to load YAML/JSON policies
- Implement policy validation against schema
- Add caching for loaded policies
- Replace hardcoded rules in tools with policy engine calls

**Code Changes**: See `patches/002-policy-engine.patch`

---

#### Task 1.3: Integrate Policy Engine into Agent Tools (30 min)
**Dependencies**: Task 1.2  
**Deliverables**:
- Updated `src/agents/17_runtime_agent.py`
- Updated `src/agents/01_returns_refunds_agent.py`

**Actions**:
- Modify `check_return_eligibility` to use policy engine
- Modify `calculate_refund_amount` to use policy engine
- Add environment variable `POLICY_FILE` for policy path
- Test with default policy

**Code Changes**: See `patches/003-integrate-policy-engine.patch`

---

### Phase 2: Decision Logging (90 minutes)

#### Task 2.1: Create Decision Log Schema (20 min)
**Dependencies**: None  
**Deliverables**:
- `src/agents/decision_logger.py` - Decision logging module
- DynamoDB table schema in `infrastructure/decision_log_table.json`

**Actions**:
- Define decision log structure (decision_id, timestamp, actor_id, decision_type, inputs, outputs, policy_version, reason)
- Create DynamoDB table schema for decision logs
- Add helper functions for generating decision IDs

---

#### Task 2.2: Implement Decision Logger (30 min)
**Dependencies**: Task 2.1  
**Deliverables**:
- Complete `DecisionLogger` class
- Integration with DynamoDB or S3 (based on available services)

**Actions**:
- Implement `log_decision()` method
- Add structured logging to CloudWatch
- Store decisions in DynamoDB table (or S3 if DynamoDB unavailable)
- Include correlation IDs for tracing

**Note**: If DynamoDB table creation requires additional permissions, fall back to S3 with JSON Lines format.

---

#### Task 2.3: Integrate Decision Logging into Tools (40 min)
**Dependencies**: Task 2.2, Task 1.3  
**Deliverables**:
- Updated agent tools with decision logging
- Test script to verify logging

**Actions**:
- Add decision logging to `check_return_eligibility`
- Add decision logging to `calculate_refund_amount`
- Log policy version used for each decision
- Add correlation ID to track related decisions
- Test end-to-end logging flow

---

### Phase 3: Basic Observability (90 minutes)

#### Task 3.1: Create Metrics Collection Module (30 min)
**Dependencies**: Task 2.2  
**Deliverables**:
- `src/agents/metrics.py` - Metrics collection and aggregation
- CloudWatch custom metrics configuration

**Actions**:
- Implement metrics collection for decision types (approved, denied, escalated)
- Add CloudWatch custom metrics publishing
- Create helper functions for metric aggregation
- Add error rate and latency metrics

---

#### Task 3.2: Build Simple Metrics Dashboard Script (30 min)
**Dependencies**: Task 3.1  
**Deliverables**:
- `src/ui/metrics_dashboard.py` - CLI dashboard for metrics
- Query script for decision logs

**Actions**:
- Create CLI script to query CloudWatch metrics
- Display counts: approved, denied, escalated (last 24h, 7d, 30d)
- Show approval rate percentage
- Add simple ASCII charts for visualization
- Query decision logs by date range

---

#### Task 3.3: Add Observability to Streamlit UI (30 min)
**Dependencies**: Task 3.2  
**Deliverables**:
- Updated `src/ui/streamlit_app.py` with metrics tab

**Actions**:
- Add "Metrics" tab to Streamlit UI
- Display real-time decision counts
- Show recent decisions table
- Add refresh button for live updates
- Include policy version in use

---

### Phase 4: Testing & Documentation (60 minutes)

#### Task 4.1: Integration Testing (30 min)
**Dependencies**: All previous tasks  
**Deliverables**:
- `src/tests/test_integration.py` - End-to-end tests
- Test results documentation

**Actions**:
- Test policy loading and validation
- Test decision logging for various scenarios
- Test metrics collection and querying
- Verify all components work together
- Document any issues found

---

#### Task 4.2: Update Documentation (30 min)
**Dependencies**: Task 4.1  
**Deliverables**:
- Updated `README.md`
- `docs/POLICY_GUIDE.md` - Policy configuration guide
- `docs/OBSERVABILITY.md` - Metrics and logging guide

**Actions**:
- Document new policy configuration
- Explain decision logging structure
- Provide examples of querying logs
- Add troubleshooting section
- Update architecture diagram

---

## Service Availability & Alternatives

### Available Services (Confirmed)
- ✅ **DynamoDB**: For decision log storage
- ✅ **S3**: For policy files and backup logs
- ✅ **CloudWatch Logs**: For structured logging
- ✅ **CloudWatch Metrics**: For custom metrics
- ✅ **Lambda**: For background processing (if needed)
- ✅ **AgentCore Runtime**: Current deployment platform

### Service Alternatives (If Access Issues)

#### If DynamoDB Table Creation Fails:
**Alternative**: Use S3 with JSON Lines format
- Store decisions in `s3://bucket/decisions/YYYY/MM/DD/HH/decision-{uuid}.json`
- Query using S3 Select or Athena
- Pros: No table management, unlimited storage
- Cons: Slower queries, no real-time indexing

**Implementation**:
```python
# Fallback to S3 if DynamoDB unavailable
def log_decision_to_s3(decision_data):
    s3_key = f"decisions/{datetime.now().strftime('%Y/%m/%d/%H')}/decision-{uuid.uuid4()}.json"
    s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=json.dumps(decision_data))
```

#### If CloudWatch Custom Metrics Unavailable:
**Alternative**: Use CloudWatch Logs with metric filters
- Log metrics as structured JSON to CloudWatch Logs
- Create metric filters to extract counts
- Pros: No additional service needed
- Cons: Less flexible, delayed metrics

**Implementation**:
```python
# Log metrics as structured JSON
logger.info(json.dumps({
    "metric_type": "decision",
    "decision_type": "approved",
    "timestamp": datetime.now().isoformat()
}))
```

#### If S3 Bucket Creation Fails:
**Alternative**: Use local file system with periodic sync
- Store policies in `policies/` directory
- Store logs in `logs/` directory
- Sync to S3 manually or via cron
- Pros: Works offline, simple
- Cons: Not production-ready, no redundancy

---

## Success Criteria

### Phase 1 (Policy Layer)
- [ ] Policies loaded from YAML/JSON files
- [ ] Policy validation working
- [ ] Agent uses policies instead of hardcoded rules
- [ ] Can switch policies without code changes

### Phase 2 (Decision Logging)
- [ ] All decisions logged with unique IDs
- [ ] Logs include who, what, why, when
- [ ] Logs queryable by date range
- [ ] Policy version tracked per decision

### Phase 3 (Observability)
- [ ] Metrics dashboard shows decision counts
- [ ] Approval rate calculated correctly
- [ ] Streamlit UI displays metrics
- [ ] Metrics update in near real-time (<5 min delay)

### Phase 4 (Testing & Docs)
- [ ] All integration tests pass
- [ ] Documentation complete and accurate
- [ ] Examples provided for common tasks
- [ ] Troubleshooting guide available

---

## Rollback Plan

If any phase fails:
1. **Policy Layer**: Revert to hardcoded rules (original code)
2. **Decision Logging**: Disable logging, agent continues to work
3. **Observability**: Remove metrics collection, core functionality unaffected

All changes are additive and can be disabled via environment variables:
- `ENABLE_POLICY_ENGINE=false` - Use hardcoded rules
- `ENABLE_DECISION_LOGGING=false` - Skip logging
- `ENABLE_METRICS=false` - Skip metrics collection

---

## Next Steps After Completion

1. Deploy updated agent to AgentCore Runtime
2. Monitor decision logs for 24 hours
3. Review metrics dashboard for insights
4. Create additional policies for different merchant scenarios
5. Add policy versioning and A/B testing capability

---

## Quick Start

See `QUICK-START.md` for a streamlined 4-hour implementation guide with timeline and troubleshooting.

## Code Patches

See `patches/` directory for concrete code changes:
- `001-policy-schema.patch` - Policy schema and sample files
- `002-policy-engine.patch` - Policy engine implementation
- `003-integrate-policy-engine.patch` - Agent integration
- `004-decision-logging.patch` - Decision logging infrastructure

Each patch includes detailed comments and can be applied via `git apply` or reviewed manually.

---

## Notes

- All code changes are backward compatible
- Environment variables provide feature flags
- Existing tests continue to pass
- No breaking changes to agent API
- Can be deployed incrementally (phase by phase)

## Files Created

This implementation plan creates the following deliverables:

**Documentation**:
- `PLAN-implementation.md` - This file (implementation plan)
- `QUICK-START.md` - 4-hour quick start guide
- `patches/README.md` - Patch application guide

**Code Patches**:
- `patches/001-policy-schema.patch` - Policy foundation
- `patches/002-policy-engine.patch` - Policy engine
- `patches/003-integrate-policy-engine.patch` - Agent integration
- `patches/004-decision-logging.patch` - Decision logging

**Total**: 7 files ready for your review and implementation

