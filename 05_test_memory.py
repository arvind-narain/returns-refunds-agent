#!/usr/bin/env python3
"""
Script to test AgentCore Memory retrieval.

This script retrieves and displays what the agent remembers about user_001:
- Preferences (email notifications, communication preferences)
- Semantic facts (return history, product interests)
- Conversation summaries
"""

import json

try:
    from bedrock_agentcore.memory import MemoryClient
except ImportError:
    print("✗ Error: bedrock_agentcore package not found")
    print("  Install with: pip install bedrock-agentcore")
    exit(1)

# Configuration
REGION = "us-west-2"
ACTOR_ID = "user_001"

print("=" * 80)
print("TESTING AGENTCORE MEMORY RETRIEVAL")
print("=" * 80)
print()

# Load memory_id from config
try:
    with open('memory_config.json') as f:
        config = json.load(f)
        memory_id = config['memory_id']
    print(f"✓ Loaded Memory ID: {memory_id}")
except FileNotFoundError:
    print("✗ Error: memory_config.json not found")
    print("  Run 03_create_memory.py first to create memory resource")
    exit(1)

print(f"✓ Region: {REGION}")
print(f"✓ Customer ID: {ACTOR_ID}")
print()

# Create memory client
memory_client = MemoryClient(region_name=REGION)

# ============================================================================
# TEST 1: Retrieve from PREFERENCES namespace
# ============================================================================
print("=" * 80)
print("TEST 1: PREFERENCES NAMESPACE")
print("=" * 80)
print()
print(f"Namespace: app/{ACTOR_ID}/preferences")
print(f"Query: 'customer preferences and communication'")
print(f"Top K: 3")
print()

try:
    preferences_memories = memory_client.retrieve_memories(
        memory_id=memory_id,
        namespace=f"app/{ACTOR_ID}/preferences",
        query="customer preferences and communication",
        top_k=3
    )
    
    if preferences_memories:
        print(f"✓ Retrieved {len(preferences_memories)} preference memories")
        print()
        
        for i, memory in enumerate(preferences_memories, 1):
            print(f"Preference Memory {i}:")
            print("─" * 70)
            content = memory.get('content', {})
            if isinstance(content, dict):
                text = content.get('text', 'N/A')
            else:
                text = str(content)
            print(f"Content: {text}")
            
            relevance = memory.get('relevanceScore', 'N/A')
            if isinstance(relevance, (int, float)):
                print(f"Relevance Score: {relevance:.3f}")
            else:
                print(f"Relevance Score: {relevance}")
            print()
    else:
        print("⚠️  No preference memories found")
        print("   Memory extraction may still be processing (takes 20-30 seconds)")
        print()
        
except Exception as e:
    print(f"❌ Error retrieving preferences: {e}")
    print()

# ============================================================================
# TEST 2: Retrieve from SEMANTIC namespace
# ============================================================================
print("=" * 80)
print("TEST 2: SEMANTIC NAMESPACE")
print("=" * 80)
print()
print(f"Namespace: app/{ACTOR_ID}/semantic")
print(f"Query: 'return history laptop electronics'")
print(f"Top K: 3")
print()

try:
    semantic_memories = memory_client.retrieve_memories(
        memory_id=memory_id,
        namespace=f"app/{ACTOR_ID}/semantic",
        query="return history laptop electronics",
        top_k=3
    )
    
    if semantic_memories:
        print(f"✓ Retrieved {len(semantic_memories)} semantic memories")
        print()
        
        for i, memory in enumerate(semantic_memories, 1):
            print(f"Semantic Memory {i}:")
            print("─" * 70)
            content = memory.get('content', {})
            if isinstance(content, dict):
                text = content.get('text', 'N/A')
            else:
                text = str(content)
            print(f"Content: {text}")
            
            relevance = memory.get('relevanceScore', 'N/A')
            if isinstance(relevance, (int, float)):
                print(f"Relevance Score: {relevance:.3f}")
            else:
                print(f"Relevance Score: {relevance}")
            print()
    else:
        print("⚠️  No semantic memories found")
        print("   Memory extraction may still be processing (takes 20-30 seconds)")
        print()
        
except Exception as e:
    print(f"❌ Error retrieving semantic memories: {e}")
    print()

# ============================================================================
# TEST 3: Get recent conversation turns (Short-term memory)
# ============================================================================
print("=" * 80)
print("TEST 3: SHORT-TERM MEMORY (Recent Conversations)")
print("=" * 80)
print()
print(f"Session: session_001")
print(f"Last K turns: 3")
print()

try:
    recent_turns = memory_client.get_last_k_turns(
        memory_id=memory_id,
        actor_id=ACTOR_ID,
        session_id="session_001",
        k=3
    )
    
    if recent_turns:
        print(f"✓ Retrieved {len(recent_turns)} recent conversation turns")
        print()
        
        for i, turn in enumerate(recent_turns, 1):
            print(f"Turn {i}:")
            print("─" * 70)
            for message in turn:
                role = message.get('role', 'UNKNOWN')
                content = message.get('content', {})
                if isinstance(content, dict):
                    text = content.get('text', 'N/A')
                elif isinstance(content, list) and len(content) > 0:
                    text = content[0].get('text', 'N/A')
                else:
                    text = str(content)
                print(f"{role}: {text}")
            print()
    else:
        print("⚠️  No recent turns found")
        print()
        
except Exception as e:
    print(f"❌ Error retrieving recent turns: {e}")
    print()

# ============================================================================
# SUMMARY
# ============================================================================
print("=" * 80)
print("WHAT THE AGENT REMEMBERS ABOUT USER_001")
print("=" * 80)
print()

has_data = False

if 'preferences_memories' in locals() and preferences_memories:
    print("📋 PREFERENCES:")
    for memory in preferences_memories:
        content = memory.get('content', {})
        if isinstance(content, dict):
            text = content.get('text', 'N/A')
        else:
            text = str(content)
        print(f"  • {text}")
    print()
    has_data = True

if 'semantic_memories' in locals() and semantic_memories:
    print("🧠 FACTS & HISTORY:")
    for memory in semantic_memories:
        content = memory.get('content', {})
        if isinstance(content, dict):
            text = content.get('text', 'N/A')
        else:
            text = str(content)
        print(f"  • {text}")
    print()
    has_data = True

if 'recent_turns' in locals() and recent_turns:
    print("💬 RECENT CONVERSATION CONTEXT:")
    print(f"  • {len(recent_turns)} conversation turns from session_001")
    print()
    has_data = True

if not has_data:
    print("⚠️  No memories retrieved yet")
    print()
    print("Possible reasons:")
    print("  1. Memory extraction is still processing (wait 20-30 seconds)")
    print("  2. No conversations have been stored yet (run 04_seed_memory.py)")
    print("  3. Memory strategies are still being provisioned")
    print()

print("=" * 80)
print("MEMORY TEST COMPLETE")
print("=" * 80)
