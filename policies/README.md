# Return Policy Configuration

This directory contains configurable return and refund policies for the returns agent.

## Policy Structure

Policies are defined in YAML or JSON format and must conform to the schema in `schema.json`.

### Required Fields

- `policy_id`: Unique identifier (e.g., "default-policy-v1")
- `policy_name`: Human-readable name
- `version`: Semantic version (e.g., "1.0.0")
- `return_windows`: Return window in days by category
- `refund_rules`: Refund calculation rules

### Optional Fields

- `effective_date`: When policy becomes active (YYYY-MM-DD)
- `non_returnable_categories`: List of categories that cannot be returned

## Return Windows

Define how many days customers have to return items by category:

```yaml
return_windows:
  electronics: 90      # 90 days for electronics
  clothing: 30         # 30 days for clothing
  books: 30            # 30 days for books
  default: 30          # Default for unlisted categories
```

## Refund Rules

Define refund percentages and fees based on return reason and item condition:

```yaml
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

## Using Custom Policies

1. Create a new policy file (YAML or JSON)
2. Validate against `schema.json`
3. Set environment variable: `POLICY_FILE=policies/my_policy.yaml`
4. Restart the agent

## Policy Validation

Validate your policy before deployment:

```bash
python -c "from src.agents.policy_engine import PolicyEngine; PolicyEngine('policies/my_policy.yaml')"
```

## Examples

- `default_policy.yaml` - Standard policy matching current hardcoded rules
- `strict_policy.yaml` - Shorter return windows, higher fees (create as needed)
- `generous_policy.yaml` - Longer windows, lower fees (create as needed)

## Notes

- Policies are cached in memory for performance
- Changes require agent restart to take effect
- Policy version is logged with each decision for audit trail
