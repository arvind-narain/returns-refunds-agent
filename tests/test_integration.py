#!/usr/bin/env python3
"""
Integration test for Policy Engine + Decision Logger
Tests the complete flow of checking eligibility and calculating refunds with logging
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.policy_engine import get_policy_engine
from src.agents.decision_logger import get_decision_logger

def test_complete_return_flow():
    """Test complete return processing flow"""
    print("=" * 80)
    print("INTEGRATION TEST: Complete Return Flow")
    print("=" * 80)
    
    policy = get_policy_engine()
    logger = get_decision_logger()
    
    # Test scenario: Customer wants to return an electronics item
    print("\nScenario: Customer purchased electronics on 2026-03-01, wants to return on 2026-03-22")
    print("-" * 80)
    
    # Step 1: Check eligibility
    print("\n1. Checking eligibility...")
    eligibility_result = policy.check_eligibility('2026-03-01', 'electronics')
    print(f"   Eligible: {eligibility_result['eligible']}")
    print(f"   Reason: {eligibility_result['reason']}")
    print(f"   Policy Version: {eligibility_result['policy_version']}")
    
    # Log eligibility decision
    logger.log_eligibility_decision(
        order_id="INT-TEST-001",
        purchase_date="2026-03-01",
        category="electronics",
        eligible=eligibility_result['eligible'],
        reason=eligibility_result['reason'],
        policy_version=eligibility_result['policy_version'],
        actor_id="integration-test",
        session_id="test-session-001"
    )
    print("   ✓ Eligibility decision logged")
    
    # Step 2: Calculate refund (if eligible)
    if eligibility_result['eligible']:
        print("\n2. Calculating refund...")
        refund_result = policy.calculate_refund(
            original_price=299.99,
            condition='opened_unused',
            reason='changed_mind'
        )
        print(f"   Original Price: ${refund_result['original_price']:.2f}")
        print(f"   Refund Amount: ${refund_result['refund_amount']:.2f}")
        print(f"   Refund Percentage: {refund_result['refund_percentage']}%")
        print(f"   Restocking Fee: ${refund_result['restocking_fee']:.2f}")
        print(f"   Shipping Refunded: {refund_result['shipping_refunded']}")
        print(f"   Policy Version: {refund_result['policy_version']}")
        
        # Log refund decision
        logger.log_refund_decision(
            order_id="INT-TEST-001",
            original_price=refund_result['original_price'],
            refund_amount=refund_result['refund_amount'],
            condition='opened_unused',
            return_reason='changed_mind',
            policy_version=refund_result['policy_version'],
            actor_id="integration-test",
            session_id="test-session-001"
        )
        print("   ✓ Refund decision logged")
    
    print("\n" + "=" * 80)
    print("✓ Integration test completed successfully")
    print("\nCheck CloudWatch Logs for decision entries:")
    print("  - Eligibility decision for order INT-TEST-001")
    print("  - Refund decision for order INT-TEST-001")
    print("=" * 80)
    
    return True

def test_multiple_scenarios():
    """Test multiple return scenarios"""
    print("\n" + "=" * 80)
    print("INTEGRATION TEST: Multiple Scenarios")
    print("=" * 80)
    
    policy = get_policy_engine()
    logger = get_decision_logger()
    
    scenarios = [
        {
            'name': 'Defective electronics',
            'order_id': 'INT-TEST-002',
            'purchase_date': '2026-03-15',
            'category': 'electronics',
            'price': 499.99,
            'condition': 'unopened',
            'reason': 'defective'
        },
        {
            'name': 'Used clothing',
            'order_id': 'INT-TEST-003',
            'purchase_date': '2026-03-20',
            'category': 'clothing',
            'price': 79.99,
            'condition': 'used',
            'reason': 'changed_mind'
        },
        {
            'name': 'Digital product (non-returnable)',
            'order_id': 'INT-TEST-004',
            'purchase_date': '2026-03-22',
            'category': 'digital',
            'price': 29.99,
            'condition': 'unopened',
            'reason': 'changed_mind'
        }
    ]
    
    for scenario in scenarios:
        print(f"\nScenario: {scenario['name']}")
        print("-" * 80)
        
        # Check eligibility
        eligibility = policy.check_eligibility(scenario['purchase_date'], scenario['category'])
        print(f"Eligible: {eligibility['eligible']} - {eligibility['reason']}")
        
        # Log eligibility
        logger.log_eligibility_decision(
            order_id=scenario['order_id'],
            purchase_date=scenario['purchase_date'],
            category=scenario['category'],
            eligible=eligibility['eligible'],
            reason=eligibility['reason'],
            policy_version=eligibility['policy_version'],
            actor_id="integration-test",
            session_id="test-session-002"
        )
        
        # Calculate refund if eligible
        if eligibility['eligible']:
            refund = policy.calculate_refund(
                scenario['price'],
                scenario['condition'],
                scenario['reason']
            )
            print(f"Refund: ${refund['refund_amount']:.2f} (from ${scenario['price']:.2f})")
            
            # Log refund
            logger.log_refund_decision(
                order_id=scenario['order_id'],
                original_price=scenario['price'],
                refund_amount=refund['refund_amount'],
                condition=scenario['condition'],
                return_reason=scenario['reason'],
                policy_version=refund['policy_version'],
                actor_id="integration-test",
                session_id="test-session-002"
            )
    
    print("\n" + "=" * 80)
    print("✓ Multiple scenarios test completed")
    print("=" * 80)
    
    return True

def main():
    """Run all integration tests"""
    print("\n" + "=" * 80)
    print("INTEGRATION TEST SUITE")
    print("=" * 80 + "\n")
    
    results = []
    
    results.append(("Complete Return Flow", test_complete_return_flow()))
    results.append(("Multiple Scenarios", test_multiple_scenarios()))
    
    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n✓ All integration tests passed!")
        return 0
    else:
        print("\n✗ Some integration tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
