#!/usr/bin/env python3
"""
Test script for memory-enabled returns agent.

This script tests if the agent correctly recalls:
- Customer communication preferences (email notifications)
- Past return history (defective laptop, wireless mouse)
- Personalized service based on memory
"""

import os
import json
import sys
import importlib.util

print("=" * 80)
print("TESTING MEMORY-ENABLED RETURNS AGENT")
print("=" * 80)
print()

# ============================================================================
# LOAD CONFIGURATION
# ============================================================================

# Load Memory ID from config
try:
    with open('memory_config.json') as f:
        memory_config = json.load(f)
        memory_id = memory_config.get('memory_id')
    print(f"✓ Loaded Memory ID: {memory_id}")
except FileNotFoundError:
    print("✗ Error: memory_config.json not found")
    print("  Run 03_create_memory.py first to create memory resource")
    sys.exit(1)

# Load Knowledge Base ID from config
try:
    with open('kb_config.json') as f:
        kb_config = json.load(f)
        kb_id = kb_config.get('knowledge_base_id')
    print(f"✓ Loaded Knowledge Base ID: {kb_id}")
except FileNotFoundError:
    print("✗ Error: kb_config.json not found")
    sys.exit(1)

print()

# Set environment variables
os.environ["MEMORY_ID"] = memory_id
os.environ["KNOWLEDGE_BASE_ID"] = kb_id

# ============================================================================
# IMPORT AGENT
# ============================================================================

print("Importing memory-enabled agent...")

try:
    # Import run_agent from 06_memory_enabled_agent.py using importlib
    spec = importlib.util.spec_from_file_location(
        "memory_enabled_agent", 
        "06_memory_enabled_agent.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["memory_enabled_agent"] = module
    spec.loader.exec_module(module)
    run_agent = module.run_agent
    print("✓ Successfully imported run_agent")
except Exception as e:
    print(f"✗ Failed to import agent: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# ============================================================================
# TEST CONFIGURATION
# ============================================================================

ACTOR_ID = "user_001"
SESSION_ID = "test_memory_session"

print("=" * 80)
print("TEST CONFIGURATION")
print("=" * 80)
print()
print(f"Customer ID: {ACTOR_ID}")
print(f"Session ID: {SESSION_ID}")
print(f"Memory ID: {memory_id}")
print()
print("Expected Memory Recall:")
print("  • Preference: Email notifications (not phone calls)")
print("  • History: Returned defective laptop last month")
print("  • History: Wireless mouse from order #78945 stopped working")
print("  • Interest: Considering purchasing a tablet")
print()

# ============================================================================
# RUN TEST
# ============================================================================

print("=" * 80)
print("RUNNING TEST")
print("=" * 80)
print()

test_query = "Hi! I'm thinking about returning something. What do you remember about my preferences?"

print(f"User Query: {test_query}")
print()
print("-" * 80)
print("AGENT PROCESSING...")
print("-" * 80)
print()

try:
    # Run the agent with user_001's context
    response = run_agent(
        user_input=test_query,
        session_id=SESSION_ID,
        actor_id=ACTOR_ID
    )
    
    print("=" * 80)
    print("AGENT RESPONSE:")
    print("=" * 80)
    print()
    print(response)
    print()
    
except Exception as e:
    print("=" * 80)
    print("✗ ERROR DURING AGENT EXECUTION")
    print("=" * 80)
    print()
    print(f"Error: {e}")
    print()
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# ANALYZE RESPONSE
# ============================================================================

print("=" * 80)
print("MEMORY RECALL ANALYSIS")
print("=" * 80)
print()

response_lower = response.lower()

# Check for preference recall
email_mentioned = any(word in response_lower for word in ['email', 'e-mail'])
phone_mentioned = 'phone' in response_lower

# Check for history recall
laptop_mentioned = 'laptop' in response_lower
mouse_mentioned = 'mouse' in response_lower
order_mentioned = '78945' in response_lower or 'order' in response_lower
defective_mentioned = 'defective' in response_lower

# Check for personalization
preference_mentioned = 'preference' in response_lower or 'prefer' in response_lower

print("Memory Recall Checklist:")
print()

print("📋 PREFERENCES:")
if email_mentioned:
    print("  ✅ Email preference mentioned")
else:
    print("  ❌ Email preference NOT mentioned")

if preference_mentioned:
    print("  ✅ Acknowledged customer preferences")
else:
    print("  ⚠️  Did not explicitly acknowledge preferences")

print()
print("🧠 RETURN HISTORY:")

if laptop_mentioned:
    print("  ✅ Previous laptop return mentioned")
else:
    print("  ❌ Previous laptop return NOT mentioned")

if mouse_mentioned or order_mentioned:
    print("  ✅ Wireless mouse issue mentioned")
else:
    print("  ❌ Wireless mouse issue NOT mentioned")

if defective_mentioned:
    print("  ✅ Defective item context recalled")
else:
    print("  ⚠️  Defective context not explicitly mentioned")

print()

# Overall assessment
recalls = sum([
    email_mentioned,
    laptop_mentioned,
    mouse_mentioned or order_mentioned,
    preference_mentioned
])

print("=" * 80)
print("OVERALL ASSESSMENT")
print("=" * 80)
print()
print(f"Memory Recall Score: {recalls}/4 key points")
print()

if recalls >= 3:
    print("✅ EXCELLENT - Agent successfully recalled customer preferences and history!")
    print("   The agent is providing personalized service based on memory.")
elif recalls >= 2:
    print("✓ GOOD - Agent recalled some customer information.")
    print("  Memory integration is working but could be more comprehensive.")
else:
    print("⚠️  LIMITED - Agent did not recall much customer information.")
    print("   Check if memory strategies have finished processing (wait 30 seconds after seeding).")

print()
print("=" * 80)
print("TEST COMPLETE")
print("=" * 80)
