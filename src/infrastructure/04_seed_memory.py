#!/usr/bin/env python3
"""
Script to seed AgentCore Memory with sample customer conversations.

This script adds realistic customer interactions to test memory capabilities:
- Conversation 1: Customer mentions email preference and previous defective laptop return
- Conversation 2: Customer asks about return windows for electronics

Memory strategies will extract:
- Preferences: Email notifications preference
- Semantic: Previous laptop return history
- Summary: Context about customer's return inquiries
"""

import json
import time

try:
    from bedrock_agentcore.memory import MemoryClient
except ImportError:
    print("✗ Error: bedrock_agentcore package not found")
    print("  Install with: pip install bedrock-agentcore")
    exit(1)

# Load memory_id from config
print("=" * 80)
print("SEEDING AGENTCORE MEMORY WITH SAMPLE CONVERSATIONS")
print("=" * 80)
print()

try:
    with open('memory_config.json') as f:
        config = json.load(f)
        memory_id = config['memory_id']
    print(f"✓ Loaded Memory ID: {memory_id}")
except FileNotFoundError:
    print("✗ Error: memory_config.json not found")
    print("  Run 03_create_memory.py first to create memory resource")
    exit(1)

# Configuration
REGION = "us-west-2"
ACTOR_ID = "user_001"

print(f"✓ Region: {REGION}")
print(f"✓ Customer ID: {ACTOR_ID}")
print()

# Create memory client
memory_client = MemoryClient(region_name=REGION)

# ============================================================================
# CONVERSATION 1: Customer mentions preferences and previous return
# ============================================================================
print("=" * 80)
print("CONVERSATION 1: Email Preference & Previous Laptop Return")
print("=" * 80)
print()

session_1_messages = [
    ("Hello, I need help with a return", "USER"),
    ("Of course! I'd be happy to help you with your return. Could you please provide me with your order number?", "ASSISTANT"),
    ("It's order #78945. I prefer to receive updates via email, not phone calls.", "USER"),
    ("Thank you! I've noted your preference for email notifications. Let me look up order #78945 for you.", "ASSISTANT"),
    ("Thanks. By the way, I returned a defective laptop last month and the process was smooth. Hoping this will be the same.", "USER"),
    ("I'm glad your previous laptop return went smoothly! I'll make sure this return is just as easy. What item are you looking to return from order #78945?", "ASSISTANT"),
    ("It's a wireless mouse that stopped working after a week.", "USER"),
    ("I understand. Since the mouse is defective and within the 30-day return window, you're eligible for a full refund. I'll send you a return label via email shortly.", "ASSISTANT")
]

print("Storing conversation 1...")
print(f"  Session ID: session_001")
print(f"  Messages: {len(session_1_messages)}")
print()

try:
    memory_client.create_event(
        memory_id=memory_id,
        actor_id=ACTOR_ID,
        session_id="session_001",
        messages=session_1_messages
    )
    print("✓ Conversation 1 stored successfully!")
except Exception as e:
    print(f"✗ Error storing conversation 1: {e}")
    exit(1)

print()

# ============================================================================
# CONVERSATION 2: Customer asks about electronics return windows
# ============================================================================
print("=" * 80)
print("CONVERSATION 2: Electronics Return Window Inquiry")
print("=" * 80)
print()

session_2_messages = [
    ("Hi, I have a question about return policies", "USER"),
    ("Hello! I'd be happy to help with your return policy question. What would you like to know?", "ASSISTANT"),
    ("What's the return window for electronics? I'm thinking of buying a tablet.", "USER"),
    ("Great question! For most electronics including tablets, you have a 30-day return window from the date of delivery. The item must be in original condition with all accessories and packaging.", "ASSISTANT"),
    ("That's good to know. What if it's defective?", "USER"),
    ("If an electronic item is defective, you're still covered within the 30-day window for a full refund or replacement. For defects discovered after 30 days, the manufacturer's warranty would apply.", "ASSISTANT"),
    ("Perfect, that's what I needed to know. Thanks!", "USER"),
    ("You're welcome! Feel free to reach out if you have any other questions. Happy shopping!", "ASSISTANT")
]

print("Storing conversation 2...")
print(f"  Session ID: session_002")
print(f"  Messages: {len(session_2_messages)}")
print()

try:
    memory_client.create_event(
        memory_id=memory_id,
        actor_id=ACTOR_ID,
        session_id="session_002",
        messages=session_2_messages
    )
    print("✓ Conversation 2 stored successfully!")
except Exception as e:
    print(f"✗ Error storing conversation 2: {e}")
    exit(1)

print()

# ============================================================================
# WAIT FOR MEMORY PROCESSING
# ============================================================================
print("=" * 80)
print("WAITING FOR MEMORY PROCESSING")
print("=" * 80)
print()
print("Memory strategies are now processing the conversations asynchronously...")
print("This extracts:")
print("  • User preferences (email notifications)")
print("  • Semantic facts (previous laptop return)")
print("  • Conversation summaries")
print()
print("⏳ Waiting 30 seconds for processing to complete...")
print()

for i in range(30, 0, -5):
    print(f"   {i} seconds remaining...")
    time.sleep(5)

print()
print("✓ Memory processing complete!")
print()

# ============================================================================
# SUMMARY
# ============================================================================
print("=" * 80)
print("✅ MEMORY SEEDING COMPLETE")
print("=" * 80)
print()
print("Summary:")
print(f"  Memory ID: {memory_id}")
print(f"  Customer ID: {ACTOR_ID}")
print(f"  Conversations stored: 2")
print(f"  Total messages: {len(session_1_messages) + len(session_2_messages)}")
print()
print("Extracted Information (available for retrieval):")
print("  ✓ Preference: Customer prefers email notifications")
print("  ✓ History: Previously returned a defective laptop")
print("  ✓ Context: Interested in electronics return policies")
print()
print("Next Steps:")
print("  1. Test memory retrieval with your agent")
print("  2. Query for user preferences")
print("  3. Search semantic memories for return history")
print()
print("=" * 80)
