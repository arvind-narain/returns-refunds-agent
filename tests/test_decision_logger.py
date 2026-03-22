#!/usr/bin/env python3
"""
Test script for Decision Logger
Tests logging to CloudWatch, DynamoDB, and S3
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.decision_logger import DecisionLogger, get_decision_logger

def test_logger_initialization():
    """Test that logger initializes correctly"""
    print("=" * 80)
    print("TEST 1: Logger Initialization")
    print("=" * 80)
    
    try:
        logger = DecisionLogger()
        print("✓ Decision logger initialized successfully")
        print(f"  Logging enabled: {logger.enabled}")
        print(f"  DynamoDB table: {logger.table_name}")
        print(f"  S3 bucket: {logger.s3_bucket}")
        print(f"  Region: {logger.region}")
        return True
    except Exception as e:
        print(f"✗ Failed to initialize logger: {e}")
        return False

def test_eligibility_logging():
    """Test eligibility decision logging"""
    print("\n" + "=" * 80)
    print("TEST 2: Eligibility Decision Logging")
    print("=" * 80)
    
    try:
        logger = get_decision_logger()
        
        # Log a test decision
        logger.log_eligibility_decision(
            order_id="TEST-ORDER-001",
            purchase_date="2026-03-01",
            category="electronics",
            eligible=True,
            reason="Within 90-day return window",
            policy_version="1.0",
            actor_id="test-actor",
            session_id="test-session"
        )
        
        print("✓ Eligibility decision logged successfully")
        print("  Check CloudWatch Logs for entry")
        return True
    except Exception as e:
        print(f"✗ Failed to log eligibility decision: {e}")
        return False

def test_refund_logging():
    """Test refund decision logging"""
    print("\n" + "=" * 80)
    print("TEST 3: Refund Decision Logging")
    print("=" * 80)
    
    try:
        logger = get_decision_logger()
        
        # Log a test decision
        logger.log_refund_decision(
            order_id="TEST-ORDER-002",
            original_price=100.00,
            refund_amount=85.00,
            item_condition="opened_unused",
            return_reason="changed_mind",
            policy_version="1.0",
            actor_id="test-actor",
            session_id="test-session"
        )
        
        print("✓ Refund decision logged successfully")
        print("  Check CloudWatch Logs for entry")
        return True
    except Exception as e:
        print(f"✗ Failed to log refund decision: {e}")
        return False

def test_generic_logging():
    """Test generic decision logging"""
    print("\n" + "=" * 80)
    print("TEST 4: Generic Decision Logging")
    print("=" * 80)
    
    try:
        logger = get_decision_logger()
        
        # Log a generic decision
        logger.log_decision(
            decision_type="test_decision",
            decision_data={
                'test_field': 'test_value',
                'numeric_field': 123,
                'boolean_field': True
            },
            order_id="TEST-ORDER-003",
            policy_version="1.0",
            actor_id="test-actor",
            session_id="test-session"
        )
        
        print("✓ Generic decision logged successfully")
        print("  Check CloudWatch Logs for entry")
        return True
    except Exception as e:
        print(f"✗ Failed to log generic decision: {e}")
        return False

def test_singleton_pattern():
    """Test that get_decision_logger returns same instance"""
    print("\n" + "=" * 80)
    print("TEST 5: Singleton Pattern")
    print("=" * 80)
    
    try:
        logger1 = get_decision_logger()
        logger2 = get_decision_logger()
        
        if logger1 is logger2:
            print("✓ Singleton pattern working correctly (same instance returned)")
            return True
        else:
            print("✗ Singleton pattern failed (different instances returned)")
            return False
    except Exception as e:
        print(f"✗ Error testing singleton: {e}")
        return False

def test_disabled_logging():
    """Test that logging can be disabled"""
    print("\n" + "=" * 80)
    print("TEST 6: Disabled Logging")
    print("=" * 80)
    
    try:
        # Set environment variable to disable logging
        os.environ['ENABLE_DECISION_LOGGING'] = 'false'
        
        # Create new logger instance
        logger = DecisionLogger()
        
        if not logger.enabled:
            print("✓ Logging disabled successfully")
            
            # Try to log (should not raise error)
            logger.log_decision(
                decision_type="test",
                decision_data={'test': 'value'},
                order_id="TEST-ORDER-004"
            )
            print("✓ Logging call with disabled logger succeeded (no-op)")
            
            # Re-enable for other tests
            os.environ['ENABLE_DECISION_LOGGING'] = 'true'
            return True
        else:
            print("✗ Failed to disable logging")
            return False
    except Exception as e:
        print(f"✗ Error testing disabled logging: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("DECISION LOGGER TEST SUITE")
    print("=" * 80 + "\n")
    
    print("Note: These tests will create log entries in CloudWatch Logs.")
    print("DynamoDB and S3 logging will only work if resources are configured.\n")
    
    results = []
    
    results.append(("Logger Initialization", test_logger_initialization()))
    results.append(("Eligibility Logging", test_eligibility_logging()))
    results.append(("Refund Logging", test_refund_logging()))
    results.append(("Generic Logging", test_generic_logging()))
    results.append(("Singleton Pattern", test_singleton_pattern()))
    results.append(("Disabled Logging", test_disabled_logging()))
    
    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n✓ All tests passed!")
        print("\nTo verify logging:")
        print("  1. Check CloudWatch Logs: /aws/returns-agent/decisions")
        print("  2. Check DynamoDB table: returns-decision-log (if created)")
        print("  3. Check S3 bucket: returns-decision-logs (if configured)")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
