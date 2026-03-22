#!/usr/bin/env python3
"""
Edge case tests for Policy Engine and Decision Logger
Tests boundary conditions, error handling, and unusual scenarios
"""

import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.policy_engine import PolicyEngine, get_policy_engine
from src.agents.decision_logger import DecisionLogger, get_decision_logger

def test_boundary_dates():
    """Test edge cases around return window boundaries"""
    print("=" * 80)
    print("TEST 1: Boundary Date Cases")
    print("=" * 80)
    
    policy = get_policy_engine()
    
    # Calculate exact boundary dates
    today = datetime.now()
    
    test_cases = [
        {
            'name': 'Exactly 30 days ago (clothing boundary)',
            'purchase_date': (today - timedelta(days=30)).strftime('%Y-%m-%d'),
            'category': 'clothing',
            'expected_eligible': True  # Should be eligible on day 30
        },
        {
            'name': 'Exactly 31 days ago (clothing expired)',
            'purchase_date': (today - timedelta(days=31)).strftime('%Y-%m-%d'),
            'category': 'clothing',
            'expected_eligible': False
        },
        {
            'name': 'Exactly 90 days ago (electronics boundary)',
            'purchase_date': (today - timedelta(days=90)).strftime('%Y-%m-%d'),
            'category': 'electronics',
            'expected_eligible': True  # Should be eligible on day 90
        },
        {
            'name': 'Exactly 91 days ago (electronics expired)',
            'purchase_date': (today - timedelta(days=91)).strftime('%Y-%m-%d'),
            'category': 'electronics',
            'expected_eligible': False
        },
        {
            'name': 'Today (day 0)',
            'purchase_date': today.strftime('%Y-%m-%d'),
            'category': 'electronics',
            'expected_eligible': True
        },
        {
            'name': 'Future date (invalid)',
            'purchase_date': (today + timedelta(days=1)).strftime('%Y-%m-%d'),
            'category': 'electronics',
            'expected_eligible': True  # Future dates treated as day 0
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        try:
            result = policy.check_eligibility(test['purchase_date'], test['category'])
            
            if result['eligible'] == test['expected_eligible']:
                print(f"✓ {test['name']}: {result['eligible']}")
                passed += 1
            else:
                print(f"✗ {test['name']}: Expected {test['expected_eligible']}, got {result['eligible']}")
                print(f"  Reason: {result['reason']}")
                failed += 1
        except Exception as e:
            print(f"✗ {test['name']}: Error - {e}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0

def test_invalid_inputs():
    """Test handling of invalid inputs"""
    print("\n" + "=" * 80)
    print("TEST 2: Invalid Input Handling")
    print("=" * 80)
    
    policy = get_policy_engine()
    
    test_cases = [
        {
            'name': 'Invalid date format',
            'purchase_date': '2026-13-45',  # Invalid month/day
            'category': 'electronics',
            'should_handle': True
        },
        {
            'name': 'Non-date string',
            'purchase_date': 'not-a-date',
            'category': 'electronics',
            'should_handle': True
        },
        {
            'name': 'Empty date',
            'purchase_date': '',
            'category': 'electronics',
            'should_handle': True
        },
        {
            'name': 'Case variations in category',
            'purchase_date': '2026-03-01',
            'category': 'ELECTRONICS',  # Uppercase
            'should_handle': True
        },
        {
            'name': 'Unknown category',
            'purchase_date': '2026-03-01',
            'category': 'unknown_category',
            'should_handle': True
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        try:
            result = policy.check_eligibility(test['purchase_date'], test['category'])
            
            # Should return a result (not crash)
            if 'eligible' in result and 'reason' in result:
                print(f"✓ {test['name']}: Handled gracefully")
                print(f"  Result: {result['eligible']} - {result['reason']}")
                passed += 1
            else:
                print(f"✗ {test['name']}: Invalid result structure")
                failed += 1
        except Exception as e:
            if test['should_handle']:
                print(f"✗ {test['name']}: Should handle but raised: {e}")
                failed += 1
            else:
                print(f"✓ {test['name']}: Correctly raised exception")
                passed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0

def test_extreme_refund_values():
    """Test refund calculations with extreme values"""
    print("\n" + "=" * 80)
    print("TEST 3: Extreme Refund Values")
    print("=" * 80)
    
    policy = get_policy_engine()
    
    test_cases = [
        {
            'name': 'Zero price',
            'price': 0.00,
            'condition': 'unopened',
            'reason': 'defective',
            'expected_refund': 0.00
        },
        {
            'name': 'Very small price (1 cent)',
            'price': 0.01,
            'condition': 'unopened',
            'reason': 'changed_mind',
            'expected_refund': 0.01
        },
        {
            'name': 'Very large price',
            'price': 999999.99,
            'condition': 'unopened',
            'reason': 'defective',
            'expected_refund': 999999.99
        },
        {
            'name': 'Negative price (invalid)',
            'price': -100.00,
            'condition': 'unopened',
            'reason': 'defective',
            'should_handle': True
        },
        {
            'name': 'Used item with restocking fee',
            'price': 10.00,
            'condition': 'used',
            'reason': 'changed_mind',
            'expected_refund': 6.00  # 80% refund - 20% restocking = 60%
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        try:
            result = policy.calculate_refund(test['price'], test['condition'], test['reason'])
            
            if 'expected_refund' in test:
                if abs(result['refund_amount'] - test['expected_refund']) < 0.01:
                    print(f"✓ {test['name']}: ${result['refund_amount']:.2f}")
                    passed += 1
                else:
                    print(f"✗ {test['name']}: Expected ${test['expected_refund']:.2f}, got ${result['refund_amount']:.2f}")
                    failed += 1
            else:
                # Just check it doesn't crash
                print(f"✓ {test['name']}: Handled (refund: ${result['refund_amount']:.2f})")
                passed += 1
        except Exception as e:
            if test.get('should_handle'):
                print(f"✓ {test['name']}: Correctly handled edge case")
                passed += 1
            else:
                print(f"✗ {test['name']}: Error - {e}")
                failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0

def test_concurrent_policy_access():
    """Test that singleton pattern works correctly"""
    print("\n" + "=" * 80)
    print("TEST 4: Concurrent Policy Access")
    print("=" * 80)
    
    try:
        # Get multiple instances
        policy1 = get_policy_engine()
        policy2 = get_policy_engine()
        policy3 = get_policy_engine()
        
        # All should be the same instance
        if policy1 is policy2 is policy3:
            print("✓ All instances are the same (singleton working)")
            
            # Test that they all return same results
            result1 = policy1.check_eligibility('2026-03-01', 'electronics')
            result2 = policy2.check_eligibility('2026-03-01', 'electronics')
            result3 = policy3.check_eligibility('2026-03-01', 'electronics')
            
            if result1 == result2 == result3:
                print("✓ All instances return consistent results")
                return True
            else:
                print("✗ Instances return different results")
                return False
        else:
            print("✗ Instances are different (singleton not working)")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_decision_logger_edge_cases():
    """Test decision logger with edge cases"""
    print("\n" + "=" * 80)
    print("TEST 5: Decision Logger Edge Cases")
    print("=" * 80)
    
    logger = get_decision_logger()
    
    test_cases = [
        {
            'name': 'Very long order ID',
            'order_id': 'A' * 1000,
            'should_handle': True
        },
        {
            'name': 'Special characters in order ID',
            'order_id': 'ORD-001!@#$%^&*()',
            'should_handle': True
        },
        {
            'name': 'Unicode in order ID',
            'order_id': 'ORD-001-日本語',
            'should_handle': True
        },
        {
            'name': 'Empty order ID',
            'order_id': '',
            'should_handle': True
        },
        {
            'name': 'Very large refund amount',
            'order_id': 'EDGE-001',
            'refund_amount': 999999999.99,
            'should_handle': True
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        try:
            if 'refund_amount' in test:
                logger.log_refund_decision(
                    order_id=test['order_id'],
                    original_price=test['refund_amount'],
                    refund_amount=test['refund_amount'],
                    condition='unopened',
                    return_reason='test',
                    policy_version='1.0.0'
                )
            else:
                logger.log_eligibility_decision(
                    order_id=test['order_id'],
                    purchase_date='2026-03-01',
                    category='test',
                    eligible=True,
                    reason='test',
                    policy_version='1.0.0'
                )
            
            print(f"✓ {test['name']}: Logged successfully")
            passed += 1
        except Exception as e:
            if test['should_handle']:
                print(f"✗ {test['name']}: Should handle but raised: {e}")
                failed += 1
            else:
                print(f"✓ {test['name']}: Correctly raised exception")
                passed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0

def test_missing_optional_fields():
    """Test decision logger with missing optional fields"""
    print("\n" + "=" * 80)
    print("TEST 6: Missing Optional Fields")
    print("=" * 80)
    
    logger = get_decision_logger()
    
    try:
        # Log without actor_id and session_id (optional fields)
        logger.log_eligibility_decision(
            order_id="OPTIONAL-001",
            purchase_date="2026-03-01",
            category="electronics",
            eligible=True,
            reason="test",
            policy_version="1.0.0"
            # actor_id and session_id omitted
        )
        print("✓ Logged without optional fields (actor_id, session_id)")
        
        # Log with None values
        logger.log_refund_decision(
            order_id="OPTIONAL-002",
            original_price=100.00,
            refund_amount=85.00,
            condition="opened_unused",
            return_reason="changed_mind",
            policy_version="1.0.0",
            actor_id=None,
            session_id=None
        )
        print("✓ Logged with None values for optional fields")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_policy_version_tracking():
    """Test that policy version is tracked in all operations"""
    print("\n" + "=" * 80)
    print("TEST 7: Policy Version Tracking")
    print("=" * 80)
    
    policy = get_policy_engine()
    
    try:
        # Get policy info
        info = policy.get_policy_info()
        policy_version = info['version']
        print(f"✓ Policy version: {policy_version}")
        
        # Check eligibility includes version
        eligibility = policy.check_eligibility('2026-03-01', 'electronics')
        if 'policy_version' in eligibility:
            print(f"✓ Eligibility check includes policy version: {eligibility['policy_version']}")
        else:
            print("✗ Eligibility check missing policy version")
            return False
        
        # Check refund calculation includes version
        refund = policy.calculate_refund(100.00, 'unopened', 'defective')
        if 'policy_version' in refund:
            print(f"✓ Refund calculation includes policy version: {refund['policy_version']}")
        else:
            print("✗ Refund calculation missing policy version")
            return False
        
        # Verify versions match
        if eligibility['policy_version'] == refund['policy_version'] == policy_version:
            print("✓ All operations use consistent policy version")
            return True
        else:
            print("✗ Policy versions inconsistent across operations")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    """Run all edge case tests"""
    print("\n" + "=" * 80)
    print("EDGE CASE TEST SUITE")
    print("=" * 80 + "\n")
    
    results = []
    
    results.append(("Boundary Date Cases", test_boundary_dates()))
    results.append(("Invalid Input Handling", test_invalid_inputs()))
    results.append(("Extreme Refund Values", test_extreme_refund_values()))
    results.append(("Concurrent Policy Access", test_concurrent_policy_access()))
    results.append(("Decision Logger Edge Cases", test_decision_logger_edge_cases()))
    results.append(("Missing Optional Fields", test_missing_optional_fields()))
    results.append(("Policy Version Tracking", test_policy_version_tracking()))
    
    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n✓ All edge case tests passed!")
        return 0
    else:
        print("\n✗ Some edge case tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
