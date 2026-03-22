# Implementation Plan: V2 Enhancements (Human Approval Workflow + Dashboard)

**Branch**: `spec-driven-v2`  
**Time Budget**: 1-2 weeks  
**Date**: 2026-03-22  
**Builds On**: V1 Implementation (Policy Engine + Decision Logging)

## Overview

This plan adds V2 capabilities to the returns/refunds agent:
1. **Human Approval Workflow**: Risk-based routing with manual approval queue
2. **Streamlit Dashboard**: Monitoring, approvals, and analytics
3. **Enhanced Decision Logging**: DynamoDB-based with queryable history
4. **Policy Versioning**: Track policy changes and audit trail

## Prerequisites

- V1 implementation complete (policy engine, decision logging, observability)
- AWS services available: DynamoDB, S3, CloudWatch, Lambda, AgentCore Runtime
- Python environment with existing dependencies
- Streamlit for dashboard UI

## Task List (Dependency Order)

### Phase 1: Approval Queue Infrastructure (2-3 days)

#### Task 1.1: Create Approval Queue DynamoDB Table (1 hour)
**Dependencies**: None  
**Deliverables**:
- `infrastructure/create_approval_queue_table.py` - Table creation script
- DynamoDB table: `returns-approval-queue`

**Table Structure**:
```yaml
table_name: returns-approval-queue
partition_key: status (String) # pending, approved, denied
sort_key: created_at (Number) # timestamp
attributes:
  - approval_id: UUID
  - return_id: UUID
  - customer_id: string
  - order_id: string
  - refund_amount: decimal
  - risk_score: integer (0-100)
  - reason: string
  - created_at: timestamp
  - sla_deadline: timestamp
  - status: pending/approved/denied/expired
  - approved_by: user_id (optional)
  - approved_at: timestamp (optional)
  - denial_reason: string (optional)
gsi:
  - approval_id-index (for lookups)
  - sla_deadline-index (for SLA monitoring)
ttl: 30 days
```

---

#### Task 1.2: Implement Approval Queue Module (4 hours)
**Dependencies**: Task 1.1  
**Deliverables**:
- `src/agents/approval_queue.py` - Queue management logic
- Unit tests in `tests/test_approval_queue.py`

**Functions**:
- `add_to_queue(return_data)` - Add approval request
- `get_pending_approvals()` - List pending items
- `approve_request(approval_id, user_id)` - Approve and process
- `deny_request(approval_id, user_id, reason)` - Deny with reason
- `check_sla_breaches()` - Identify expired items
- `get_approval_status(approval_id)` - Query status

---

#### Task 1.3: Implement Risk Scoring (3 hours)
**Dependencies**: Task 1.2  
**Deliverables**:
- `src/agents/risk_scorer.py` - Risk scoring logic
- Unit tests in `tests/test_risk_scorer.py`

**Risk Thresholds**:
- Auto-approve: `refund_amount < $100 AND days_since_purchase < 30`
- Manual review: `refund_amount >= $100 OR days_since_purchase >= 30`
- Critical review: `refund_amount >= $500` (manager approval)

**Risk Factors**:
- Refund amount (0-40 points)
- Days since purchase (0-20 points)
- Customer return history (0-20 points)
- Item condition (0-10 points)
- Category risk (0-10 points)

---

### Phase 2: Agent Integration (1-2 days)

#### Task 2.1: Add Approval Tools to Agent (3 hours)
**Dependencies**: Phase 1  
**Deliverables**:
- Updated `src/agents/17_runtime_agent.py`
- New tools: `request_approval`, `check_approval_status`

**New Tools**:
```python
@tool
def request_approval(return_data: dict) -> dict:
    """Request human approval for high-risk refund"""
    
@tool
def check_approval_status(approval_id: str) -> dict:
    """Check status of approval request"""
    
@tool
def get_decision_history(customer_id: str = None, limit: int = 10) -> list:
    """Retrieve past decisions for context"""
```

---

#### Task 2.2: Update Agent System Prompt (1 hour)
**Dependencies**: Task 2.1  
**Deliverables**:
- Updated system prompt in `17_runtime_agent.py`

**Prompt Updates**:
- Mention approval workflow for high-risk refunds
- Explain when to use `request_approval` tool
- Guide on checking approval status
- Instructions for customer communication during approval

---

#### Task 2.3: Integration Testing (2 hours)
**Dependencies**: Task 2.2  
**Deliverables**:
- `tests/test_approval_integration.py`
- Test scenarios: auto-approve, manual review, denial

---

### Phase 3: Streamlit Dashboard (3-4 days)

#### Task 3.1: Dashboard Foundation (2 hours)
**Dependencies**: None  
**Deliverables**:
- `src/ui/dashboard_app.py` - Main Streamlit app
- `src/ui/pages/` - Page modules
- `.streamlit/config.toml` - Streamlit configuration
- `.streamlit/secrets.toml.template` - Auth template

**Dashboard Structure**:
```
src/ui/
├── dashboard_app.py (main app with navigation)
├── pages/
│   ├── home.py (overview metrics)
│   ├── approvals.py (approval queue)
│   ├── analytics.py (charts)
│   ├── decisions.py (decision log)
│   └── policies.py (policy viewer)
└── utils/
    ├── auth.py (authentication)
    ├── db.py (DynamoDB queries)
    └── charts.py (plotting helpers)
```

---

#### Task 3.2: Home Page - Overview Metrics (3 hours)
**Dependencies**: Task 3.1  
**Deliverables**:
- `src/ui/pages/home.py`

**Metrics**:
- Total returns (today/week/month)
- Auto-approval rate (%)
- Manual approval rate (%)
- Average refund amount ($)
- Pending approvals count
- SLA breach count

**Recent Activity**:
- Last 10 decisions (table)
- Last 5 approvals (table)
- Last 5 denials (table)

---

#### Task 3.3: Approvals Page - Queue Management (4 hours)
**Dependencies**: Task 3.1, Phase 2  
**Deliverables**:
- `src/ui/pages/approvals.py`

**Features**:
- List pending approvals (sorted by SLA deadline)
- View return details (customer, order, amount, risk)
- Approve button (with confirmation)
- Deny button (with reason input)
- SLA countdown timer (visual indicator)
- Risk score visualization (gauge chart)
- Filter by risk level
- Search by customer/order ID

**Actions**:
- Approve: Update DynamoDB, log decision, show success
- Deny: Prompt for reason, update DynamoDB, log decision
- Refresh: Reload pending approvals

---

#### Task 3.4: Analytics Page - Charts and Metrics (3 hours)
**Dependencies**: Task 3.1  
**Deliverables**:
- `src/ui/pages/analytics.py`

**Charts**:
- Returns over time (line chart)
- Approval rate by decision type (pie chart)
- Refund amounts distribution (histogram)
- Risk score distribution (bar chart)
- Top customers by return count (table)

**Filters**:
- Date range picker
- Decision type filter
- Risk level filter

---

#### Task 3.5: Decisions Page - Searchable Log (2 hours)
**Dependencies**: Task 3.1  
**Deliverables**:
- `src/ui/pages/decisions.py`

**Features**:
- Searchable decision log (by customer, order, date)
- Filterable by decision type, risk score
- Sortable columns
- Export to CSV
- View decision details (modal)
- Policy version used

---

#### Task 3.6: Policies Page - Policy Viewer (2 hours)
**Dependencies**: Task 3.1  
**Deliverables**:
- `src/ui/pages/policies.py`

**Features**:
- List available policies
- View policy details (YAML formatted)
- Compare two policies side-by-side
- Policy change history (Git log)
- Active policy indicator

---

#### Task 3.7: Authentication and Authorization (2 hours)
**Dependencies**: Task 3.1  
**Deliverables**:
- `src/ui/utils/auth.py`
- `.streamlit/secrets.toml.template`

**Authentication**:
- Streamlit secrets-based (username/password)
- Session state for login tracking
- Session timeout (30 minutes)

**Roles**:
- `agent`: View metrics, view decisions
- `manager`: All agent permissions + approve/deny requests

**Security**:
- HTTPS only
- Password hashing (bcrypt)
- Audit log for all approval actions

---

### Phase 4: Enhanced Decision Logging (1 day)

#### Task 4.1: Upgrade Decision Log Table (2 hours)
**Dependencies**: None  
**Deliverables**:
- `infrastructure/upgrade_decision_log_table.py`
- Updated table schema with GSIs

**New GSIs**:
- `customer_id-timestamp-index` (customer history)
- `decision_type-timestamp-index` (analytics)
- `decided_by-timestamp-index` (user activity)

---

#### Task 4.2: Enhanced Decision Logger (2 hours)
**Dependencies**: Task 4.1  
**Deliverables**:
- Updated `src/agents/decision_logger.py`
- New query functions

**New Functions**:
- `get_customer_history(customer_id, limit)` - Customer's past decisions
- `get_decisions_by_type(type, start_date, end_date)` - Analytics queries
- `get_user_decisions(user_id)` - Audit trail
- `export_decisions_csv(filters)` - Export for reporting

---

### Phase 5: Policy Versioning (1 day)

#### Task 5.1: Policy Metadata Tracking (2 hours)
**Dependencies**: None  
**Deliverables**:
- `src/agents/policy_versioner.py`
- Policy metadata in DynamoDB

**Metadata**:
- Policy ID, version, effective date
- Git commit hash
- Created by, created at
- Change description

---

#### Task 5.2: Policy Change Audit (2 hours)
**Dependencies**: Task 5.1  
**Deliverables**:
- Policy change tracking in decision log
- Git integration for policy history

**Features**:
- Log policy version with each decision
- Store policy snapshot in decision log
- Track policy changes in Git
- Dashboard shows policy change timeline

---

### Phase 6: Testing and Deployment (2 days)

#### Task 6.1: Integration Testing (4 hours)
**Dependencies**: All previous phases  
**Deliverables**:
- `tests/test_v2_integration.py`
- End-to-end test scenarios

**Test Scenarios**:
- Low-risk return → auto-approve
- High-risk return → manual review → approve
- High-risk return → manual review → deny
- SLA breach detection
- Dashboard approval workflow
- Policy versioning

---

#### Task 6.2: Performance Testing (2 hours)
**Dependencies**: Task 6.1  
**Deliverables**:
- Performance test results
- Latency benchmarks

**Targets**:
- Agent response: <5 seconds
- Dashboard load: <2 seconds
- Approval action: <500ms
- Policy evaluation: <100ms

---

#### Task 6.3: Documentation (3 hours)
**Dependencies**: Task 6.2  
**Deliverables**:
- Updated `README.md`
- `docs/V2_FEATURES.md` - V2 feature guide
- `docs/DASHBOARD_GUIDE.md` - Dashboard user guide
- `docs/APPROVAL_WORKFLOW.md` - Approval workflow guide

---

#### Task 6.4: Deployment (3 hours)
**Dependencies**: Task 6.3  
**Deliverables**:
- Deployed agent to AgentCore Runtime
- Deployed dashboard to Streamlit Cloud or EC2
- Deployment verification

**Deployment Steps**:
1. Create DynamoDB tables
2. Deploy updated agent
3. Deploy dashboard
4. Configure authentication
5. User acceptance testing

---

## Total Timeline

**Optimistic**: 7 days (1 week)  
**Realistic**: 10-12 days (1.5-2 weeks)  
**Pessimistic**: 14 days (2 weeks)

## Dependencies

- V1 implementation complete
- AWS account with DynamoDB access
- Streamlit Cloud account (or EC2 for dashboard)
- Python 3.12 environment

## Success Criteria

### Phase 1 (Approval Queue)
- [ ] DynamoDB table created
- [ ] Queue management functions work
- [ ] Risk scoring accurate
- [ ] SLA tracking functional

### Phase 2 (Agent Integration)
- [ ] Agent can request approvals
- [ ] Agent can check approval status
- [ ] System prompt updated
- [ ] Integration tests pass

### Phase 3 (Dashboard)
- [ ] Dashboard loads without errors
- [ ] All pages functional
- [ ] Approval actions work
- [ ] Charts render correctly
- [ ] Authentication works

### Phase 4 (Enhanced Logging)
- [ ] Decision log upgraded
- [ ] Query functions work
- [ ] Export to CSV functional

### Phase 5 (Policy Versioning)
- [ ] Policy metadata tracked
- [ ] Policy changes logged
- [ ] Git integration works

### Phase 6 (Testing & Deployment)
- [ ] All tests pass
- [ ] Performance targets met
- [ ] Documentation complete
- [ ] Agent deployed
- [ ] Dashboard deployed

## Rollback Plan

If any phase fails:
1. **Approval Queue**: Revert to V1 auto-approve only
2. **Dashboard**: Agent continues to work without dashboard
3. **Enhanced Logging**: Fall back to V1 logging
4. **Policy Versioning**: Use policies without versioning

All changes are additive and can be disabled via environment variables.

## Next Steps After Completion

1. Monitor approval queue for 24 hours
2. Train support managers on dashboard
3. Gather feedback on approval workflow
4. Plan V3 enhancements (multi-tenant, ML fraud detection)
