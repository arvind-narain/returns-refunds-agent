"""
Test script for returns_refunds_agent
Tests various customer service scenarios
"""

import os
import sys
import importlib.util

# Set environment variable for Knowledge Base
os.environ["KNOWLEDGE_BASE_ID"] = "WJOU9NWICK"

# Import run_agent from 01_returns_refunds_agent.py using importlib
def import_run_agent():
    """Import run_agent function from 01_returns_refunds_agent.py"""
    spec = importlib.util.spec_from_file_location("returns_refunds_agent", "01_returns_refunds_agent.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["returns_refunds_agent"] = module
    spec.loader.exec_module(module)
    return module.run_agent

# Test questions
test_questions = [
    {
        "id": 1,
        "question": "What time is it?",
        "description": "Test current_time tool"
    },
    {
        "id": 2,
        "question": "Can I return a laptop I purchased 25 days ago? The order ID is ORD-12345.",
        "description": "Test check_return_eligibility tool for electronics within window"
    },
    {
        "id": 3,
        "question": "Calculate my refund for a $500 item returned due to defect in like-new condition.",
        "description": "Test calculate_refund_amount tool for defective item"
    },
    {
        "id": 4,
        "question": "Explain the return policy for electronics in a simple way.",
        "description": "Test format_policy_response tool"
    },
    {
        "id": 5,
        "question": "Use the retrieve tool to search the knowledge base for 'Amazon return policy for electronics'",
        "description": "Test retrieve tool with Knowledge Base"
    }
]

def run_tests():
    """Run all test questions against the agent"""
    print("=" * 100)
    print("TESTING RETURNS & REFUNDS AGENT")
    print("=" * 100)
    print(f"\nKnowledge Base ID: {os.environ.get('KNOWLEDGE_BASE_ID')}")
    print(f"Total Tests: {len(test_questions)}\n")
    
    # Import the run_agent function
    try:
        run_agent = import_run_agent()
        print("✓ Successfully imported run_agent from 01_returns_refunds_agent.py\n")
    except Exception as e:
        print(f"✗ Failed to import run_agent: {e}")
        return
    
    # Run each test
    for test in test_questions:
        print("\n" + "=" * 100)
        print(f"TEST {test['id']}: {test['description']}")
        print("=" * 100)
        print(f"\nQUESTION: {test['question']}\n")
        print("-" * 100)
        
        try:
            # Run the agent with the test question
            response = run_agent(test['question'])
            
            print("RESPONSE:")
            print("-" * 100)
            print(response)
            print("-" * 100)
            print(f"✓ Test {test['id']} completed successfully")
            
        except Exception as e:
            print(f"✗ Test {test['id']} failed with error:")
            print(f"   {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 100)
    print("ALL TESTS COMPLETED")
    print("=" * 100)

if __name__ == "__main__":
    run_tests()
