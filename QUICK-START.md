# Quick Start: 4-Hour Implementation Session

This guide helps you execute the implementation plan in `PLAN-implementation.md` efficiently.

## Pre-Session Checklist (5 minutes)

- [ ] On `spec-driven-v1` branch
- [ ] Python environment activated
- [ ] AWS credentials configured
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] Current agent working (test with `python src/agents/01_returns_refunds_agent.py`)

## Session Timeline

### Hour 1: Policy Layer Foundation (Tasks 1.1-1.3)

**Task 1.1: Create Policy Schema (30 min)**
```bash
# Apply patch or create files manually
git apply patches/001-policy-schema.patch

# Verify files created
ls -la policies/
cat policies/default_policy.yaml
```

**Task 1.2: Implement Policy Engine (30 min)**
```bash
# Apply patch
git apply patches/002-policy-engine.patch

# Run tests
python -m pytest src/tests/test_policy_engine.py -v

# Test policy loading
python -c "from src.agents.policy_engine import PolicyEngine; p = PolicyEngine(); print(p.get_policy_info())"
```

**Break: 5 minutes** ☕

---

### Hour 2: Policy Integration + Decision Logging Setup (Tasks 1.3, 2.1-2.2)

**Task 1.3: Integrate Policy Engine (30 min)**
```bash
# Apply patch
git apply patches/003-integrate-policy-engine.patch

# Test agent with policy engine
export POLICY_FILE=policies/default_policy.yaml
python src/agents/01_returns_refunds_agent.py

# Verify policy info tool works
python -c "from src.agents.policy_engine import get_policy_engine; print(get_policy_engine().get_policy_info())"
```

**Task 2.1-2.2: Decision Logging (30 min)**
```bash
# Apply patch
git apply patches/004-decision-logging.patch

# Try to create DynamoDB table (may fail, that's OK)
python infrastructure/create_decision_log_table.py

# If DynamoDB fails, logging will use S3 fallback
# Test decision logger
python -c "from src.agents.decision_logger import get_decision_logger; logger = get_decision_logger(); print('Logger initialized')"
```

**Break: 10 minutes** ☕

---

### Hour 3: Integrate Decision Logging into Tools (Task 2.3)

**Task 2.3: Add Logging to Tools (40 min)**

Edit `src/agents/17_runtime_agent.py`:

```python
# Add import at top
from src.agents.decision_logger import get_decision_logger

# In check_return_eligibility tool, after getting result:
try:
    decision_logger = get_decision_logger()
    decision_logger.log_eligibility_decision(
        order_id=order_id,
        purchase_date=purchase_date,
        category=item_category,
        eligible=result['eligible'],
        reason=result['reason'],
        policy_version=result.get('policy_version', 'unknown'),
        actor_id=ACTOR_ID,
        session_id=SESSION_ID
    )
except Exception as e:
    logger.warning(f"Failed to log decision: {e}")
```

```python
# In calculate_refund_amount tool, after getting result:
try:
    decision_logger = get_decision_logger()
    decision_logger.log_refund_decision(
        order_id='unknown',  # Add order_id parameter if available
        original_price=original_price,
        refund_amount=result['refund_amount'],
        condition=item_condition,
        return_reason=return_reason,
        policy_version=result.get('policy_version', 'unknown'),
        actor_id=ACTOR_ID,
        session_id=SESSION_ID
    )
except Exception as e:
    logger.warning(f"Failed to log decision: {e}")
```

**Test end-to-end:**
```bash
# Run agent and make a decision
python src/agents/01_returns_refunds_agent.py

# Check CloudWatch Logs for decision logs
aws logs tail /aws/lambda/returns-agent --follow
```

**Break: 10 minutes** ☕

---

### Hour 4: Basic Observability (Tasks 3.1-3.2)

**Task 3.1: Metrics Collection (30 min)**

Create `src/agents/metrics.py`:

```python
"""Simple metrics collection for decision tracking"""
import boto3
from datetime import datetime
from typing import Dict, Any

cloudwatch = boto3.client('cloudwatch', region_name='us-west-2')

def publish_decision_metric(decision_type: str, decision: str):
    """Publish decision metric to CloudWatch"""
    try:
        cloudwatch.put_metric_data(
            Namespace='ReturnsAgent',
            MetricData=[
                {
                    'MetricName': f'Decision_{decision.title()}',
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': datetime.utcnow(),
                    'Dimensions': [
                        {'Name': 'DecisionType', 'Value': decision_type}
                    ]
                }
            ]
        )
    except Exception as e:
        print(f"Failed to publish metric: {e}")
```

Add to tools:
```python
# After logging decision
from src.agents.metrics import publish_decision_metric
publish_decision_metric('eligibility', 'approved' if result['eligible'] else 'denied')
```

**Task 3.2: Metrics Dashboard Script (30 min)**

Create `src/ui/metrics_dashboard.py`:

```python
"""CLI dashboard for viewing decision metrics"""
import boto3
from datetime import datetime, timedelta
from collections import defaultdict

def get_decision_counts(hours=24):
    """Get decision counts from CloudWatch Logs"""
    logs = boto3.client('logs', region_name='us-west-2')
    
    # Query CloudWatch Logs Insights
    query = """
    fields @timestamp, decision_type, decision
    | filter decision_type = "eligibility" or decision_type = "refund"
    | stats count() by decision
    """
    
    start_time = int((datetime.now() - timedelta(hours=hours)).timestamp())
    end_time = int(datetime.now().timestamp())
    
    try:
        response = logs.start_query(
            logGroupName='/aws/lambda/returns-agent',
            startTime=start_time,
            endTime=end_time,
            queryString=query
        )
        
        query_id = response['queryId']
        
        # Wait for query to complete
        import time
        while True:
            result = logs.get_query_results(queryId=query_id)
            if result['status'] == 'Complete':
                break
            time.sleep(1)
        
        # Parse results
        counts = defaultdict(int)
        for row in result['results']:
            decision = next((f['value'] for f in row if f['field'] == 'decision'), 'unknown')
            count = int(next((f['value'] for f in row if f['field'] == 'count()'), 0))
            counts[decision] = count
        
        return counts
    
    except Exception as e:
        print(f"Error querying logs: {e}")
        return {}

def display_dashboard():
    """Display metrics dashboard"""
    print("=" * 60)
    print("RETURNS AGENT METRICS DASHBOARD")
    print("=" * 60)
    
    # Get counts for different time periods
    for period, hours in [("Last 24 Hours", 24), ("Last 7 Days", 168)]:
        print(f"\n{period}:")
        counts = get_decision_counts(hours)
        
        approved = counts.get('approved', 0)
        denied = counts.get('denied', 0)
        total = approved + denied
        
        print(f"  Approved: {approved}")
        print(f"  Denied:   {denied}")
        print(f"  Total:    {total}")
        
        if total > 0:
            approval_rate = (approved / total) * 100
            print(f"  Approval Rate: {approval_rate:.1f}%")
        
        # Simple ASCII bar chart
        if approved > 0 or denied > 0:
            max_count = max(approved, denied)
            approved_bar = '█' * int((approved / max_count) * 40)
            denied_bar = '█' * int((denied / max_count) * 40)
            print(f"\n  Approved: {approved_bar} {approved}")
            print(f"  Denied:   {denied_bar} {denied}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    display_dashboard()
```

**Test dashboard:**
```bash
python src/ui/metrics_dashboard.py
```

---

## Post-Session Checklist (10 minutes)

- [ ] All tests passing: `python -m pytest src/tests/ -v`
- [ ] Policy engine working: `python -c "from src.agents.policy_engine import get_policy_engine; print(get_policy_engine().get_policy_info())"`
- [ ] Decision logging working: Check CloudWatch Logs
- [ ] Metrics dashboard displays data: `python src/ui/metrics_dashboard.py`
- [ ] Commit changes: `git add . && git commit -m "Add policy layer, decision logging, and observability"`
- [ ] Push to GitHub: `git push origin spec-driven-v1`

## If You Run Out of Time

### Minimum Viable Implementation (2-3 hours)
Focus on:
1. ✅ Policy Layer (Tasks 1.1-1.3) - 90 minutes
2. ✅ Decision Logging to CloudWatch only (Task 2.1-2.3) - 60 minutes
3. ⏭️ Skip DynamoDB table creation (use S3 fallback)
4. ⏭️ Skip metrics dashboard (use CloudWatch Logs Insights manually)

### What to Skip
- DynamoDB table creation (use S3 fallback)
- Streamlit UI integration (Task 3.3)
- Comprehensive testing (Task 4.1)
- Documentation updates (Task 4.2)

### What NOT to Skip
- Policy engine implementation (core feature)
- Decision logging to CloudWatch (audit requirement)
- Basic integration testing (ensure it works)

## Troubleshooting

### "Policy file not found"
```bash
# Check file exists
ls -la policies/default_policy.yaml

# Set environment variable
export POLICY_FILE=policies/default_policy.yaml
```

### "DynamoDB table creation failed"
```bash
# This is OK! Decision logging will use S3 fallback
# Verify S3 fallback is working
python -c "from src.agents.decision_logger import DecisionLogger; logger = DecisionLogger(log_to_dynamodb=False, log_to_s3=True); print('S3 fallback enabled')"
```

### "Import errors"
```bash
# Ensure you're in repo root
pwd

# Add src to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

### "AWS credentials not configured"
```bash
# Configure AWS CLI
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=us-west-2
```

## Success Criteria

At the end of 4-5 hours, you should have:

✅ **Policy Layer**
- Policies loaded from YAML files
- Agent uses policies instead of hardcoded rules
- Can switch policies via environment variable

✅ **Decision Logging**
- All decisions logged with unique IDs
- Logs include who, what, why, when
- Logs queryable in CloudWatch

✅ **Basic Observability**
- Can view decision counts
- Can calculate approval rate
- Metrics available via CLI dashboard

## Next Steps

After completing this session:

1. Deploy to AgentCore Runtime: `python scripts/19_deploy_agent.py`
2. Monitor decision logs for 24 hours
3. Review metrics dashboard for insights
4. Create additional policies for testing
5. Add Streamlit UI integration (Task 3.3)
6. Complete documentation (Task 4.2)

