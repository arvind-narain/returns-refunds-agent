#!/usr/bin/env python3
"""
Test script for Policy Engine
Tests policy loading, eligibility checks, and refund calculations
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.policy_engine import PolicyEngine, get_policy_engine

def test_policy_loading():
    """Test that policy loads correctly"""
    print("=" * 80)
    print("TEST 1: Policy Loading")
    print("=" * 80)
    
    try:
        policy = PolicyEngine()
        info = policy.get_policy_info()
        
        print(f"✓ Policy loaded successfully")
        print(f"  Policy Name: {info['policy_name']}")
        print(f"  Version: {info['policy_version']}")
        print(f"  Effective Date: {info['effective_date']}")
        print(f"  Source: {info['policy_file']}")
        return True
    except Exception as e:
        print(f"✗ Failed to load policy: {e}")
        return False

def test_eligibility_checks():
    """Test eligibility checking"""
    print("\n" + "=" * 80)
    print("TEST 2: Eligibility Checks")
    print("=" * 80)
    
    policy = get_policy_engine()
    
    test_cases = [
        {
            'name': 'Electronics within window',
            'purchase_date': '2026-03-01',
            'category': 'electronics',
            'expected_eligible': True
        },
        {
            'name': 'Electronics outside window',
            'purchase_date': '2025-01-01',
            'category': 'electronics',
            'expected_eligible': False
        },
        {
            'name': 'Digital product (non-returnable)',
            'purchase_date': '2026-03-20',
            'category': 'digital',
            'expected_eligible': False
        },
        {
            'name': 'Clothing within window',
            'purchase_date': '2026-03-15',
            'category': 'clothing',
            'expected_eligible': True
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        try:
            result = policy.check_eligibility(test['purchase_date'], test['category'])
            
            if result['eligible'] == test['expected_eligible']:
                print(f"✓ {test['name']}: {result['eligible']} (reason: {result['reason']})")
                passed += 1
            else:
                print(f"✗ {test['name']}: Expected {test['expected_eligible']}, got {result['eligible']}")
                failed += 1
        except Exception as e:
            print(f"✗ {test['name']}: Error - {e}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0

def test_refund_calculations():
    """Test refund calculations"""
    print("\n" + "=" * 80)
    print("TEST 3: Refund Calculations")
    print("=" * 80)
    
    policy = get_policy_engine()
    
    test_cases = [
        {
            'name': 'Defective item - full refund',
            'price': 100.00,
            'condition': 'unopened',
            'reason': 'defective',
            'expected_refund': 100.00
        },
        {
            'name': 'Unopened, changed mind - full refund',
            'price': 100.00,
            'condition': 'unopened',
            'reason': 'changed_mind',
            'expected_refund': 100.00
        },
        {
            'name': 'Opened unused - 15% restocking fee',
            'price': 100.00,
            'condition': 'opened_unused',
            'reason': 'changed_mind',
            'expected_refund': 85.00
        },
        {
            'name': 'Used - 20% restocking fee + 80% refund',
            'price': 100.00,
            'condition': 'used',
            'reason': 'changed_mind',
            'expected_refund': 60.00
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        try:
            result = policy.calculate_refund(test['price'], test['condition'], test['reason'])
            
            if abs(result['refund_amount'] - test['expected_refund']) < 0.01:
                print(f"✓ {test['name']}: ${result['refund_amount']:.2f}")
                passed += 1
            else:
                print(f"✗ {test['name']}: Expected ${test['expected_refund']:.2f}, got ${result['refund_amount']:.2f}")
                failed += 1
        except Exception as e:
            print(f"✗ {test['name']}: Error - {e}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0

def test_singleton_pattern():
    """Test that get_policy_engine returns same instance"""
    print("\n" + "=" * 80)
    print("TEST 4: Singleton Pattern")
    print("=" * 80)
    
    try:
        policy1 = get_policy_engine()
        policy2 = get_policy_engine()
        
        if policy1 is policy2:
            print("✓ Singleton pattern working correctly (same instance returned)")
            return True
        else:
            print("✗ Singleton pattern failed (different instances returned)")
            return False
    except Exception as e:
        print(f"✗ Error testing singleton: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("POLICY ENGINE TEST SUITE")
    print("=" * 80 + "\n")
    
    results = []
    
    results.append(("Policy Loading", test_policy_loading()))
    results.append(("Eligibility Checks", test_eligibility_checks()))
    results.append(("Refund Calculations", test_refund_calculations()))
    results.append(("Singleton Pattern", test_singleton_pattern()))
    
    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
