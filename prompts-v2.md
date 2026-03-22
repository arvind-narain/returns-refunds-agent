# V2 Implementation Prompts

**Branch**: `spec-driven-v2`  
**Date**: 2026-03-22  
**Purpose**: Concrete Kiro prompts for implementing V2 policy layer and dashboard

These prompts reference existing files and can be used directly with Kiro to generate working code.

---

## Prompt 1: Enhanced Policy Engine with Risk Scoring

```
Based on specs/returns-agent-v2.yaml and the existing src/agents/policy_engine.py, 
implement risk-based routing for the policy engine:

1. Create src/agents/risk_scorer.py with:
   - calculate_risk_score(return_data: dict) -> int function
   - Risk factors: refund_amount (0-40 pts), days_since_purchase (0-20 pts), 
     customer_return_history (0-20 pts), item_condition (0-10 pts), category_risk (0-10 pts)
   - Risk thresholds: 0-30 (auto-approve), 31-60 (auto-approve with monitoring), 
     61-80 (manual review), 81-100 (critical review)

2. Update src/agents/policy_engine.py to:
   - Import and integrate risk_scorer
   - Add calculate_risk_score() call in check_eligibility()
   - Return risk_score with eligibility decision
   - Add get_risk_level(score: int) -> str helper (returns "low", "medium", "high", "critical")

3. Create tests/test_risk_scorer.py with:
   - Test risk calculation for various scenarios
   - Test threshold boundaries
   - Test edge cases (negative amounts, future dates, etc.)

4. Create two new policy examples:
   - policies/electronics_merchant.yaml (90-day window, 15% restocking fee for opened items)
   - policies/clothing_merchant.yaml (30-day window, no restocking fee, final sale items)

Reference the existing policy_engine.py structure and maintain backward compatibility.
All new functions should include docstrings and type hints.
```

---

## Prompt 2: Approval Queue and DynamoDB Integration

```
Based on specs/returns-agent-v2.yaml and PLAN-implementation.md Milestone 2, 
implement the human approval workflow:

1. Create infrastructure/create_approval_queue_table.py:
   - DynamoDB table: "returns-approval-queue"
   - Partition key: "status" (pending/approved/denied)
   - Sort key: "created_at" (timestamp)
   - GSIs: "approval_id-index", "sla_deadline-index"
   - TTL: 30 days on "ttl" attribute
   - On-demand billing mode
   - Include table creation and verification logic

2. Create src/agents/approval_queue.py with:
   - add_to_queue(return_data: dict) -> str (returns approval_id)
   - get_pending_approvals(limit: int = 50) -> list (sorted by SLA deadline)
   - approve_request(approval_id: str, user_id: str) -> dict
   - deny_request(approval_id: str, user_id: str, reason: str) -> dict
   - check_sla_breaches() -> list (identify expired items)
   - Use boto3 DynamoDB client
   - Include proper error handling and logging

3. Create tests/test_approval_queue.py:
   - Test adding items to queue
   - Test retrieving pending approvals
   - Test approve/deny actions
   - Test SLA breach detection
   - Use moto for DynamoDB mocking

4. Update src/agents/decision_logger.py to:
   - Add log_approval_action(approval_id, action, user_id, reason) method
   - Integrate with existing decision logging

Reference the existing decision_logger.py structure. Ensure all DynamoDB operations
include error handling and retry logic. Use environment variables for table names.
```

---

## Prompt 3: Streamlit Dashboard with Observability Integration

```
Based on specs/returns-agent-v2.yaml, PLAN-implementation.md Milestone 3, and the existing
scripts/22_get_dashboard.py and agentcore-mcp-server/handlers/observability_handlers.py,
create a Streamlit dashboard for monitoring and approvals:

1. Create src/ui/dashboard_app.py (main app):
   - Multi-page navigation using st.sidebar
   - Pages: Home, Approvals, Analytics, Decisions, Policies
   - Authentication using st.session_state (simple username/password)
   - Role-based access: "agent" (view only) vs "manager" (approve/deny)

2. Create src/ui/pages/home.py:
   - Display metrics: total returns (today/week/month), approval rates, avg refund, 
     pending count, SLA breaches
   - Recent activity: last 10 decisions table, last 5 approvals, last 5 denials
   - Use src/agents/decision_logger.py to query DynamoDB
   - Refresh button with auto-refresh every 30 seconds

3. Create src/ui/pages/approvals.py:
   - List pending approvals from src/agents/approval_queue.py
   - Display: customer_id, order_id, refund_amount, risk_score, SLA countdown
   - Approve/Deny buttons with confirmation dialogs
   - Risk score gauge chart (use plotly or streamlit native)
   - Filter by risk level (low/medium/high/critical)
   - Sort by SLA deadline (ascending)

4. Create src/ui/pages/analytics.py:
   - Returns over time line chart (last 30 days)
   - Approval rate pie chart (auto vs manual)
   - Refund amounts histogram
   - Risk score distribution bar chart
   - Use data from decision_logger.py
   - Date range picker for filtering

5. Create src/ui/utils/db.py:
   - query_decisions(filters: dict) -> list helper
   - query_approvals(status: str) -> list helper
   - get_metrics(date_range: tuple) -> dict helper
   - Reuse boto3 DynamoDB client patterns from decision_logger.py

6. Create .streamlit/config.toml:
   - Theme: light mode, primary color #1f77b4
   - Layout: wide
   - Hide menu and footer

7. Create requirements_dashboard.txt:
   - streamlit>=1.30.0
   - boto3>=1.34.0
   - plotly>=5.18.0
   - pandas>=2.1.0
   - Include existing dependencies from requirements.txt

8. Integrate with existing observability:
   - Reference agentcore-mcp-server/handlers/observability_handlers.py for log queries
   - Use scripts/22_get_dashboard.py patterns for CloudWatch metrics
   - Display CloudWatch dashboard URL link in sidebar

Create a clean, professional UI with proper error handling. Use st.cache_data for
expensive queries. Include loading spinners and success/error messages for all actions.
All pages should handle empty data gracefully.
```

---

## Usage Instructions

1. **Ensure you're on the v2 branch**:
   ```bash
   git checkout spec-driven-v2
   ```

2. **Use prompts sequentially**:
   - Prompt 1 → Policy engine enhancements (Milestone 1)
   - Prompt 2 → Approval workflow (Milestone 2)
   - Prompt 3 → Dashboard (Milestone 3)

3. **After each prompt**:
   - Review generated code
   - Run tests: `pytest tests/`
   - Commit changes: `git commit -m "feat: <description>"`

4. **Test integration**:
   ```bash
   # After Prompt 1
   pytest tests/test_risk_scorer.py tests/test_policy_engine.py
   
   # After Prompt 2
   python infrastructure/create_approval_queue_table.py
   pytest tests/test_approval_queue.py
   
   # After Prompt 3
   streamlit run src/ui/dashboard_app.py
   ```

---

## Expected Deliverables

**Prompt 1**:
- `src/agents/risk_scorer.py` (~150 lines)
- Updated `src/agents/policy_engine.py` (+50 lines)
- `tests/test_risk_scorer.py` (~200 lines)
- `policies/electronics_merchant.yaml` (~80 lines)
- `policies/clothing_merchant.yaml` (~80 lines)

**Prompt 2**:
- `infrastructure/create_approval_queue_table.py` (~100 lines)
- `src/agents/approval_queue.py` (~250 lines)
- `tests/test_approval_queue.py` (~300 lines)
- Updated `src/agents/decision_logger.py` (+30 lines)

**Prompt 3**:
- `src/ui/dashboard_app.py` (~150 lines)
- `src/ui/pages/home.py` (~200 lines)
- `src/ui/pages/approvals.py` (~250 lines)
- `src/ui/pages/analytics.py` (~200 lines)
- `src/ui/utils/db.py` (~150 lines)
- `.streamlit/config.toml` (~20 lines)
- `requirements_dashboard.txt` (~15 lines)

**Total**: ~2,000 lines of production code + tests

---

## Notes

- All prompts reference existing files for consistency
- Prompts are designed to be copy-paste ready for Kiro
- Each prompt builds on previous work (sequential dependencies)
- Tests are included in each prompt for immediate validation
- Dashboard integrates with existing observability infrastructure
