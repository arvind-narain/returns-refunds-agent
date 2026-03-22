# Implementation Plan: V2 Returns & Refunds Agent

**Branch**: `spec-driven-v2`  
**Time Budget**: 1-2 weeks  
**Date**: 2026-03-22  
**Builds On**: V1 Implementation (Policy Engine + Decision Logging)

## Overview

This plan implements V2 enhancements to the returns/refunds agent based on `specs/returns-agent-v2.yaml`. Tasks are organized into 4 milestones, with each task taking 30-90 minutes and referencing concrete files.

**V2 Enhancements**:
1. **Configurable Policies**: YAML-based per-merchant policies (no hardcoded rules)
2. **Human Approval Workflow**: Risk-based routing with manual approval queue
3. **Streamlit Dashboard**: Monitoring, approvals, and analytics
4. **Enhanced Logging**: DynamoDB-based decision log with queryable history

## Prerequisites

- V1 implementation complete (policy engine, decision logging, observability)
- AWS services: DynamoDB, S3, CloudWatch, Lambda, AgentCore Runtime
- Python 3.12+ with existing dependencies
- Streamlit for dashboard UI

---

# Milestone 1: Policies & Risk Management (3-4 hours)

## Task 1.1: Create Additional Policy Examples (45 min)
**Files**: `policies/electronics_merchant.yaml`, `policies/clothing_merchant.yaml`

Create merchant-specific policy examples:
- Electronics: 90-day return window, 15% restocking fee for opened items
- Clothing: 30-day return window, no restocking fee, final sale items

**Deliverables**:
- `policies/electronics_merchant.yaml`
- `policies/clothing_merchant.yaml`
- Update `policies/README.md` with examples

---

## Task 1.2: Implement Risk Scoring Module (60 min)
**Files**: `src/agents/risk_scorer.py`, `tests/test_risk_scorer.py`

Create risk scoring logic for routing decisions:

```python
def calculate_risk_score(return_data: dict) -> int:
    """Calculate risk score (0-100) based on multiple factors"""
    # Refund amount (0-40 points)
    # Days since purchase (0-20 points)
    # Customer return history (0-20 points)
    # Item condition (0-10 points)
    # Category risk (0-10 points)
```

**Risk Thresholds**:
- 0-30: Auto-approve
- 31-60: Auto-approve with monitoring
- 61-80: Manual review
- 81-100: Critical review (manager required)

**Deliverables**:
- `src/agents/risk_scorer.py`
- `tests/test_risk_scorer.py` (unit tests)

---

## Task 1.3: Update Policy Engine with Risk Integration (45 min)
**Files**: `src/agents/policy_engine.py`

Integrate risk scoring into policy evaluation:
- Add `calculate_risk_score()` call
- Return risk score with eligibility decision
- Add risk-based routing logic

**Deliverables**:
- Updated `src/agents/policy_engine.py`
- Updated tests in `tests/test_policy_engine.py`

---

# Milestone 2: Approval Workflow (4-5 hours)

## Task 2.1: Create Approval Queue DynamoDB Table (45 min)
**Files**: `infrastructure/create_approval_queue_table.py`

Create DynamoDB table for approval queue:

```python
table_name: "returns-approval-queue"
partition_key: "status" (pending/approved/denied)
sort_key: "created_at" (timestamp)
gsi: ["approval_id-index", "sla_deadline-index"]
ttl: 30 days
```

**Deliverables**:
- `infrastructure/create_approval_queue_table.py`
- Run script to create table

---

## Task 2.2: Implement Approval Queue Module (75 min)
**Files**: `src/agents/approval_queue.py`, `tests/test_approval_queue.py`

Create approval queue management:

```python
def add_to_queue(return_data: dict) -> str:
    """Add approval request, return approval_id"""

def get_pending_approvals() -> list:
    """List pending items sorted by SLA deadline"""

def approve_request(approval_id: str, user_id: str) -> dict:
    """Approve and process refund"""

def deny_request(approval_id: str, user_id: str, reason: str) -> dict:
    """Deny with reason"""

def check_sla_breaches() -> list:
    """Identify expired items"""
```

**Deliverables**:
- `src/agents/approval_queue.py`
- `tests/test_approval_queue.py`

---

## Task 2.3: Add Approval Tools to Agent (60 min)
**Files**: `src/agents/17_runtime_agent.py`

Add new tools to agent:

```python
@tool
def request_approval(return_data: dict) -> dict:
    """Request human approval for high-risk refund"""

@tool
def check_approval_status(approval_id: str) -> dict:
    """Check status of approval request"""

@tool
def get_decision_history(customer_id: str = None) -> list:
    """Retrieve past decisions for context"""
```

**Deliverables**:
- Updated `src/agents/17_runtime_agent.py`
- Updated system prompt mentioning approval workflow

---

## Task 2.4: Integration Testing (60 min)
**Files**: `tests/test_approval_integration.py`

Test end-to-end approval workflow:
- Low-risk return → auto-approve
- High-risk return → add to queue
- Manager approval → process refund
- Manager denial → log reason

**Deliverables**:
- `tests/test_approval_integration.py`

---

# Milestone 3: Dashboard (6-8 hours)

## Task 3.1: Dashboard Foundation & Navigation (60 min)
**Files**: `src/ui/dashboard_app.py`, `.streamlit/config.toml`

Create main dashboard structure:

```
src/ui/
├── dashboard_app.py (main app with navigation)
├── pages/
│   ├── home.py
│   ├── approvals.py
│   ├── analytics.py
│   ├── decisions.py
│   └── policies.py
└── utils/
    ├── auth.py
    ├── db.py
    └── charts.py
```

**Deliverables**:
- `src/ui/dashboard_app.py` (navigation sidebar)
- `.streamlit/config.toml` (theme, layout)
- `src/ui/utils/db.py` (DynamoDB query helpers)

---

## Task 3.2: Home Page - Overview Metrics (75 min)
**Files**: `src/ui/pages/home.py`

Display key metrics and recent activity:
- Metrics: Total returns, approval rates, avg refund, pending count, SLA breaches
- Recent activity: Last 10 decisions, last 5 approvals, last 5 denials

**Deliverables**:
- `src/ui/pages/home.py`
- Query functions in `src/ui/utils/db.py`

---

## Task 3.3: Approvals Page - Queue Management (90 min)
**Files**: `src/ui/pages/approvals.py`

Build approval queue interface:
- List pending approvals (sorted by SLA deadline)
- View return details (customer, order, amount, risk)
- Approve/Deny buttons with confirmation
- SLA countdown timer
- Risk score gauge chart
- Filter by risk level

**Deliverables**:
- `src/ui/pages/approvals.py`
- Approval action handlers

---

## Task 3.4: Analytics Page - Charts (75 min)
**Files**: `src/ui/pages/analytics.py`, `src/ui/utils/charts.py`

Create analytics visualizations:
- Returns over time (line chart)
- Approval rate by type (pie chart)
- Refund amounts distribution (histogram)
- Risk score distribution (bar chart)
- Top customers by return count (table)

**Deliverables**:
- `src/ui/pages/analytics.py`
- `src/ui/utils/charts.py` (plotting helpers)

---

## Task 3.5: Decisions Page - Searchable Log (60 min)
**Files**: `src/ui/pages/decisions.py`

Build decision log viewer:
- Search by customer, order, date
- Filter by decision type, risk score
- Sortable columns
- Export to CSV
- View decision details (modal)

**Deliverables**:
- `src/ui/pages/decisions.py`

---

## Task 3.6: Policies Page - Policy Viewer (60 min)
**Files**: `src/ui/pages/policies.py`

Display policy information:
- List available policies
- View policy details (YAML formatted)
- Compare two policies side-by-side
- Policy change history (Git log)
- Active policy indicator

**Deliverables**:
- `src/ui/pages/policies.py`

---

## Task 3.7: Authentication & Authorization (60 min)
**Files**: `src/ui/utils/auth.py`, `.streamlit/secrets.toml.template`

Implement dashboard security:
- Username/password authentication
- Session management (30-min timeout)
- Role-based access (agent vs. manager)
- Audit logging for approval actions

**Deliverables**:
- `src/ui/utils/auth.py`
- `.streamlit/secrets.toml.template`

---

# Milestone 4: Enhanced Logging & Deployment (2-3 hours)

## Task 4.1: Upgrade Decision Log Table (45 min)
**Files**: `infrastructure/upgrade_decision_log_table.py`

Add GSIs to decision log table:
- `customer_id-timestamp-index` (customer history)
- `decision_type-timestamp-index` (analytics)
- `decided_by-timestamp-index` (user activity)

**Deliverables**:
- `infrastructure/upgrade_decision_log_table.py`
- Run script to add GSIs

---

## Task 4.2: Enhanced Decision Logger (60 min)
**Files**: `src/agents/decision_logger.py`

Add new query functions:
- `get_customer_history(customer_id)` - Query by customer
- `get_decisions_by_type(type, date_range)` - Analytics queries
- `get_user_decisions(user_id)` - Audit trail

**Deliverables**:
- Updated `src/agents/decision_logger.py`
- Updated tests

---

## Task 4.3: Deploy Dashboard (45 min)
**Files**: `requirements_dashboard.txt`, deployment scripts

Deploy dashboard to Streamlit Cloud or EC2:
- Create `requirements_dashboard.txt`
- Configure secrets
- Deploy and test

**Deliverables**:
- `requirements_dashboard.txt`
- Dashboard URL
- Deployment documentation

---

## Task 4.4: End-to-End Testing (60 min)
**Files**: `tests/test_e2e_v2.py`

Test complete V2 workflow:
- Policy evaluation with risk scoring
- Auto-approve low-risk returns
- Manual approval for high-risk returns
- Dashboard displays correct data
- Decision logging works

**Deliverables**:
- `tests/test_e2e_v2.py`
- Test results documentation

---

# Timeline Summary

| Milestone | Duration | Tasks |
|-----------|----------|-------|
| 1. Policies & Risk | 3-4 hours | 3 tasks |
| 2. Approval Workflow | 4-5 hours | 4 tasks |
| 3. Dashboard | 6-8 hours | 7 tasks |
| 4. Logging & Deployment | 2-3 hours | 4 tasks |
| **Total** | **15-20 hours** | **18 tasks** |

**Realistic Timeline**: 1-2 weeks (2-3 hours/day)

---

# Success Criteria

- [ ] Policies loaded from YAML files (no hardcoded rules)
- [ ] Risk scoring routes high-risk returns to approval queue
- [ ] Dashboard displays metrics and pending approvals
- [ ] Managers can approve/deny requests via dashboard
- [ ] All decisions logged to DynamoDB with queryable history
- [ ] End-to-end tests pass
- [ ] Dashboard deployed and accessible

---

# Rollback Plan

If any milestone fails:
1. **Policies**: Revert to V1 policy engine
2. **Approval Workflow**: Disable approval queue, auto-approve all
3. **Dashboard**: Stop dashboard, use CloudWatch for monitoring
4. **Logging**: Fall back to CloudWatch-only logging

All changes are additive and can be disabled via environment variables.
